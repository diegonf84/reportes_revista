"""
Export all datos_balance data for a specific company to parquet and upload to S3.

Queries all rows from datos_balance for the given cod_cia, joins ramo/subramo names,
saves as parquet, and uploads to s3://insurance-visualization-proyect/companies/{cod_cia}/all_data.parquet

Usage:
    python export_parquet/export_company_to_s3.py --cod_cia 0002
"""

import pandas as pd
import os
import sys
import argparse
from dotenv import load_dotenv
import sqlite3
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.common import setup_logging
from export_parquet.upload_to_s3 import upload_file_to_s3

logger = logging.getLogger(__name__)

BUCKET_NAME = "insurance-visualization-proyect"
S3_PREFIX = "companies"


def export_company_to_parquet(cod_cia: str, output_dir: str = "output/companies") -> str:
    """Export all datos_balance data for a company to parquet. Returns the output file path."""
    load_dotenv()
    database_path = os.getenv('DATABASE')

    with sqlite3.connect(database_path) as conn:
        query = """
        SELECT db.*, r.ramo_nombre_corto, r.subramo_nombre_corto
        FROM datos_balance db
        LEFT JOIN datos_ramos_subramos r USING (cod_subramo)
        WHERE db.cod_cia = ?
        """
        df = pd.read_sql_query(query, conn, params=[cod_cia])

    if df.empty:
        logger.error(f"No data found for cod_cia={cod_cia}")
        sys.exit(1)

    logger.info(f"Loaded {len(df):,} rows for company {cod_cia}")
    logger.info(f"  Periods: {df['periodo'].nunique()} unique")
    logger.info(f"  Subramos: {df['cod_subramo'].nunique()} unique")

    company_dir = os.path.join(output_dir, cod_cia)
    os.makedirs(company_dir, exist_ok=True)

    output_path = os.path.join(company_dir, "all_data.parquet")
    df.to_parquet(output_path, index=False, engine='pyarrow')

    logger.info(f"Parquet saved: {output_path} ({os.path.getsize(output_path) / 1024 / 1024:.2f} MB)")
    return output_path


def main():
    setup_logging()
    load_dotenv()

    parser = argparse.ArgumentParser(
        description='Export company data to parquet and upload to S3'
    )
    parser.add_argument(
        '--cod_cia',
        type=str,
        required=True,
        help='Company code (e.g., 0002)'
    )
    args = parser.parse_args()

    # Generate parquet
    output_path = export_company_to_parquet(args.cod_cia)

    # Upload to S3
    aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')
    aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
    region_name = os.getenv('AWS_REGION')

    if not aws_access_key or not aws_secret_key:
        logger.error("AWS credentials not found in .env")
        sys.exit(1)

    s3_key = f"{S3_PREFIX}/{args.cod_cia}/all_data.parquet"

    upload_file_to_s3(
        file_path=output_path,
        bucket_name=BUCKET_NAME,
        s3_key=s3_key,
        aws_access_key=aws_access_key,
        aws_secret_key=aws_secret_key,
        region_name=region_name
    )


if __name__ == "__main__":
    main()
