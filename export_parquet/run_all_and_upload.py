"""
Orchestrator: generate the 3 historical parquet files and upload them to S3.

Runs (in order):
    1. export_subramos_to_parquet
    2. export_ramos_to_parquet
    3. export_otros_conceptos_to_parquet
    4. upload_parquet_files  (reads AWS/S3 config from .env)

Usage:
    python export_parquet/run_all_and_upload.py --max_period 202503
"""

import argparse
import logging
import os
import sys
import time

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


def run_step(name: str, fn, *args, **kwargs) -> float:
    """Run a step, log timing, re-raise on failure."""
    logger.info(f"\n{'#'*60}")
    logger.info(f"# STEP: {name}")
    logger.info(f"{'#'*60}")
    start = time.time()
    fn(*args, **kwargs)
    elapsed = time.time() - start
    logger.info(f"✅ {name} finished in {elapsed:.1f}s")
    return elapsed


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
        required=True,
        help='Maximum period to include (e.g., 202503)',
    )
    args = parser.parse_args()
    max_period = args.max_period

    # Validate S3 config up-front so we fail fast before running ~long exports
    aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')
    aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
    region_name = os.getenv('AWS_REGION')
    bucket_name = os.getenv('S3_BUCKET')
    prefix = os.getenv('S3_PREFIX', '')

    if not aws_access_key or not aws_secret_key:
        logger.error("❌ AWS credentials not found in .env")
        sys.exit(1)
    if not bucket_name:
        logger.error("❌ S3_BUCKET not found in .env")
        sys.exit(1)

    total_start = time.time()
    logger.info(f"\n{'='*60}")
    logger.info(f"RUN ALL & UPLOAD — max_period={max_period}")
    logger.info(f"  Output dir: {OUTPUT_DIR}")
    logger.info(f"  S3 bucket : {bucket_name}")
    logger.info(f"  S3 prefix : {prefix if prefix else '(root)'}")
    logger.info(f"{'='*60}")

    run_step("export_subramos_to_parquet",
             export_subramos_to_parquet, max_period, OUTPUT_DIR)
    run_step("export_ramos_to_parquet",
             export_ramos_to_parquet, max_period, OUTPUT_DIR)
    run_step("export_otros_conceptos_to_parquet",
             export_otros_conceptos_to_parquet, max_period, OUTPUT_DIR)

    run_step(
        "upload_parquet_files",
        upload_parquet_files,
        bucket_name=bucket_name,
        input_dir=OUTPUT_DIR,
        prefix=prefix,
        aws_access_key=aws_access_key,
        aws_secret_key=aws_secret_key,
        region_name=region_name,
    )

    total_elapsed = time.time() - total_start
    logger.info(f"\n{'='*60}")
    logger.info(f"ALL DONE in {total_elapsed/60:.1f} min")
    logger.info(f"{'='*60}\n")


if __name__ == "__main__":
    main()
