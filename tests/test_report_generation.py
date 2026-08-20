import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd
from flask import Flask
from openpyxl import Workbook

from app.routes import data_processing
from ending_files.generate_all_reports import generate_all_reports
from modules.report_generation import (
    CORRECTED_TABLES,
    CSV_CONTRACTS,
    EXCEL_REPORT_NAMES,
    ReportValidationError,
    expected_historical_periods,
    publish_staged_directories,
    validate_csv_outputs,
    validate_excel_outputs,
    validate_report_preflight,
)
from utils.report_generator import export_query_to_csv


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFINITIONS_PATH = PROJECT_ROOT / "ending_files" / "report_definitions.json"


class ReportGeneratorErrorTests(unittest.TestCase):
    def test_export_query_to_csv_raises_and_does_not_publish_on_query_error(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            output = Path(temporary_directory) / "report.csv"

            with self.assertRaises(Exception):
                export_query_to_csv(
                    "SELECT * FROM missing_table",
                    str(output),
                    database_path=":memory:",
                )

            self.assertFalse(output.exists())
            self.assertFalse(output.with_suffix(".csv.tmp").exists())

    def test_generate_all_reports_returns_failure_when_query_fails(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            with patch.dict(os.environ, {"DATABASE": ":memory:"}):
                result = generate_all_reports(
                    definitions_file=str(DEFINITIONS_PATH),
                    output_dir=temporary_directory,
                    period="202602",
                    specific_report="cuadro_nuevo",
                )

            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["successful"], [])
            self.assertEqual(result["failed"][0][0], "cuadro_nuevo")
            self.assertFalse(
                (Path(temporary_directory) / "202602" / "202602_cuadro_nuevo.csv").exists()
            )


class ReportPreflightTests(unittest.TestCase):
    def _create_database(self, path: Path, period: int) -> None:
        required_periods = expected_historical_periods(period)
        with sqlite3.connect(path) as connection:
            for table_name in (*CORRECTED_TABLES, "base_otros_conceptos"):
                connection.execute(
                    f'CREATE TABLE "{table_name}" (periodo INTEGER, value INTEGER)'
                )
                connection.execute(
                    f'INSERT INTO "{table_name}" VALUES (?, 1)',
                    (period,),
                )

            for table_name in ("base_subramos", "base_ramos"):
                connection.execute(
                    f'CREATE TABLE "{table_name}" (periodo INTEGER, cod_cia TEXT)'
                )
                connection.executemany(
                    f'INSERT INTO "{table_name}" VALUES (?, ?)',
                    [
                        (required_period, f"{company_code:04d}")
                        for required_period in required_periods
                        for company_code in (541, 686, 829)
                    ],
                )

    def test_preflight_accepts_current_tables_and_required_history(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            database = Path(temporary_directory) / "reports.sqlite"
            self._create_database(database, 202602)

            validate_report_preflight(database, 202602)

    def test_preflight_rejects_stale_current_table(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            database = Path(temporary_directory) / "reports.sqlite"
            self._create_database(database, 202602)
            with sqlite3.connect(database) as connection:
                connection.execute(
                    "UPDATE base_otros_conceptos SET periodo = 202601"
                )

            with self.assertRaisesRegex(ReportValidationError, "base_otros_conceptos"):
                validate_report_preflight(database, 202602)


class ReportOutputValidationTests(unittest.TestCase):
    def test_csv_validator_requires_exact_non_empty_contracts(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            period = "202602"
            for report_name, contract in CSV_CONTRACTS.items():
                row = {column: 1 for column in contract.columns}
                pd.DataFrame([row]).to_csv(
                    directory / f"{period}_{report_name}.csv",
                    sep=contract.separator,
                    index=False,
                )

            validated = validate_csv_outputs(directory, period)

            self.assertEqual(len(validated), len(CSV_CONTRACTS))

    def test_excel_validator_requires_exact_readable_workbooks(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            period = "202602"
            for report_name in EXCEL_REPORT_NAMES:
                workbook = Workbook()
                workbook.active["A1"] = report_name
                workbook.save(directory / f"{period}_{report_name}.xlsx")

            validated = validate_excel_outputs(directory, period)

            self.assertEqual(len(validated), len(EXCEL_REPORT_NAMES))

    def test_publish_replaces_official_directories_without_versions(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            staged_csv = root / "staged-csv"
            staged_excel = root / "staged-excel"
            official_csv = root / "official-csv"
            official_excel = root / "official-excel"
            for directory in (staged_csv, staged_excel, official_csv, official_excel):
                directory.mkdir()
            (staged_csv / "new.csv").write_text("new")
            (staged_excel / "new.xlsx").write_text("new")
            (official_csv / "old.csv").write_text("old")
            (official_excel / "old.xlsx").write_text("old")

            publish_staged_directories((
                (staged_csv, official_csv),
                (staged_excel, official_excel),
            ))

            self.assertEqual({path.name for path in official_csv.iterdir()}, {"new.csv"})
            self.assertEqual({path.name for path in official_excel.iterdir()}, {"new.xlsx"})
            self.assertFalse(list(root.glob(".*.backup-*")))

    def test_publish_restores_all_official_directories_on_failure(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            staged_csv = root / "staged-csv"
            missing_staged_excel = root / "missing-staged-excel"
            official_csv = root / "official-csv"
            official_excel = root / "official-excel"
            for directory in (staged_csv, official_csv, official_excel):
                directory.mkdir()
            (staged_csv / "new.csv").write_text("new")
            (official_csv / "old.csv").write_text("old")
            (official_excel / "old.xlsx").write_text("old")

            with self.assertRaises(ReportValidationError):
                publish_staged_directories((
                    (staged_csv, official_csv),
                    (missing_staged_excel, official_excel),
                ))

            self.assertEqual({path.name for path in official_csv.iterdir()}, {"old.csv"})
            self.assertEqual({path.name for path in official_excel.iterdir()}, {"old.xlsx"})
            self.assertFalse(list(root.glob(".*.backup-*")))


class ReportGenerationEndpointTests(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.register_blueprint(data_processing.data_processing_bp)
        self.client = self.app.test_client()

    @patch.dict(os.environ, {"DATABASE": "reports.sqlite"})
    @patch.object(data_processing, "validate_report_preflight")
    @patch.object(data_processing.subprocess, "run")
    def test_endpoint_reports_partial_csv_failure_without_technical_cause(
        self,
        run_mock,
        preflight_mock,
    ):
        run_mock.return_value.returncode = 1
        run_mock.return_value.stdout = "❌ cuadro_nuevo falló: no such table"
        run_mock.return_value.stderr = "traceback detail"

        response = self.client.post(
            "/api/generate-all-reports",
            json={"periodo": "202602"},
        )

        payload = response.get_json()
        self.assertEqual(response.status_code, 500)
        self.assertEqual(payload["status"], "partial")
        self.assertEqual(payload["failed_csv_reports"], ["cuadro_nuevo"])
        self.assertEqual(
            payload["error"],
            "No se generaron 1 archivos CSV: cuadro_nuevo.",
        )
        self.assertNotIn("no such table", payload["error"])
        preflight_mock.assert_called_once()


if __name__ == "__main__":
    unittest.main()
