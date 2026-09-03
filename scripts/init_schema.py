"""Applies schema.sql to whatever database DATABASE_URL points at.

Usage:
    python scripts/init_schema.py

Reads the same DATABASE_URL env var as the app (app/db.py), so pointing
this at a fresh Railway Postgres is just a matter of setting that env var
before running it. Safe to re-run: schema.sql uses CREATE TABLE IF NOT EXISTS.
"""
import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from app.db import get_connection

SCHEMA_PATH = REPO_ROOT / "schema.sql"


def main():
    sql = SCHEMA_PATH.read_text()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
    print("schema applied")


if __name__ == "__main__":
    main()
