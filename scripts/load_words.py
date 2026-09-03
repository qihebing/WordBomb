"""Loads the ENABLE word list into the `words` table of whatever database
DATABASE_URL points at, using Postgres COPY for speed.

Usage:
    python scripts/load_words.py [path/to/enable1.txt]

Defaults to enable1.txt in the repo root if no path is given. Assumes the
words table is empty (this is how it was loaded locally) -- run this once
per fresh database, right after scripts/init_schema.py.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from app.db import get_connection


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "enable1.txt"
    with open(path) as f:
        words = [line.strip().lower() for line in f if line.strip()]

    with get_connection() as conn:
        with conn.cursor() as cur:
            with cur.copy("COPY words (word) FROM STDIN") as copy:
                for word in words:
                    copy.write_row((word,))

    print(f"loaded {len(words)} words")


if __name__ == "__main__":
    main()
