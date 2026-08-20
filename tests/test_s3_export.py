import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from flask import Flask

from app.routes import data_processing
from export_parquet import run_all_and_upload as s3_export
from export_parquet import upload_to_s3
from export_parquet import export_otros_conceptos_parquet
from export_parquet import export_ramos_parquet
from export_parquet import export_subramos_parquet


PERIOD = 202602
UPLOAD_RESULT = {
    "uploaded_files": [
        "subramos_historico.parquet",
        "ramos_historico.parquet",
        "otros_conceptos_historico.parquet",
    ],
    "failed_files": [],
    "missing_files": [],
    "success_count": 3,
}


class S3ExportTests(unittest.TestCase):
    def test_all_exports_use_the_same_six_year_period_window(self):
        for exporter in (
            export_subramos_parquet,
            export_ramos_parquet,
            export_otros_conceptos_parquet,
        ):
            periods = exporter.generate_period_list(202503)
            self.assertEqual(periods[0], 201902)
            self.assertEqual(periods[-1], 202503)
            self.assertEqual(len(periods), 26)

    @patch.object(upload_to_s3, "upload_file_to_s3", return_value=True)
    def test_upload_summary_requires_the_three_expected_files(self, upload_mock):
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            for filename in UPLOAD_RESULT["uploaded_files"]:
                (directory / filename).write_bytes(b"parquet")

            result = upload_to_s3.upload_parquet_files(
                bucket_name="reports-bucket",
                input_dir=str(directory),
                prefix="parquet",
                aws_access_key="key",
                aws_secret_key="secret",
            )

        self.assertEqual(result, UPLOAD_RESULT)
        self.assertEqual(upload_mock.call_count, 3)

    def test_latest_period_comes_from_datos_balance(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            database = Path(temporary_directory) / "reports.sqlite"
            with sqlite3.connect(database) as connection:
                connection.execute("CREATE TABLE datos_balance (periodo INTEGER)")
                connection.executemany(
                    "INSERT INTO datos_balance VALUES (?)",
                    [(202504,), (PERIOD,), (202601,)],
                )

            self.assertEqual(s3_export.get_latest_period(database), PERIOD)

    @patch.object(s3_export, "upload_parquet_files", return_value=UPLOAD_RESULT)
    @patch.object(s3_export, "export_otros_conceptos_to_parquet")
    @patch.object(s3_export, "export_ramos_to_parquet")
    @patch.object(s3_export, "export_subramos_to_parquet")
    def test_run_all_uses_one_period_and_uploads_complete_contract(
        self,
        subramos_mock,
        ramos_mock,
        otros_mock,
        upload_mock,
    ):
        with tempfile.TemporaryDirectory() as temporary_directory:
            with patch.dict(os.environ, {
                "AWS_ACCESS_KEY_ID": "key",
                "AWS_SECRET_ACCESS_KEY": "secret",
                "AWS_REGION": "us-east-1",
                "S3_BUCKET": "reports-bucket",
                "S3_PREFIX": "parquet",
            }):
                result = s3_export.run_all_and_upload(
                    PERIOD,
                    database_path="configured.sqlite",
                    output_dir=temporary_directory,
                )

        for export_mock in (subramos_mock, ramos_mock, otros_mock):
            export_mock.assert_called_once_with(PERIOD, str(Path(temporary_directory).resolve()))
        self.assertEqual(result["uploaded_count"], 3)
        self.assertEqual(result["periodo"], str(PERIOD))
        upload_mock.assert_called_once()

    @patch.object(s3_export, "upload_parquet_files", return_value={
        "uploaded_files": ["subramos_historico.parquet"],
        "failed_files": ["ramos_historico.parquet"],
        "missing_files": ["otros_conceptos_historico.parquet"],
        "success_count": 1,
    })
    @patch.object(s3_export, "export_otros_conceptos_to_parquet")
    @patch.object(s3_export, "export_ramos_to_parquet")
    @patch.object(s3_export, "export_subramos_to_parquet")
    def test_incomplete_upload_is_not_reported_as_success(self, *_):
        with patch.dict(os.environ, {
            "AWS_ACCESS_KEY_ID": "key",
            "AWS_SECRET_ACCESS_KEY": "secret",
            "S3_BUCKET": "reports-bucket",
        }):
            with self.assertRaises(s3_export.S3ExportError):
                s3_export.run_all_and_upload(
                    PERIOD,
                    database_path="configured.sqlite",
                )


class S3ExportEndpointTests(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.register_blueprint(data_processing.data_processing_bp)
        self.client = self.app.test_client()

    @patch.object(data_processing, "pipeline_lock")
    @patch.object(data_processing, "run_all_and_upload")
    @patch.object(data_processing, "get_latest_period", return_value=PERIOD)
    def test_endpoint_uses_latest_period_without_user_input(
        self,
        latest_period_mock,
        run_mock,
        lock_mock,
    ):
        run_mock.return_value = {
            "periodo": str(PERIOD),
            "uploaded_count": 3,
            "uploaded_files": UPLOAD_RESULT["uploaded_files"],
            "bucket": "reports-bucket",
            "prefix": "parquet",
            "elapsed_seconds": 1.0,
        }

        with patch.dict(os.environ, {"DATABASE": "reports.sqlite"}):
            response = self.client.post("/api/upload-parquet-to-s3", json={})

        payload = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(payload["success"])
        latest_period_mock.assert_called_once_with("reports.sqlite")
        lock_mock.assert_called_once_with("reports.sqlite", PERIOD)
        run_mock.assert_called_once_with(PERIOD, database_path="reports.sqlite")


if __name__ == "__main__":
    unittest.main()
