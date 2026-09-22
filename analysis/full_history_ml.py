import json
import hashlib
import logging
from datetime import datetime
from typing import Dict, Optional

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler

from config.settings import settings
from ml.validator import PatternMLValidator


class FullHistoryMLEvaluator:
    """Executa treino walk-forward em série histórica completa e registra hashes."""

    def __init__(self, api_client, db_manager, logger: Optional[logging.Logger] = None):
        self.api_client = api_client
        self.db = db_manager
        self.logger = logger or logging.getLogger(__name__)
        self.validator = PatternMLValidator()

    def _build_recipe(self, symbol: str, timeframe: str, horizon: str,
                      min_train_size: int, retrain_every: int,
                      feature_columns: list) -> Dict:
        return {
            "version": "full_history_ml_v1",
            "symbol": symbol,
            "timeframe": timeframe,
            "horizon": horizon,
            "model": "RandomForestClassifier",
            "model_params": {
                "n_estimators": 200,
                "random_state": 42,
                "n_jobs": -1,
                "class_weight": "balanced_subsample"
            },
            "min_train_size": min_train_size,
            "retrain_every": retrain_every,
            "ml_confidence_weight": settings.ML_CONFIDENCE_WEIGHT,
            "feature_columns": feature_columns,
            "target": "future_direction"
        }

    @staticmethod
    def _hash_payload(payload: Dict) -> str:
        raw = json.dumps(payload, sort_keys=True, ensure_ascii=True)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    @staticmethod
    def _sanitize_feature_frame(df: pd.DataFrame, feature_columns: list) -> pd.DataFrame:
        """Normaliza tipos numéricos e remove linhas com valores inválidos para ML."""
        clean = df.copy()

        for col in feature_columns:
            clean[col] = pd.to_numeric(clean[col], errors="coerce")

        clean[feature_columns] = clean[feature_columns].replace([np.inf, -np.inf], np.nan)
        clean = clean.dropna(subset=feature_columns + ["target_direction"]).reset_index(drop=True)

        # Limite defensivo para evitar overflow em validações internas do sklearn.
        clean[feature_columns] = clean[feature_columns].clip(lower=-1e12, upper=1e12)
        return clean

    def run(self,
            symbol: str = "BTCUSDT",
            timeframe: str = "1h",
            horizon: str = "24h",
            start_date: Optional[datetime] = None,
            end_date: Optional[datetime] = None,
            min_train_size: int = 1000,
            retrain_every: int = 24) -> Dict:
        horizon_bars = {"1h": 1, "4h": 4, "24h": 24}
        if horizon not in horizon_bars:
            raise ValueError(f"Unsupported horizon: {horizon}")

        historical_data = self.api_client.get_full_historical_data(
            symbol=symbol,
            timeframe=timeframe,
            start_date=start_date,
            end_date=end_date
        )

        if historical_data is None or historical_data.empty:
            raise RuntimeError("No historical data available for full-history ML evaluation")

        self.logger.info(f"[FULL-ML] Loaded {len(historical_data)} candles")
        self.logger.info(f"[FULL-ML] Starting walk-forward evaluation for {symbol} {timeframe} horizon={horizon}")

        features_df = self.validator.create_ml_features(historical_data)
        bars_ahead = horizon_bars[horizon]

        features_df["future_return_eval"] = (
            features_df["close"].shift(-bars_ahead) / features_df["close"] - 1
        )
        features_df["target_direction"] = (features_df["future_return_eval"] > 0).astype(int)
        features_df = features_df.dropna().reset_index(drop=True)

        feature_columns = [
            col for col in features_df.columns
            if col not in [
                "future_return_1h",
                "future_return_4h",
                "future_return_eval",
                "target_direction",
                "timestamp",
                "open",
                "high",
                "low",
                "close",
                "volume"
            ]
        ]

        features_df = self._sanitize_feature_frame(features_df, feature_columns)

        self.logger.info(
            f"[FULL-ML] Valid samples after sanitization: {len(features_df)}"
        )

        if len(features_df) <= min_train_size:
            raise RuntimeError(
                f"Not enough samples after feature engineering: {len(features_df)} <= {min_train_size}"
            )

        recipe_payload = self._build_recipe(
            symbol=symbol,
            timeframe=timeframe,
            horizon=horizon,
            min_train_size=min_train_size,
            retrain_every=retrain_every,
            feature_columns=feature_columns
        )
        recipe_hash = self._hash_payload(recipe_payload)

        predictions = []
        model = None
        scaler = None

        for i in range(min_train_size, len(features_df)):
            if model is None or ((i - min_train_size) % retrain_every == 0):
                train_slice = features_df.iloc[:i]
                X_train = train_slice[feature_columns].to_numpy(dtype=np.float64, copy=False)
                y_train = train_slice["target_direction"].values

                if not np.isfinite(X_train).all():
                    self.logger.warning(
                        f"[FULL-ML] Skipping retrain at i={i} due to non-finite values in training window"
                    )
                    model = None
                    scaler = None
                    continue

                if len(np.unique(y_train)) < 2:
                    continue

                scaler = StandardScaler()
                X_train_scaled = scaler.fit_transform(X_train)

                model = RandomForestClassifier(
                    n_estimators=200,
                    random_state=42,
                    n_jobs=-1,
                    class_weight="balanced_subsample"
                )
                model.fit(X_train_scaled, y_train)

            if model is None or scaler is None:
                continue

            row = features_df.iloc[i]
            X_now = row[feature_columns].to_numpy(dtype=np.float64).reshape(1, -1)

            if not np.isfinite(X_now).all():
                continue

            X_now_scaled = scaler.transform(X_now)

            up_probability = float(model.predict_proba(X_now_scaled)[0, 1])
            pred_direction = "up" if up_probability >= 0.5 else "down"
            actual_direction = "up" if int(row["target_direction"]) == 1 else "down"
            was_correct = 1 if pred_direction == actual_direction else 0

            decision_payload = {
                "recipe_hash": recipe_hash,
                "timestamp": str(row["timestamp"]),
                "predicted_direction": pred_direction,
                "actual_direction": actual_direction,
                "confidence": round(up_probability, 8)
            }
            decision_hash = self._hash_payload(decision_payload)

            predictions.append({
                "timestamp": str(row["timestamp"]),
                "predicted_direction": pred_direction,
                "actual_direction": actual_direction,
                "confidence": up_probability,
                "was_correct": was_correct,
                "decision_hash": decision_hash
            })

        if not predictions:
            raise RuntimeError("No predictions generated in walk-forward evaluation")

        total = len(predictions)
        correct = sum(int(p["was_correct"]) for p in predictions)
        accuracy = correct / total

        run_id = self.db.save_ml_recipe_run(
            recipe_hash=recipe_hash,
            symbol=symbol,
            timeframe=timeframe,
            horizon=horizon,
            config_json=json.dumps(recipe_payload, ensure_ascii=True),
            total_predictions=total,
            accuracy=accuracy
        )
        self.db.save_ml_recipe_predictions(run_id, predictions)

        self.logger.info(
            f"[FULL-ML] recipe={recipe_hash[:12]} total={total} correct={correct} accuracy={accuracy:.2%}"
        )

        return {
            "run_id": run_id,
            "recipe_hash": recipe_hash,
            "total_predictions": total,
            "correct_predictions": correct,
            "accuracy": accuracy,
            "symbol": symbol,
            "timeframe": timeframe,
            "horizon": horizon,
            "start_timestamp": str(features_df.iloc[min_train_size]["timestamp"]),
            "end_timestamp": str(features_df.iloc[-1]["timestamp"])
        }
