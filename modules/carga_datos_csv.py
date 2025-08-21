"""
Module to load CSV data directly into datos_balance table.

This module provides functionality to load CSV data for specific companies
and periods when MDB files are incomplete or need supplementation.

Usage:
    python modules/carga_datos_csv.py <periodo> <csv_file_path>

Example:
    python modules/carga_datos_csv.py 202502 /path/to/company_data.csv

CSV Format Expected:
    cod_cia,periodo,cod_cuenta,cod_subramo,importe
    0415,202502,1.00.00.00.00.00.00.00,,13837123197
    0415,202502,1.01.00.00.00.00.00.00,,346027938
"""

import pandas as pd
import logging
import os
import argparse
from pathlib import Path
from dotenv import load_dotenv
from typing import Optional
from utils.other_functions import quita_nulos, verificar_tipos
from utils.db_functions import insert_info
from modules.common import validate_period, setup_logging, format_number

logger = logging.getLogger(__name__)


def validate_csv_structure(df: pd.DataFrame) -> None:
    """
    Validates that the CSV has the required columns and structure.
    
    Args:
        df (pd.DataFrame): DataFrame loaded from CSV
        
    Raises:
        ValueError: If required columns are missing or structure is invalid
    """
    required_columns = {'cod_cia', 'periodo', 'cod_cuenta', 'cod_subramo', 'importe'}
    
    if not required_columns.issubset(df.columns):
        missing_cols = required_columns - set(df.columns)
        raise ValueError(
            f"CSV is missing required columns: {missing_cols}. "
            f"Required columns: {required_columns}"
        )
    
    if len(df) == 0:
        raise ValueError("CSV file is empty")
    
    logger.info(f"CSV validation passed. Found {len(df):,} rows with required columns")


def load_csv_data(csv_file_path: str) -> pd.DataFrame:
    """
    Loads CSV data and performs initial validation.
    
    Args:
        csv_file_path (str): Path to the CSV file
        
    Returns:
        pd.DataFrame: Loaded and validated DataFrame
        
    Raises:
        FileNotFoundError: If CSV file doesn't exist
        ValueError: If CSV structure is invalid
    """
    csv_path = Path(csv_file_path)
    
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_file_path}")
    
    try:
        # Try to read with different encodings
        for encoding in ['utf-8', 'latin-1', 'cp1252']:
            try:
                df = pd.read_csv(csv_path, encoding=encoding)
                logger.info(f"Successfully loaded CSV with {encoding} encoding")
                break
            except UnicodeDecodeError:
                continue
        else:
            raise ValueError("Could not read CSV file with any supported encoding")
        
        validate_csv_structure(df)
        return df
        
    except pd.errors.EmptyDataError:
        raise ValueError("CSV file is empty")
    except pd.errors.ParserError as e:
        raise ValueError(f"Error parsing CSV file: {e}")


def transform_csv_data(df: pd.DataFrame, target_periodo: int) -> pd.DataFrame:
    """
    Transforms CSV data to match database schema and applies business rules.
    
    Args:
        df (pd.DataFrame): Raw CSV data
        target_periodo (int): Target period for validation
        
    Returns:
        pd.DataFrame: Transformed data ready for database insertion
        
    Raises:
        ValueError: If data transformation fails or validation errors occur
    """
    data = df.copy()
    
    # Validate that all periods in CSV match the target period
    unique_periods = data['periodo'].unique()
    if len(unique_periods) > 1:
        logger.warning(f"CSV contains multiple periods: {unique_periods}")
    
    # Check if target period exists in data
    if target_periodo not in unique_periods:
        logger.warning(
            f"Target period {target_periodo} not found in CSV. "
            f"CSV contains periods: {unique_periods}"
        )
    
    # Filter to only target period if multiple periods exist
    data = data[data['periodo'] == target_periodo].copy()
    
    if len(data) == 0:
        raise ValueError(
            f"No data found for period {target_periodo} in CSV. "
            f"Available periods: {unique_periods}"
        )
    
    logger.info(f"Processing {len(data):,} rows for period {target_periodo}")
    
    # Apply transformations following the same logic as carga_base_principal.py
    
    # 1. Handle cod_subramo nulls
    data['cod_subramo'] = data['cod_subramo'].map(quita_nulos)
    
    # 2. Zero-pad cod_cia to 4 digits
    data['cod_cia'] = data['cod_cia'].astype(str).str.zfill(4)
    
    # 3. Ensure periodo is integer
    data['periodo'] = data['periodo'].astype(int)
    
    # 4. Ensure importe is integer (round if necessary)
    data['importe'] = data['importe'].round().astype(int)
    
    # 5. Filter out zero amounts (following existing pattern)
    initial_count = len(data)
    data = data[data['importe'] != 0].reset_index(drop=True)
    filtered_count = initial_count - len(data)
    
    if filtered_count > 0:
        logger.info(f"Filtered out {filtered_count:,} rows with zero amounts")
    
    if len(data) == 0:
        raise ValueError("No data remaining after filtering zero amounts")
    
    # 6. Validate final data types
    tipos_esperados = {
        'cod_cia': 'object',
        'periodo': 'int64',
        'cod_subramo': 'object',
        'importe': 'int64',
        'cod_cuenta': 'object'
    }
    
    if not verificar_tipos(data, tipos_esperados):
        actual_types = dict(data.dtypes)
        logger.error(f"Expected types: {tipos_esperados}")
        logger.error(f"Actual types: {actual_types}")
        raise ValueError("Error in data types after transformation")
    
    logger.info(f"Data transformation successful. Final dataset: {len(data):,} rows")
    
    return data


def main(periodo: int, csv_file_path: str) -> None:
    """
    Main function to load CSV data into datos_balance table.
    
    Args:
        periodo (int): Target period in YYYYPP format
        csv_file_path (str): Path to the CSV file
    """
    # Validate inputs
    validate_period(periodo)
    
    # Load environment
    load_dotenv()
    database_path = os.getenv('DATABASE')
    
    if not database_path:
        raise ValueError("DATABASE environment variable not set")
    
    if not Path(database_path).exists():
        raise FileNotFoundError(f"Database file not found: {database_path}")
    
    logger.info(f"Starting CSV data load for period {periodo}")
    logger.info(f"CSV file: {csv_file_path}")
    logger.info(f"Database: {database_path}")
    
    try:
        # Load and validate CSV
        df_raw = load_csv_data(csv_file_path)
        logger.info(f"Loaded {len(df_raw):,} rows from CSV")
        
        # Transform data
        df_transformed = transform_csv_data(df_raw, periodo)
        
        # Get unique companies for logging
        unique_companies = df_transformed['cod_cia'].nunique()
        company_list = sorted(df_transformed['cod_cia'].unique())
        
        logger.info(f"Data ready for insertion:")
        logger.info(f"  - Period: {periodo}")
        logger.info(f"  - Companies: {unique_companies} ({', '.join(company_list)})")
        logger.info(f"  - Records: {format_number(len(df_transformed))}")
        logger.info(f"  - Total amount: {format_number(df_transformed['importe'].sum())}")
        
        # Insert data into database
        insert_info(
            data=df_transformed,
            database_path=database_path,
            table='datos_balance'
        )
        
        logger.info(f"✅ Successfully inserted {format_number(len(df_transformed))} rows into datos_balance")
        logger.info(f"   Period: {periodo}")
        logger.info(f"   Companies: {', '.join(company_list)}")
        
    except Exception as e:
        logger.error(f"❌ Error loading CSV data: {e}")
        raise


if __name__ == "__main__":
    setup_logging()
    
    parser = argparse.ArgumentParser(
        description='Load CSV data into datos_balance table',
        epilog="""
Examples:
  python modules/carga_datos_csv.py 202502 /path/to/company_data.csv
  python modules/carga_datos_csv.py 202501 ./supplemental_data.csv

CSV Format:
  cod_cia,periodo,cod_cuenta,cod_subramo,importe
  0415,202502,1.00.00.00.00.00.00.00,,13837123197
  0415,202502,1.01.00.00.00.00.00.00,,346027938

Notes:
  - Only records with importe != 0 will be inserted
  - cod_cia will be zero-padded to 4 digits
  - Data will be validated against database schema
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        'periodo',
        type=int,
        help='Target period in YYYYPP format (e.g., 202502 for June 2025)'
    )
    
    parser.add_argument(
        'csv_file_path',
        type=str,
        help='Path to the CSV file containing the data to load'
    )
    
    args = parser.parse_args()
    
    main(args.periodo, args.csv_file_path)