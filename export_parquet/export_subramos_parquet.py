"""
Export historical subramos data with corregida logic to parquet file.

This script generates a parquet file with 5 years of subramo-level data,
applying the same corregida logic as crea_tabla_subramos_corregida.py
to ALL periods and ALL concepts (from conceptos_reportes where es_subramo = TRUE).

Usage:
    python export_parquet/export_subramos_parquet.py --max_period 202503

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

from modules.common import validate_period, setup_logging

logger = logging.getLogger(__name__)


def calculate_periods(periodo_actual: int) -> dict:
    """Calculate all required periods based on current period"""
    periodo_str = str(periodo_actual)
    year = int(periodo_str[:4])
    quarter = int(periodo_str[4:])

    periods = {
        'actual': periodo_actual,
    }

    if quarter == 1:
        periods.update({
            'diciembre_actual': int(f"{year-1}04"),
            'junio_actual': int(f"{year-1}02"),
        })
    elif quarter == 2:
        periods.update({
            'diciembre_anterior': int(f"{year-1}04"),
            'junio_anterior': int(f"{year-1}02"),
        })
    elif quarter == 3:
        periods.update({
            'junio_actual': int(f"{year}02"),
        })
    elif quarter == 4:
        periods.update({
            'junio_actual': int(f"{year}02"),
        })

    return periods


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


def get_all_periods_needed(target_periods: list) -> list:
    """
    Get all periods needed including auxiliary periods for corregida calculations.
    """
    all_periods = set(target_periods)

    for periodo in target_periods:
        aux_periods = calculate_periods(periodo)
        all_periods.update(aux_periods.values())

    return sorted(list(all_periods))


def load_all_data(conn: sqlite3.Connection, all_periods: list, concepts: list) -> pd.DataFrame:
    """
    Load ALL data from datos_balance for all periods at once.
    This is much faster than querying multiple times.
    """
    logger.info(f"Loading data from datos_balance for {len(all_periods)} periods...")

    # Get parametros_reportes mappings
    params_query = """
    SELECT pr.*, cr.concepto
    FROM parametros_reportes pr
    JOIN conceptos_reportes cr ON pr.reporte = cr.reporte AND pr.referencia = cr.referencia
    WHERE cr.es_subramo = 1
    """
    params_df = pd.read_sql_query(params_query, conn)

    # Get all data from datos_balance for all periods
    periods_str = ','.join([str(p) for p in all_periods])

    base_query = f"""
    SELECT db.*, r.subramo_denominacion, r.ramo_denominacion, r.ramo_tipo
    FROM datos_balance db
    LEFT JOIN datos_ramos_subramos r USING (cod_subramo)
    WHERE db.periodo IN ({periods_str})
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

    # Aggregate by periodo, cod_cia, cod_subramo, subramo_denominacion, ramo_denominacion, ramo_tipo
    agg_dict = {col: 'sum' for col in concepts}
    aggregated = result.groupby(['periodo', 'cod_cia', 'cod_subramo', 'subramo_denominacion', 'ramo_denominacion', 'ramo_tipo'], as_index=False).agg(agg_dict)

    logger.info(f"Aggregated to {len(aggregated):,} rows (periodo, cod_cia, cod_subramo)")

    return aggregated


def get_data_for_period_and_cia(all_data: pd.DataFrame, periodo: int, cod_cias: list) -> pd.DataFrame:
    """Filter in-memory data for specific period and companies"""
    filtered = all_data[
        (all_data['periodo'] == periodo) &
        (all_data['cod_cia'].isin(cod_cias))
    ].copy()

    key_cols = ['cod_cia', 'cod_subramo', 'subramo_denominacion', 'ramo_denominacion', 'ramo_tipo']
    return filtered[key_cols + [col for col in filtered.columns if col not in ['periodo'] + key_cols]]


def apply_corregida_formula_march(actual_df, junio_df, diciembre_df, concepts: list):
    """Apply marzo corregida formula: actual - junio + diciembre"""
    result = actual_df[['cod_cia', 'cod_subramo', 'subramo_denominacion', 'ramo_denominacion', 'ramo_tipo']].copy()

    # Merge dataframes
    df = actual_df.merge(junio_df, on=['cod_cia', 'cod_subramo', 'subramo_denominacion', 'ramo_denominacion', 'ramo_tipo'], how='left', suffixes=('_act', '_jun'))
    df = df.merge(diciembre_df, on=['cod_cia', 'cod_subramo', 'subramo_denominacion', 'ramo_denominacion', 'ramo_tipo'], how='left', suffixes=('', '_dic'))

    # Apply formula to each concept: actual - junio + diciembre
    for concept in concepts:
        act = df[f'{concept}_act'].fillna(0) if f'{concept}_act' in df.columns else 0
        jun = df[f'{concept}_jun'].fillna(0) if f'{concept}_jun' in df.columns else 0
        dic = df[f'{concept}_dic'].fillna(0) if f'{concept}_dic' in df.columns else 0

        result[concept] = act - jun + dic

    return result


def apply_corregida_formula_june(actual_df, diciembre_df, junio_df, concepts: list):
    """Apply junio corregida formula: actual + diciembre - junio"""
    result = actual_df[['cod_cia', 'cod_subramo', 'subramo_denominacion', 'ramo_denominacion', 'ramo_tipo']].copy()

    # Merge dataframes
    df = actual_df.merge(diciembre_df, on=['cod_cia', 'cod_subramo', 'subramo_denominacion', 'ramo_denominacion', 'ramo_tipo'], how='left', suffixes=('_act', '_dic'))
    df = df.merge(junio_df, on=['cod_cia', 'cod_subramo', 'subramo_denominacion', 'ramo_denominacion', 'ramo_tipo'], how='left', suffixes=('', '_jun'))

    # Apply formula to each concept: actual + diciembre - junio
    for concept in concepts:
        act = df[f'{concept}_act'].fillna(0) if f'{concept}_act' in df.columns else 0
        dic = df[f'{concept}_dic'].fillna(0) if f'{concept}_dic' in df.columns else 0
        jun = df[f'{concept}_jun'].fillna(0) if f'{concept}_jun' in df.columns else 0

        result[concept] = act + dic - jun

    return result


def apply_corregida_formula_sept_dec(actual_df, junio_df, concepts: list):
    """Apply sept/dec corregida formula: actual - junio"""
    result = actual_df[['cod_cia', 'cod_subramo', 'subramo_denominacion', 'ramo_denominacion', 'ramo_tipo']].copy()

    # Merge dataframes
    df = actual_df.merge(junio_df, on=['cod_cia', 'cod_subramo', 'subramo_denominacion', 'ramo_denominacion', 'ramo_tipo'], how='left', suffixes=('_act', '_jun'))

    # Apply formula to each concept: actual - junio
    for concept in concepts:
        act = df[f'{concept}_act'].fillna(0) if f'{concept}_act' in df.columns else 0
        jun = df[f'{concept}_jun'].fillna(0) if f'{concept}_jun' in df.columns else 0

        result[concept] = act - jun

    return result


def get_data_for_period(all_data: pd.DataFrame, periodo: int, concepts: list) -> pd.DataFrame:
    """
    Get corregida data for a single period applying logic to ALL concepts.
    Works with in-memory data instead of querying database.
    """
    periodo_str = str(periodo)
    quarter = int(periodo_str[4:])

    periods = calculate_periods(periodo)
    logger.info(f"Processing period {periodo} (Q{quarter})")

    special_cias = ['0829', '0541', '0686']

    # Get data for special companies from in-memory dataframe
    if quarter == 1:  # Marzo
        actual = get_data_for_period_and_cia(all_data, periods['actual'], special_cias)
        junio = get_data_for_period_and_cia(all_data, periods['junio_actual'], special_cias)
        diciembre = get_data_for_period_and_cia(all_data, periods['diciembre_actual'], special_cias)

        special_df = apply_corregida_formula_march(actual, junio, diciembre, concepts)

    elif quarter == 2:  # Junio
        actual = get_data_for_period_and_cia(all_data, periods['actual'], special_cias)
        diciembre = get_data_for_period_and_cia(all_data, periods['diciembre_anterior'], special_cias)
        junio = get_data_for_period_and_cia(all_data, periods['junio_anterior'], special_cias)

        special_df = apply_corregida_formula_june(actual, diciembre, junio, concepts)

    elif quarter in [3, 4]:  # Septiembre o Diciembre
        actual = get_data_for_period_and_cia(all_data, periods['actual'], special_cias)
        junio = get_data_for_period_and_cia(all_data, periods['junio_actual'], special_cias)

        special_df = apply_corregida_formula_sept_dec(actual, junio, concepts)

    # Get data for normal companies (no corregida needed)
    all_cias = all_data['cod_cia'].unique()
    normal_cias = [cia for cia in all_cias if cia not in special_cias]

    normal_df = get_data_for_period_and_cia(all_data, periodo, normal_cias)

    # Combine special and normal companies
    combined_df = pd.concat([special_df, normal_df], ignore_index=True)

    # Add periodo column
    combined_df['periodo'] = periodo

    # Filter out zero primas_emitidas
    combined_df = combined_df[combined_df['primas_emitidas'] != 0]

    logger.info(f"  -> {len(combined_df):,} records retrieved")

    return combined_df


def add_quarter_and_date_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add fiscal quarter and date columns based on period.

    Fiscal year is July-June:
    - Period 03 (Sep) → Q1 fiscal, date: YYYY-09-01
    - Period 04 (Dec) → Q2 fiscal, date: YYYY-12-01
    - Period 01 (Mar) → Q3 fiscal, date: YYYY-03-01
    - Period 02 (Jun) → Q4 fiscal, date: YYYY-06-01
    """
    result_df = df.copy()

    # Map quarter number to fiscal quarter and month
    quarter_map = {
        3: {'fiscal_q': 'Q1', 'month': 9},   # September
        4: {'fiscal_q': 'Q2', 'month': 12},  # December
        1: {'fiscal_q': 'Q3', 'month': 3},   # March
        2: {'fiscal_q': 'Q4', 'month': 6}    # June
    }

    # Apply mapping
    result_df['fiscal_quarter'] = result_df['periodo'].apply(
        lambda p: quarter_map[int(str(p)[4:])]['fiscal_q']
    )

    result_df['period_date'] = result_df['periodo'].apply(
        lambda p: pd.Timestamp(year=int(str(p)[:4]), month=quarter_map[int(str(p)[4:])]['month'], day=1)
    )

    logger.info("Added fiscal_quarter and period_date columns")
    return result_df


def add_current_period_columns(df: pd.DataFrame, concepts: list) -> pd.DataFrame:
    """
    Add "_current" columns showing quarter-only values (not cumulative).

    Logic based on fiscal year July-June:
    - Period 03: current = P03 (already Q1 only: Jul+Aug+Sep)
    - Period 04: current = P04 - P03 (Q2 only: Oct+Nov+Dec)
    - Period 01: current = P01 - P04_prev_year (Q3 only: Jan+Feb+Mar)
    - Period 02: current = P02 - P01 (Q4 only: Apr+May+Jun)
    """
    result_df = df.copy()

    # Create lookup dictionary for fast access: (periodo, cod_cia, cod_subramo) -> row_index
    df_indexed = df.set_index(['periodo', 'cod_cia', 'cod_subramo'])

    # For each row, calculate current values
    for idx, row in df.iterrows():
        periodo = row['periodo']
        cod_cia = row['cod_cia']
        cod_subramo = row['cod_subramo']

        periodo_str = str(periodo)
        year = int(periodo_str[:4])
        quarter = int(periodo_str[4:])

        # Determine the previous period based on fiscal year logic
        if quarter == 3:  # Sep: already Q1, no subtraction needed
            for concept in concepts:
                result_df.loc[idx, f'{concept}_current'] = row[concept]

        elif quarter == 4:  # Dec: subtract Sep of same year
            prev_periodo = int(f"{year}03")
            try:
                prev_row = df_indexed.loc[(prev_periodo, cod_cia, cod_subramo)]
                for concept in concepts:
                    result_df.loc[idx, f'{concept}_current'] = row[concept] - prev_row[concept]
            except KeyError:
                # If previous period not found, use current value as fallback
                for concept in concepts:
                    result_df.loc[idx, f'{concept}_current'] = row[concept]

        elif quarter == 1:  # Mar: subtract Dec of previous year
            prev_periodo = int(f"{year-1}04")
            try:
                prev_row = df_indexed.loc[(prev_periodo, cod_cia, cod_subramo)]
                for concept in concepts:
                    result_df.loc[idx, f'{concept}_current'] = row[concept] - prev_row[concept]
            except KeyError:
                # If previous period not found, use current value as fallback
                for concept in concepts:
                    result_df.loc[idx, f'{concept}_current'] = row[concept]

        elif quarter == 2:  # Jun: subtract Mar of same year
            prev_periodo = int(f"{year}01")
            try:
                prev_row = df_indexed.loc[(prev_periodo, cod_cia, cod_subramo)]
                for concept in concepts:
                    result_df.loc[idx, f'{concept}_current'] = row[concept] - prev_row[concept]
            except KeyError:
                # If previous period not found, use current value as fallback
                for concept in concepts:
                    result_df.loc[idx, f'{concept}_current'] = row[concept]

    logger.info(f"Added _current columns for {len(concepts)} concepts")
    return result_df


def export_subramos_to_parquet(max_period: int, output_dir: str = "output/parquet") -> None:
    """Export historical subramos data with corregida logic to parquet file"""
    load_dotenv()
    database_path = os.getenv('DATABASE')

    with sqlite3.connect(database_path) as conn:
        # Get concepts list from conceptos_reportes
        query = """
        SELECT DISTINCT concepto
        FROM conceptos_reportes
        WHERE es_subramo = 1
        ORDER BY concepto
        """
        concepts_df = pd.read_sql_query(query, conn)
        concepts = concepts_df['concepto'].tolist()
        logger.info(f"Found {len(concepts)} concepts: {concepts}")

        # Generate period list
        target_periods = generate_period_list(max_period)
        logger.info(f"Target periods: {len(target_periods)} periods from {target_periods[0]} to {target_periods[-1]}")

        # Get all periods needed (including auxiliary for corregida)
        all_periods = get_all_periods_needed(target_periods)
        logger.info(f"All periods needed (including auxiliary): {len(all_periods)} periods")

        # Load ALL data at once
        all_data = load_all_data(conn, all_periods, concepts)

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    # Process all periods (working with in-memory data)
    all_data_list = []

    for periodo in target_periods:
        try:
            df = get_data_for_period(all_data, periodo, concepts)
            all_data_list.append(df)
        except Exception as e:
            logger.error(f"Error processing period {periodo}: {e}")
            logger.warning(f"Skipping period {periodo}")
            continue

    # Combine all data
    if not all_data_list:
        raise ValueError("No data was retrieved for any period")

    combined_df = pd.concat(all_data_list, ignore_index=True)

    # Add fiscal quarter and date columns
    logger.info("Adding fiscal quarter and date columns...")
    combined_df = add_quarter_and_date_columns(combined_df)

    # Calculate "_current" columns (quarter-only values, not cumulative)
    logger.info("Calculating _current columns for quarter-only values...")
    combined_df = add_current_period_columns(combined_df, concepts)

    # Add company names from datos_companias
    # Note: cod_cia in datos_balance is string like '0002', in datos_companias is int like 2
    with sqlite3.connect(database_path) as conn:
        companies_query = "SELECT cod_cia, nombre_corto, tipo_cia FROM datos_companias"
        companies_df = pd.read_sql_query(companies_query, conn)

    # Convert cod_cia to int for matching
    combined_df['cod_cia_int'] = combined_df['cod_cia'].astype(int)
    combined_df = combined_df.merge(companies_df, left_on='cod_cia_int', right_on='cod_cia', how='left', suffixes=('', '_comp'))
    combined_df.drop(columns=['cod_cia_int', 'cod_cia_comp'], inplace=True)

    logger.info(f"\n{'='*60}")
    logger.info(f"FINAL COMBINED DATA:")
    logger.info(f"  Total records: {len(combined_df):,}")
    logger.info(f"  Periods: {combined_df['periodo'].nunique()} unique")
    logger.info(f"  Companies: {combined_df['cod_cia'].nunique()} unique")
    logger.info(f"  Subramos: {combined_df['cod_subramo'].nunique()} unique")
    logger.info(f"  Concepts: {len(concepts)} concepts")
    logger.info(f"{'='*60}\n")

    # Save to parquet
    output_path = os.path.join(output_dir, "subramos_historico.parquet")
    combined_df.to_parquet(output_path, index=False, engine='pyarrow')

    logger.info(f"✅ Parquet file saved: {output_path}")
    logger.info(f"   File size: {os.path.getsize(output_path) / 1024 / 1024:.2f} MB")


def main():
    """Main entry point"""
    setup_logging()

    parser = argparse.ArgumentParser(
        description='Export historical subramos data with corregida logic to parquet',
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

    export_subramos_to_parquet(args.max_period, args.output_dir)


if __name__ == "__main__":
    main()
