"""Load the UCI Online Retail xlsx into a SQLite database.

Reads data/online_retail.xlsx and writes it as table `raw` in
retail.db (created in this project folder). SQLite is built into
Python, so no database install is needed.

Run from the project folder:
    python scripts/load_data.py

Requires: pandas, openpyxl  (pip install pandas openpyxl)
"""
import sqlite3
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent.parent
XLSX = HERE / "data" / "online_retail.xlsx"
DB = HERE / "retail.db"


def main() -> None:
    df = pd.read_excel(XLSX)
    print(f"read {len(df):,} rows from {XLSX.name}")
    print(f"columns: {list(df.columns)}")
    with sqlite3.connect(DB) as conn:
        df.to_sql("raw", conn, if_exists="replace", index=False)
        rows, revenue = conn.execute(
            "SELECT COUNT(*), ROUND(SUM(Quantity * UnitPrice), 2) FROM raw"
        ).fetchone()
    print(f"wrote table `raw`: {rows:,} rows, revenue ${revenue:,.2f}")
    print("expected: 541,909 rows, revenue $9,747,747.93")
    print(f"database: {DB}")


if __name__ == "__main__":
    main()
