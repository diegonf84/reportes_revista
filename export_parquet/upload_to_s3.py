"""
Upload parquet files to AWS S3 bucket.

This script uploads the generated parquet files to an S3 bucket for use
with Superset or other data visualization tools.

Reads S3_BUCKET and S3_PREFIX from .env file.

Usage:
    python export_parquet/upload_to_s3.py
"""

import boto3
import os
import sys
from dotenv import load_dotenv
import logging

# Add parent directory to path to import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.common import setup_logging

logger = logging.getLogger(__name__)


def upload_file_to_s3(file_path: str, bucket_name: str, s3_key: str,
                       aws_access_key: str, aws_secret_key: str, region_name: str = None) -> bool:
    """
    Upload a file to S3 bucket.

    Args:
        file_path: Local path to the file
        bucket_name: Name of the S3 bucket
        s3_key: Key (path) in S3 where file will be stored
        aws_access_key: AWS access key ID
        aws_secret_key: AWS secret access key
        region_name: AWS region (optional)

    Returns:
        True if upload successful, False otherwise
    """
    try:
        # Create S3 client
        s3_client = boto3.client(
            's3',
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key,
            region_name=region_name
        )

        # Get file size for progress
        file_size = os.path.getsize(file_path)
        logger.info(f"Uploading {file_path} ({file_size / 1024 / 1024:.2f} MB) to s3://{bucket_name}/{s3_key}")

        # Upload file
        s3_client.upload_file(file_path, bucket_name, s3_key)

        logger.info(f"✅ Successfully uploaded to s3://{bucket_name}/{s3_key}")
        return True

    except Exception as e:
        logger.error(f"❌ Error uploading {file_path}: {e}")
        return False


def upload_parquet_files(bucket_name: str, input_dir: str = "output/parquet",
                         prefix: str = "", aws_access_key: str = None,
                         aws_secret_key: str = None, region_name: str = None) -> None:
    """
    Upload all parquet files to S3.

    Args:
        bucket_name: Name of the S3 bucket
        input_dir: Directory containing parquet files
        prefix: Optional prefix (folder path) in S3
        aws_access_key: AWS access key ID
        aws_secret_key: AWS secret access key
        region_name: AWS region
    """
    # Define parquet files to upload
    parquet_files = [
        "subramos_historico.parquet",
        "ramos_historico.parquet",
        "otros_conceptos_historico.parquet"
    ]

    logger.info(f"\n{'='*60}")
    logger.info(f"UPLOADING PARQUET FILES TO S3")
    logger.info(f"  Bucket: {bucket_name}")
    logger.info(f"  Prefix: {prefix if prefix else '(root)'}")
    logger.info(f"  Input directory: {input_dir}")
    logger.info(f"{'='*60}\n")

    success_count = 0
    failed_files = []

    for filename in parquet_files:
        file_path = os.path.join(input_dir, filename)

        # Check if file exists
        if not os.path.exists(file_path):
            logger.warning(f"⚠️  File not found: {file_path} - skipping")
            continue

        # Construct S3 key
        s3_key = os.path.join(prefix, filename) if prefix else filename

        # Upload file
        if upload_file_to_s3(file_path, bucket_name, s3_key,
                            aws_access_key, aws_secret_key, region_name):
            success_count += 1
        else:
            failed_files.append(filename)

    # Summary
    logger.info(f"\n{'='*60}")
    logger.info(f"UPLOAD SUMMARY:")
    logger.info(f"  ✅ Successfully uploaded: {success_count} files")
    if failed_files:
        logger.info(f"  ❌ Failed to upload: {len(failed_files)} files")
        for filename in failed_files:
            logger.info(f"     - {filename}")
    logger.info(f"{'='*60}\n")


def main():
    """Main entry point"""
    setup_logging()

    # Load environment variables
    load_dotenv()

    # Get config from .env
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

    # Upload files
    upload_parquet_files(
        bucket_name=bucket_name,
        input_dir='output/parquet',
        prefix=prefix,
        aws_access_key=aws_access_key,
        aws_secret_key=aws_secret_key,
        region_name=region_name
    )


if __name__ == "__main__":
    main()
