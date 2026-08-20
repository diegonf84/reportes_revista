"""
Orchestrator: generate the 3 historical parquet files and upload them to S3.

Runs (in order):
    1. export_subramos_to_parquet
    2. export_ramos_to_parquet
    3. export_otros_conceptos_to_parquet
    4. upload_parquet_files  (reads AWS/S3 config from .env)

Usage:
    python export_parquet/run_all_and_upload.py
    python export_parquet/run_all_and_upload.py --max_period 202503

When --max_period is omitted, MAX(periodo) is read from datos_balance.
"""

import argparse
import logging
import os
import sqlite3
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

# Add parent directory to path to import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.common import setup_logging

from export_parquet.export_subramos_parquet import export_subramos_to_parquet
from export_parquet.export_ramos_parquet import export_ramos_to_parquet
from export_parquet.export_otros_conceptos_parquet import export_otros_conceptos_to_parquet
from export_parquet.upload_to_s3 import upload_parquet_files

logger = logging.getLogger(__name__)

OUTPUT_DIR = "output/parquet"
EXPECTED_PARQUET_FILES = 3


class S3ExportError(RuntimeError):
    """Raised when the complete Parquet export and upload cannot finish."""


def run_step(name: str, fn, *args, **kwargs) -> tuple[object, float]:
    """Run a step, log timing, re-raise on failure."""
    logger.info(f"\n{'#'*60}")
    logger.info(f"# STEP: {name}")
    logger.info(f"{'#'*60}")
    start = time.time()
    result = fn(*args, **kwargs)
    elapsed = time.time() - start
    logger.info(f"✅ {name} finished in {elapsed:.1f}s")
    return result, elapsed


def get_latest_period(database_path: str | os.PathLike) -> int:
    """Return the latest reporting period available in datos_balance."""
    path = Path(database_path).expanduser().resolve()
    if not path.is_file():
        raise ValueError("La base de datos configurada no existe.")

    with sqlite3.connect(path) as connection:
        row = connection.execute(
            "SELECT MAX(periodo) FROM datos_balance WHERE periodo IS NOT NULL"
        ).fetchone()

    if row is None or row[0] is None:
        raise ValueError("No hay períodos disponibles en datos_balance.")
    return int(row[0])


def run_all_and_upload(
    max_period: int | None = None,
    *,
    database_path: str | os.PathLike | None = None,
    output_dir: str | os.PathLike = OUTPUT_DIR,
) -> dict:
    """Generate all historical Parquet files and upload the complete set to S3."""
    load_dotenv()

    configured_database = database_path or os.getenv('DATABASE')
    if not configured_database:
        raise S3ExportError("La base de datos no está configurada.")
    selected_period = int(max_period or get_latest_period(configured_database))

    aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')
    aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
    region_name = os.getenv('AWS_REGION')
    bucket_name = os.getenv('S3_BUCKET')
    prefix = os.getenv('S3_PREFIX', '')

    if not aws_access_key or not aws_secret_key:
        raise S3ExportError("Las credenciales de AWS no están configuradas.")
    if not bucket_name:
        raise S3ExportError("El bucket S3 no está configurado.")

    output_path = str(Path(output_dir).expanduser().resolve())
    total_start = time.time()
    logger.info(f"\n{'='*60}")
    logger.info(f"RUN ALL & UPLOAD — max_period={selected_period}")
    logger.info(f"  Output dir: {output_path}")
    logger.info(f"  S3 bucket : {bucket_name}")
    logger.info(f"  S3 prefix : {prefix if prefix else '(root)'}")
    logger.info(f"{'='*60}")

    run_step(
        "export_subramos_to_parquet",
        export_subramos_to_parquet,
        selected_period,
        output_path,
    )
    run_step(
        "export_ramos_to_parquet",
        export_ramos_to_parquet,
        selected_period,
        output_path,
    )
    run_step(
        "export_otros_conceptos_to_parquet",
        export_otros_conceptos_to_parquet,
        selected_period,
        output_path,
    )

    upload_result, _ = run_step(
        "upload_parquet_files",
        upload_parquet_files,
        bucket_name=bucket_name,
        input_dir=output_path,
        prefix=prefix,
        aws_access_key=aws_access_key,
        aws_secret_key=aws_secret_key,
        region_name=region_name,
    )

    if (
        upload_result["success_count"] != EXPECTED_PARQUET_FILES
        or upload_result["failed_files"]
        or upload_result["missing_files"]
    ):
        raise S3ExportError("No se pudieron subir los tres archivos Parquet a S3.")

    total_elapsed = time.time() - total_start
    logger.info(f"\n{'='*60}")
    logger.info(f"ALL DONE in {total_elapsed/60:.1f} min")
    logger.info(f"{'='*60}\n")

    return {
        "periodo": str(selected_period),
        "uploaded_count": upload_result["success_count"],
        "uploaded_files": upload_result["uploaded_files"],
        "bucket": bucket_name,
        "prefix": prefix,
        "elapsed_seconds": round(total_elapsed, 1),
    }


def main():
    setup_logging()
    load_dotenv()

    parser = argparse.ArgumentParser(
        description='Generate the 3 historical parquet files and upload them to S3',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        '--max_period',
        type=int,
        required=False,
        help='Maximum period to include; defaults to MAX(periodo) in datos_balance',
    )
    args = parser.parse_args()

    try:
        run_all_and_upload(args.max_period)
    except (S3ExportError, ValueError) as error:
        logger.error("❌ %s", error)
        sys.exit(1)


if __name__ == "__main__":
    main()
