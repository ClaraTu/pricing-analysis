"""Run sql/01_cleaning.sql against retail.db and print every result.

The SQL file mixes CREATE TABLE statements with SELECT checks, so this
runner executes it statement by statement and prints the output of
each SELECT. Safe to re-run: it drops `orders` and `daily_revenue`
first, so the CREATE TABLE statements do not fail on a second run.

Run from the project folder, after scripts/load_data.py:
    python scripts/run_sql.py

Requires: nothing beyond Python's built-in sqlite3.
"""
import re
import sqlite3
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
SQL_FILE = HERE / "sql" / "01_cleaning.sql"
DB = HERE / "retail.db"


def strip_comments(sql: str) -> str:
    lines = [line for line in sql.splitlines() if not line.strip().startswith("--")]
    return "\n".join(lines)


def main() -> None:
    if not DB.exists():
        raise SystemExit(
            f"{DB.name} not found. Run `python scripts/load_data.py` first."
        )
    sql = strip_comments(SQL_FILE.read_text(encoding="utf-8"))
    statements = [s.strip() for s in sql.split(";") if s.strip()]
    with sqlite3.connect(DB) as conn:
        conn.execute("DROP TABLE IF EXISTS orders")
        conn.execute("DROP TABLE IF EXISTS daily_revenue")
        for stmt in statements:
            cur = conn.execute(stmt)
            if stmt.lstrip().upper().startswith("SELECT"):
                rows = cur.fetchall()
                cols = [d[0] for d in cur.description]
                print(" | ".join(cols))
                for row in rows:
                    print(" | ".join(str(v) for v in row))
                print()
            else:
                print(f"ok: {stmt.splitlines()[0][:60]}...")
        conn.commit()
    print("done. Tables now in retail.db: raw, orders, daily_revenue")


if __name__ == "__main__":
    main()
