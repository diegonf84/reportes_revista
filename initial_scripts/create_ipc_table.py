"""
Load IPC data from CSV into the database.

Creates two tables:
  - monthly_ipc_data: all monthly records as-is (periodo YYYYMM)
  - quarter_ipc_data: only end-of-quarter months, with periodo converted to YYYYQQ
    (march -> YY01, june -> YY02, september -> YY03, december -> YY04)

Reads data_base_carga_ipc.csv (semicolon-separated, comma as decimal separator).

Usage:
    python initial_scripts/create_ipc_table.py
"""

import pandas as pd
import os
import sys
from dotenv import load_dotenv
import sqlite3
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.common import setup_logging

logger = logging.getLogger(__name__)

load_dotenv()

database_path = os.getenv('DATABASE')

CSV_PATH = '/Users/diegofrigerio/Personal/repositorios/insurance_full_proyect/data_base_carga_ipc.csv'


# Map end-of-quarter month to project quarter code
MONTH_TO_QUARTER = {
    3: 1,   # march  -> Q1 (YYYY01)
    6: 2,   # june   -> Q2 (YYYY02)
    9: 3,   # september -> Q3 (YYYY03)
    12: 4,  # december  -> Q4 (YYYY04)
}


def main():
    logger.info(f"Reading CSV from {CSV_PATH}")
    df = pd.read_csv(CSV_PATH, sep=';', decimal=',')

    df['periodo'] = df['periodo'].astype(int)
    df['indice_ipc'] = df['indice_ipc'].astype(float)

    logger.info(f"Loaded {len(df):,} rows")
    logger.info(f"Periods: {df['periodo'].min()} - {df['periodo'].max()}")

    conn = sqlite3.connect(database_path)

    # --- monthly_ipc_data ---
    conn.execute('''
    CREATE TABLE IF NOT EXISTS monthly_ipc_data (
        periodo INTEGER NOT NULL,
        indice_ipc REAL NOT NULL
    );
    ''')
    conn.commit()

    df.to_sql('monthly_ipc_data', conn, if_exists='replace', index=False)
    count = conn.execute("SELECT COUNT(*) FROM monthly_ipc_data").fetchone()[0]
    logger.info(f"monthly_ipc_data: {count} rows saved")

    # --- quarter_ipc_data ---
    df['year'] = df['periodo'] // 100
    df['month'] = df['periodo'] % 100

    df_quarter = df[df['month'].isin(MONTH_TO_QUARTER.keys())].copy()
    df_quarter['periodo'] = df_quarter['year'] * 100 + df_quarter['month'].map(MONTH_TO_QUARTER)
    df_quarter = df_quarter[['periodo', 'indice_ipc']]

    conn.execute('''
    CREATE TABLE IF NOT EXISTS quarter_ipc_data (
        periodo INTEGER NOT NULL,
        indice_ipc REAL NOT NULL
    );
    ''')
    conn.commit()

    df_quarter.to_sql('quarter_ipc_data', conn, if_exists='replace', index=False)
    count = conn.execute("SELECT COUNT(*) FROM quarter_ipc_data").fetchone()[0]
    logger.info(f"quarter_ipc_data: {count} rows saved")

    conn.close()


if __name__ == "__main__":
    setup_logging()
    main()
