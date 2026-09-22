"""One-off, idempotent-ish migration from the legacy SQLite file to Supabase.

Run only after applying supabase/migrations/0001_serverless_bot.sql:
    DATABASE_URL='...' py -3 scripts/migrate_sqlite_to_supabase.py bitcoin_patterns.db
"""
from __future__ import annotations

import json
import math
import os
import sqlite3
import sys
from pathlib import Path

import psycopg
from psycopg import sql

JSON_COLUMNS = {"market_data", "config_json", "features_used", "additional_context"}


def normalize(value, column):
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    if column in JSON_COLUMNS and value is not None:
        if not isinstance(value, str):
            return json.dumps(value, default=str)
        try:
            json.loads(value)
            return value
        except json.JSONDecodeError:
            return json.dumps({"legacy_raw": value})
    return value


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: py -3 scripts/migrate_sqlite_to_supabase.py path\\to\\bitcoin_patterns.db")
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise SystemExit("DATABASE_URL is required")
    sqlite_path = Path(sys.argv[1]).resolve()
    if not sqlite_path.is_file():
        raise SystemExit(f"SQLite database not found: {sqlite_path}")

    source = sqlite3.connect(sqlite_path)
    source.row_factory = sqlite3.Row
    with psycopg.connect(url, prepare_threshold=None) as destination:
        tables = [r[0] for r in source.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
        for table in tables:
            with destination.cursor() as cursor:
                cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name=%s", (table,))
                target_columns = {row[0] for row in cursor.fetchall()}
            source_columns = [row[1] for row in source.execute(f'PRAGMA table_info("{table}")')]
            columns = [name for name in source_columns if name in target_columns]
            if not columns:
                print(f"Skipping unknown table {table}")
                continue
            quoted_columns = ", ".join(f'"{name}"' for name in columns)
            rows = source.execute(f'SELECT {quoted_columns} FROM "{table}"').fetchall()
            if not rows:
                continue
            placeholders = sql.SQL(",").join(sql.Placeholder() for _ in columns)
            statement = sql.SQL("INSERT INTO {} ({}) VALUES ({}) ON CONFLICT DO NOTHING").format(
                sql.Identifier(table), sql.SQL(",").join(map(sql.Identifier, columns)), placeholders)
            with destination.cursor() as cursor:
                cursor.executemany(statement, [tuple(normalize(row[name], name) for name in columns) for row in rows])
            print(f"Migrated {len(rows)} rows from {table}")
        # Explicit legacy IDs were preserved so foreign keys still match. Advance
        # identity sequences afterwards, otherwise a subsequent insert can reuse
        # an already imported ID.
        for table in tables:
            with destination.cursor() as cursor:
                cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name=%s AND column_name='id'", (table,))
                if not cursor.fetchone():
                    continue
                cursor.execute(sql.SQL("""SELECT setval(pg_get_serial_sequence(%s, 'id'),
                    coalesce((select max(id) from {}), 1), (select count(*) > 0 from {}))""").format(
                    sql.Identifier(table), sql.Identifier(table)), (table,))
    source.close()


if __name__ == "__main__":
    main()
