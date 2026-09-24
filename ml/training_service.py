"""Local training, model versioning, and optional Vercel deployment."""
from __future__ import annotations

import hashlib
import logging
import os
import shutil
import subprocess
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import joblib
import pandas as pd

from config.settings import settings
from data.api_client import APIClient
from data.database import DatabaseManager
from ml.validator import PatternMLValidator

logger = logging.getLogger(__name__)


class TrainingService:
    """Runs local ML training against Supabase-backed market history."""

    def __init__(self, db: DatabaseManager | None = None):
        self.db = db or DatabaseManager()
        self.api_client = APIClient(self.db)
        self.last_training: dict[str, Any] | None = None

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as file:
            for block in iter(lambda: file.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()

    @staticmethod
    def _active_paths() -> tuple[Path, Path]:
        return Path(settings.ML_MODEL_PATH).resolve(), Path(settings.ML_SCALER_PATH).resolve()

    def _backup_active_models(self, version: str) -> str | None:
        model_path, scaler_path = self._active_paths()
        if not model_path.is_file() or not scaler_path.is_file():
            return None
        versions_dir = Path(settings.MODEL_VERSIONS_DIR)
        backup_dir = versions_dir / version
        backup_dir.mkdir(parents=True, exist_ok=False)
        shutil.copy2(model_path, backup_dir / model_path.name)
        shutil.copy2(scaler_path, backup_dir / scaler_path.name)
        return str(backup_dir.relative_to(Path(settings.BASE_DIR)))

    def _prune_backups(self, keep: int = 3) -> None:
        versions_dir = Path(settings.MODEL_VERSIONS_DIR)
        if not versions_dir.is_dir():
            return
        backups = sorted((path for path in versions_dir.iterdir() if path.is_dir()), key=lambda path: path.name, reverse=True)
        for obsolete in backups[keep:]:
            shutil.rmtree(obsolete)

    def train(self, days: int = 30) -> dict:
        if days < 7:
            raise ValueError("Use at least 7 days of hourly data for training.")
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)
        historical = self.api_client.get_historical_data(settings.SYMBOL, "1h", start_date, end_date)
        if historical is None or len(historical) < 100:
            raise RuntimeError("Insufficient historical candles for training (minimum: 100).")

        validator = PatternMLValidator()
        metrics = validator.train_models(historical)
        version = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        model_path, scaler_path = self._active_paths()
        stage_root = Path(tempfile.mkdtemp(prefix="aracbot-training-", dir=model_path.parent))
        staged_model = stage_root / model_path.name
        staged_scaler = stage_root / scaler_path.name

        try:
            # Do not disturb the active model until both staged artifacts can be read.
            validator.save_models(str(staged_model), str(staged_scaler))
            joblib.load(staged_model)
            joblib.load(staged_scaler)

            backup_path = self._backup_active_models(version)
            os.replace(staged_model, model_path)
            os.replace(staged_scaler, scaler_path)
            self._prune_backups(keep=3)
        finally:
            shutil.rmtree(stage_root, ignore_errors=True)

        result = {
            "version": version,
            "status": "completed",
            "data_start": pd.to_datetime(historical["timestamp"].min()).to_pydatetime(),
            "data_end": pd.to_datetime(historical["timestamp"].max()).to_pydatetime(),
            "total_rows": int(len(historical)),
            "metrics": metrics,
            "model_sha256": self._sha256(model_path),
            "scaler_sha256": self._sha256(scaler_path),
            "backup_path": backup_path,
        }
        try:
            result["run_id"] = self.db.save_model_training_run(result)
        except Exception as exc:
            # The artifacts are valid and active, but the UI must make this
            # visible because the Supabase migration may not yet be applied.
            result["metadata_error"] = str(exc)
            logger.error("Could not persist training metadata: %s", exc)
        self.last_training = result
        return result

    def recent_runs(self, limit: int = 10) -> list[dict]:
        return self.db.get_recent_model_training_runs(limit)

    def deploy(self, version: str) -> str:
        """Deploy current artifacts only when the user explicitly chooses it."""
        command = ["npx", "vercel", "--prod", "--yes"]
        process = subprocess.run(command, cwd=settings.BASE_DIR, text=True, capture_output=True, timeout=900, check=False)
        output = "\n".join(part for part in (process.stdout, process.stderr) if part).strip()
        if process.returncode != 0:
            raise RuntimeError(f"Vercel deployment failed:\n{output[-3000:]}")
        urls = [line.strip() for line in output.splitlines() if line.strip().startswith("https://")]
        deployment_url = urls[-1] if urls else ""
        self.db.mark_model_training_deployed(version, deployment_url)
        return deployment_url
