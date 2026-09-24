"""Supabase Postgres persistence for the serverless bot."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional
from urllib.parse import urlparse

import pandas as pd
import psycopg

from config.settings import settings

logger = logging.getLogger(__name__)


class SupabaseDatabaseManager:
    """Short-lived Postgres connections; schema is managed by migrations."""

    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url or settings.DATABASE_URL
        if not self.database_url:
            raise RuntimeError("DATABASE_URL is required; configure the Supabase pooler URL.")
        if "\\." in self.database_url:
            raise RuntimeError(
                "DATABASE_URL inválida: o hostname contém '\\.'. Remova a barra invertida; "
                "use db.seu-project-ref.supabase.co, nunca db.seu-project-ref\\.supabase.co."
            )
        # Square brackets are only for literal IPv6 addresses in URLs. They
        # must not surround the textual Supabase hostname copied from Connect.
        authority = self.database_url.rsplit("@", 1)[-1].split("/", 1)[0]
        if authority.startswith("["):
            raise RuntimeError(
                "DATABASE_URL inválida: não coloque o hostname Supabase entre colchetes []. "
                "Copie a URI do painel Connect sem os caracteres de placeholder."
            )

    def setup_database(self) -> None:
        """Legacy no-op. Never create schema in a request handler."""

    def get_connection(self):
        # Supavisor transaction pooling does not allow prepared statements.
        try:
            return psycopg.connect(
                self.database_url,
                prepare_threshold=None,
                autocommit=False,
                connect_timeout=10,
            )
        except psycopg.OperationalError as exc:
            host = urlparse(self.database_url).hostname or "<invalid DATABASE_URL>"
            pooler_hint = (
                "Use the Supabase Transaction pooler URL (host ending in "
                ".pooler.supabase.com, port 6543), not the direct db.<project>.supabase.co URL."
            )
            raise RuntimeError(
                f"Could not resolve/connect to Supabase host '{host}'. {pooler_hint} "
                "Check DATABASE_URL, DNS, and the network connection."
            ) from exc

    @staticmethod
    def _json(value: Any) -> str:
        return json.dumps(value, default=str, separators=(",", ":"))

    def save_pattern(self, data: dict) -> int:
        with self.get_connection() as conn, conn.cursor() as cur:
            cur.execute("""INSERT INTO patterns_detected (timestamp,pattern_name,signal_type,confidence,ml_confidence,combined_confidence,price_detection,position_size,prediction,timeframe)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
                (data.get("timestamp", datetime.now(timezone.utc)), data["pattern_name"], data["signal_type"], data.get("confidence", 0), data.get("ml_confidence", 0), data.get("combined_confidence", 0), data["price_detection"], data.get("position_size", 0), data.get("prediction", "HOLD"), data.get("timeframe", "1m")))
            return cur.fetchone()[0]

    def update_pattern_result(self, pattern_id: int, data: dict) -> None:
        with self.get_connection() as conn, conn.cursor() as cur:
            cur.execute("UPDATE patterns_detected SET status='closed',result=%s,profit_loss=%s,duration_minutes=%s,exit_reason=%s WHERE id=%s",
                        (data["result"], data["profit_loss"], data["duration_minutes"], data.get("exit_reason", "timeout"), pattern_id))

    def get_patterns_by_status(self, status="open") -> pd.DataFrame:
        with self.get_connection() as conn:
            return pd.read_sql("SELECT * FROM patterns_detected WHERE status=%s", conn, params=[status])

    def save_price_data(self, df: pd.DataFrame, symbol: str, timeframe: str) -> None:
        if df.empty:
            return
        rows = [(r.timestamp, symbol, timeframe, float(r.open), float(r.high), float(r.low), float(r.close), float(r.volume))
                for r in df[["timestamp", "open", "high", "low", "close", "volume"]].itertuples(index=False)]
        with self.get_connection() as conn, conn.cursor() as cur:
            cur.executemany("""INSERT INTO price_history (timestamp,symbol,timeframe,open,high,low,close,volume)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (timestamp,symbol,timeframe) DO UPDATE SET
                open=EXCLUDED.open,high=EXCLUDED.high,low=EXCLUDED.low,close=EXCLUDED.close,volume=EXCLUDED.volume""", rows)

    def get_price_data(self, symbol, timeframe, start_date=None, end_date=None) -> pd.DataFrame:
        query, params = "SELECT timestamp,open,high,low,close,volume FROM price_history WHERE symbol=%s AND timeframe=%s", [symbol, timeframe]
        if start_date:
            query += " AND timestamp >= %s"; params.append(start_date)
        if end_date:
            query += " AND timestamp <= %s"; params.append(end_date)
        with self.get_connection() as conn:
            df = pd.read_sql(query + " ORDER BY timestamp", conn, params=params)
        if not df.empty:
            df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True).dt.tz_localize(None)
        return df

    def save_signal_for_analysis(self, data: dict) -> None:
        with self.get_connection() as conn, conn.cursor() as cur:
            cur.execute("""INSERT INTO collected_signals (timestamp,pattern,confidence,signal,price,market_data)
                VALUES (%s,%s,%s,%s,%s,%s::jsonb) ON CONFLICT (timestamp,pattern,signal) DO NOTHING""",
                (data["timestamp"], data["pattern"], data["confidence"], data["signal"], data["price"], self._json(data["market_data"])))

    def get_collected_signals(self) -> pd.DataFrame:
        with self.get_connection() as conn:
            return pd.read_sql("SELECT * FROM collected_signals ORDER BY timestamp", conn)

    def save_trade_result(self, data: dict) -> None:
        with self.get_connection() as conn, conn.cursor() as cur:
            cur.execute("""INSERT INTO patterns_detected (timestamp,pattern_name,signal_type,confidence,price_detection,position_size,result,profit_loss,exit_reason,status)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,'closed')""",
                (data["timestamp"], data["pattern"], data["signal_type"], data.get("confidence", 0), data["entry_price"], data["position_size"], data["result"], data["profit"], data.get("exit_reason", "manual")))

    def save_news_sentiment(self, data: dict) -> None:
        with self.get_connection() as conn, conn.cursor() as cur:
            cur.execute("""INSERT INTO news_sentiment (timestamp,score,label,confidence,news_count,positive_count,negative_count,neutral_count)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""", (data["timestamp"], data["score"], data["label"], data["confidence"], data["news_count"], data["positive_count"], data["negative_count"], data["neutral_count"]))

    def save_news_article(self, data: dict) -> bool:
        with self.get_connection() as conn, conn.cursor() as cur:
            cur.execute("""INSERT INTO news_articles (timestamp,title,source,sentiment_score,sentiment_label,url)
                VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT (url) DO NOTHING""",
                (data["timestamp"], data["title"], data["source"], data["sentiment_score"], data["sentiment_label"], data.get("url", "")))
            return cur.rowcount > 0

    def save_ml_recipe_run(self, recipe_hash, symbol, timeframe, horizon, config_json, total_predictions, accuracy) -> int:
        with self.get_connection() as conn, conn.cursor() as cur:
            cur.execute("""INSERT INTO ml_recipe_runs (recipe_hash,symbol,timeframe,horizon,config_json,total_predictions,accuracy)
                VALUES (%s,%s,%s,%s,%s::jsonb,%s,%s) ON CONFLICT (recipe_hash) DO UPDATE SET total_predictions=EXCLUDED.total_predictions,accuracy=EXCLUDED.accuracy,config_json=EXCLUDED.config_json RETURNING id""",
                (recipe_hash, symbol, timeframe, horizon, config_json, total_predictions, accuracy))
            return cur.fetchone()[0]

    def save_ml_recipe_predictions(self, run_id: int, predictions: list) -> None:
        if predictions:
            with self.get_connection() as conn, conn.cursor() as cur:
                cur.executemany("""INSERT INTO ml_recipe_predictions (run_id,timestamp,predicted_direction,actual_direction,confidence,was_correct,decision_hash)
                    VALUES (%s,%s,%s,%s,%s,%s,%s)""", [(run_id, p["timestamp"], p["predicted_direction"], p["actual_direction"], p["confidence"], p["was_correct"], p["decision_hash"]) for p in predictions])

    def get_recent_sentiment(self, hours=24) -> pd.DataFrame:
        with self.get_connection() as conn:
            return pd.read_sql("SELECT * FROM news_sentiment WHERE timestamp >= now()-(%s * interval '1 hour') ORDER BY timestamp DESC", conn, params=[hours])

    # Persistent state needed between hourly invocations.
    def create_analysis_run(self, message_id=None) -> int:
        with self.get_connection() as conn, conn.cursor() as cur:
            cur.execute("INSERT INTO analysis_runs (trigger_message_id,status) VALUES (%s,'running') RETURNING id", (message_id,))
            return cur.fetchone()[0]

    def finish_analysis_run(self, run_id, status, summary=None, error=None) -> None:
        with self.get_connection() as conn, conn.cursor() as cur:
            cur.execute("UPDATE analysis_runs SET status=%s,summary=%s::jsonb,error=%s,finished_at=now() WHERE id=%s", (status, self._json(summary or {}), error, run_id))

    def create_purchase_suggestion(self, data: dict) -> Optional[int]:
        with self.get_connection() as conn, conn.cursor() as cur:
            cur.execute("""INSERT INTO trade_suggestions (dedupe_key,symbol,pattern,confidence,entry_price,position_size,quantity,stop_loss,take_profit,context)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb) ON CONFLICT (dedupe_key) DO NOTHING RETURNING id""",
                (data["dedupe_key"], data["symbol"], data["pattern"], data["confidence"], data["entry_price"], data["position_size"], data["quantity"], data["stop_loss"], data["take_profit"], self._json(data.get("context", {}))))
            row = cur.fetchone(); return row[0] if row else None

    def claim_purchase_suggestion(self, suggestion_id: int) -> Optional[dict]:
        with self.get_connection() as conn, conn.cursor() as cur:
            cur.execute("""UPDATE trade_suggestions SET status='approval_in_progress' WHERE id=%s AND status='pending' AND expires_at>now()
                RETURNING id,symbol,pattern,confidence,entry_price,position_size,quantity,stop_loss,take_profit""", (suggestion_id,))
            row = cur.fetchone()
            return dict(zip([d.name for d in cur.description], row)) if row else None

    def release_purchase_suggestion(self, suggestion_id: int, error: str) -> None:
        with self.get_connection() as conn, conn.cursor() as cur:
            cur.execute("UPDATE trade_suggestions SET status='pending',execution_error=%s WHERE id=%s AND status='approval_in_progress'", (error, suggestion_id))

    def open_position(self, suggestion: dict, order_id: str, approved_by: str) -> int:
        with self.get_connection() as conn, conn.cursor() as cur:
            cur.execute("""INSERT INTO positions (suggestion_id,symbol,pattern,entry_price,quantity,position_size,stop_loss,take_profit,buy_order_id,approved_by)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""", (suggestion["id"], suggestion["symbol"], suggestion["pattern"], suggestion["entry_price"], suggestion["quantity"], suggestion["position_size"], suggestion["stop_loss"], suggestion["take_profit"], order_id, approved_by))
            position_id = cur.fetchone()[0]
            cur.execute("UPDATE trade_suggestions SET status='approved',approved_at=now(),approved_by=%s WHERE id=%s", (approved_by, suggestion["id"]))
            return position_id

    def get_open_positions(self) -> list[dict]:
        with self.get_connection() as conn, conn.cursor() as cur:
            cur.execute("SELECT * FROM positions WHERE status='open' ORDER BY created_at")
            names = [d.name for d in cur.description]
            return [dict(zip(names, row)) for row in cur.fetchall()]

    def claim_position_for_exit(self, position_id: int) -> Optional[dict]:
        """Reserves an exit so queue retries cannot submit two sell orders."""
        with self.get_connection() as conn, conn.cursor() as cur:
            cur.execute("UPDATE positions SET status='closing' WHERE id=%s AND status='open' RETURNING *", (position_id,))
            row = cur.fetchone()
            return dict(zip([d.name for d in cur.description], row)) if row else None

    def release_position_exit(self, position_id: int) -> None:
        with self.get_connection() as conn, conn.cursor() as cur:
            cur.execute("UPDATE positions SET status='open' WHERE id=%s AND status='closing'", (position_id,))

    def close_position(self, position_id, exit_price, sell_order_id, reason) -> Optional[dict]:
        with self.get_connection() as conn, conn.cursor() as cur:
            cur.execute("""UPDATE positions SET status='closed',exit_price=%s,sell_order_id=%s,exit_reason=%s,closed_at=now(),profit_loss=(%s-entry_price)*quantity
                WHERE id=%s AND status='closing' RETURNING *""", (exit_price, sell_order_id, reason, exit_price, position_id))
            row = cur.fetchone()
            return dict(zip([d.name for d in cur.description], row)) if row else None

    def save_model_training_run(self, data: dict) -> int:
        """Stores metadata only; model files remain local/deployable artifacts."""
        with self.get_connection() as conn, conn.cursor() as cur:
            cur.execute(
                """INSERT INTO model_training_runs
                (version,status,data_start,data_end,total_rows,metrics,model_sha256,scaler_sha256,backup_path,error)
                VALUES (%s,%s,%s,%s,%s,%s::jsonb,%s,%s,%s,%s) RETURNING id""",
                (data["version"], data["status"], data.get("data_start"), data.get("data_end"),
                 data.get("total_rows", 0), self._json(data.get("metrics", {})),
                 data.get("model_sha256"), data.get("scaler_sha256"), data.get("backup_path"), data.get("error")),
            )
            return cur.fetchone()[0]

    def mark_model_training_deployed(self, version: str, deployment_url: str) -> None:
        with self.get_connection() as conn, conn.cursor() as cur:
            cur.execute(
                """UPDATE model_training_runs SET status='deployed', deployment_url=%s, deployed_at=now()
                WHERE version=%s""", (deployment_url, version),
            )

    def get_recent_model_training_runs(self, limit: int = 10) -> list[dict]:
        with self.get_connection() as conn, conn.cursor() as cur:
            cur.execute(
                """SELECT version,status,data_start,data_end,total_rows,metrics,created_at,deployed_at,deployment_url,error
                FROM model_training_runs ORDER BY created_at DESC LIMIT %s""", (limit,),
            )
            columns = [d.name for d in cur.description]
            return [dict(zip(columns, row)) for row in cur.fetchall()]


# One driver in every environment. Local training and Vercel monitoring both
# use Supabase Postgres; the legacy SQLite file is used only by the one-off
# migration script. Keeping a single SQL dialect prevents SQLite from trying to
# execute PostgreSQL placeholders such as `%s`.
DatabaseManager = SupabaseDatabaseManager
