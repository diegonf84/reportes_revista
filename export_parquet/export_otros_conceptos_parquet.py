"""
Export historical otros_conceptos (company-level financial data) to parquet file.

This script generates a parquet file with 5 years of company-level financial data,
using concepts from conceptos_reportes where es_subramo = FALSE.

These are balance/financial concepts like:
- resultado_tecnico, resultado_financiero
- deudas_con_asegurados, disponibilidades
- inversiones, patrimonio_neto, etc.

NO corregida logic needed - these are company-level totals.

Usage:
    python export_parquet/export_otros_conceptos_parquet.py --max_period 202503

This will generate data from 202002 to 202503 (5 complete years).
"""

import pandas as pd
import os
import sys
import argparse
from dotenv import load_dotenv
import sqlite3
import logging

# Add parent directory to path to import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.common import setup_logging

logger = logging.getLogger(__name__)


def generate_period_list(max_period: int) -> list:
    """Generate list of periods for 5 complete years"""
    max_year = int(str(max_period)[:4])
    start_year = max_year - 5

    periods = []
    for year in range(start_year, max_year + 1):
        for quarter in [1, 2, 3, 4]:
            period = int(f"{year}{quarter:02d}")
            if period >= int(f"{start_year}02") and period <= max_period:
                periods.append(period)

    return periods


def load_all_data(conn: sqlite3.Connection, all_periods: list, concepts: list) -> pd.DataFrame:
    """
    Load ALL data from datos_balance for all periods at once.
    Apply concept mappings and aggregate by cod_cia and periodo.
    """
    logger.info(f"Loading data from datos_balance for {len(all_periods)} periods...")

    # Get parametros_reportes mappings for otros_conceptos
    params_query = """
    SELECT pr.*, cr.concepto
    FROM parametros_reportes pr
    JOIN conceptos_reportes cr ON pr.reporte = cr.reporte AND pr.referencia = cr.referencia
    WHERE cr.es_subramo = 0
    """
    params_df = pd.read_sql_query(params_query, conn)

    # Get all data from datos_balance for all periods
    periods_str = ','.join([str(p) for p in all_periods])

    base_query = f"""
    SELECT *
    FROM datos_balance
    WHERE periodo IN ({periods_str})
    """

    logger.info(f"Executing query to load all data...")
    base_df = pd.read_sql_query(base_query, conn)
    logger.info(f"Loaded {len(base_df):,} rows from datos_balance")

    # Apply concept mappings to create columns
    result = base_df.copy()

    for concepto in concepts:
        mapping_df = params_df[params_df['concepto'] == concepto]
        if len(mapping_df) > 0:
            mapping = dict(zip(mapping_df['cod_cuenta'], mapping_df['signo']))
            result[concepto] = result['cod_cuenta'].map(mapping).fillna(0) * result['importe']
        else:
            result[concepto] = 0

    # Aggregate by periodo and cod_cia (company level, no ramo/subramo)
    agg_dict = {col: 'sum' for col in concepts}
    aggregated = result.groupby(['periodo', 'cod_cia'], as_index=False).agg(agg_dict)

    logger.info(f"Aggregated to {len(aggregated):,} rows (periodo, cod_cia)")

    return aggregated


def export_otros_conceptos_to_parquet(max_period: int, output_dir: str = "output/parquet") -> None:
    """Export historical otros_conceptos data to parquet file"""
    load_dotenv()
    database_path = os.getenv('DATABASE')

    with sqlite3.connect(database_path) as conn:
        # Get concepts list from conceptos_reportes where es_subramo = FALSE
        query = """
        SELECT DISTINCT concepto
        FROM conceptos_reportes
        WHERE es_subramo = 0
        ORDER BY concepto
        """
        concepts_df = pd.read_sql_query(query, conn)
        concepts = concepts_df['concepto'].tolist()
        logger.info(f"Found {len(concepts)} company-level concepts: {concepts}")

        # Generate period list
        target_periods = generate_period_list(max_period)
        logger.info(f"Target periods: {len(target_periods)} periods from {target_periods[0]} to {target_periods[-1]}")

        # Load ALL data at once and aggregate
        all_data = load_all_data(conn, target_periods, concepts)

    # Filter to only target periods (all_data already has them, but just to be sure)
    final_data = all_data[all_data['periodo'].isin(target_periods)].copy()

    # Add company names from datos_companias
    # Note: cod_cia in datos_balance is string like '0002', in datos_companias is int like 2
    with sqlite3.connect(database_path) as conn:
        companies_query = "SELECT cod_cia, nombre_corto, tipo_cia FROM datos_companias"
        companies_df = pd.read_sql_query(companies_query, conn)

    # Convert cod_cia to int for matching
    final_data['cod_cia_int'] = final_data['cod_cia'].astype(int)
    final_data = final_data.merge(companies_df, left_on='cod_cia_int', right_on='cod_cia', how='left', suffixes=('', '_comp'))
    final_data.drop(columns=['cod_cia_int', 'cod_cia_comp'], inplace=True)

    logger.info(f"\n{'='*60}")
    logger.info(f"FINAL DATA:")
    logger.info(f"  Total records: {len(final_data):,}")
    logger.info(f"  Periods: {final_data['periodo'].nunique()} unique")
    logger.info(f"  Companies: {final_data['cod_cia'].nunique()} unique")
    logger.info(f"  Concepts: {len(concepts)} concepts")
    logger.info(f"{'='*60}\n")

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    # Save to parquet
    output_path = os.path.join(output_dir, "otros_conceptos_historico.parquet")
    final_data.to_parquet(output_path, index=False, engine='pyarrow')

    logger.info(f"✅ Parquet file saved: {output_path}")
    logger.info(f"   File size: {os.path.getsize(output_path) / 1024 / 1024:.2f} MB")


def main():
    """Main entry point"""
    setup_logging()

    parser = argparse.ArgumentParser(
        description='Export historical otros_conceptos (company-level financial data) to parquet',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '--max_period',
        type=int,
        required=True,
        help='Maximum period to include (e.g., 202503)'
    )

    parser.add_argument(
        '--output_dir',
        type=str,
        default='output/parquet',
        help='Output directory for parquet files (default: output/parquet)'
    )

    args = parser.parse_args()

    export_otros_conceptos_to_parquet(args.max_period, args.output_dir)


if __name__ == "__main__":
    main()
