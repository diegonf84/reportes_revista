import io
import sqlite3
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import pandas as pd
from flask import Flask

from app.routes import data_processing
from modules import period_reload
from modules.period_reload import (
    PeriodReloadError,
    cancel_staged_reload,
    confirm_staged_reload,
    stage_reload_candidate,
    validate_reload_archive,
)


PERIOD = 202602
FILENAME = "2026-2.zip"


def build_zip_bytes(members: dict[str, bytes]) -> bytes:
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, content in members.items():
            archive.writestr(name, content)
    return stream.getvalue()


def balance_dataframe(rows: list[tuple]) -> pd.DataFrame:
    return pd.DataFrame(
        rows,
        columns=["cod_cia", "periodo", "cod_cuenta", "cod_subramo", "importe"],
    )


def create_reload_database(path: Path) -> None:
    with sqlite3.connect(path) as connection:
        connection.execute(
            """
            CREATE TABLE datos_balance (
                cod_cia TEXT,
                periodo INTEGER,
                cod_cuenta TEXT,
                cod_subramo TEXT,
                importe INTEGER
            )
            """
        )
        connection.executemany(
            "INSERT INTO datos_balance VALUES (?, ?, ?, ?, ?)",
            [
                ("0001", PERIOD, "A", "01", 10),
                ("0002", PERIOD, "B", "02", 20),
                ("0003", 202601, "C", "03", 30),
            ],
        )
        for table_name in period_reload.DERIVED_PERIOD_TABLES:
            connection.execute(
                f'CREATE TABLE "{table_name}" (periodo INTEGER, value INTEGER)'
            )
            connection.executemany(
                f'INSERT INTO "{table_name}" VALUES (?, ?)',
                [(PERIOD, 1), (202601, 2)],
            )
        for table_name in period_reload.CORRECTED_CURRENT_TABLES:
            connection.execute(
                f'CREATE TABLE "{table_name}" (periodo INTEGER, value INTEGER)'
            )
            connection.execute(
                f'INSERT INTO "{table_name}" VALUES (?, ?)',
                (PERIOD, 1),
            )


class ReloadArchiveValidationTests(unittest.TestCase):
    def test_archive_requires_exact_single_expected_mdb(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            archive_path = Path(temporary_directory) / FILENAME
            archive_path.write_bytes(
                build_zip_bytes({"../2026-2.mdb": b"mdb", "extra.txt": b"unexpected"})
            )

            with self.assertRaisesRegex(PeriodReloadError, "únicamente 2026-2.mdb"):
                validate_reload_archive(archive_path, PERIOD)

    @patch.object(period_reload.subprocess, "run")
    def test_mdb_export_failure_is_propagated(self, run_mock):
        run_mock.return_value.returncode = 1
        run_mock.return_value.stderr = b"invalid database"
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            csv_path = root / "Balance.csv"

            with self.assertRaisesRegex(PeriodReloadError, "No se pudo leer"):
                period_reload._export_balance_table(root / "source.mdb", csv_path)

            self.assertFalse(csv_path.exists())


class StagedReloadTests(unittest.TestCase):
    def setUp(self):
        self.new_data = balance_dataframe(
            [
                ("0001", PERIOD, "A", "01", 100),
                ("0004", PERIOD, "D", "04", 400),
            ]
        )
        self.company_names = {"0001": "One", "0004": "Four"}

    def _stage(self, upload_directory: Path):
        source = io.BytesIO(build_zip_bytes({"2026-2.mdb": b"candidate-source"}))
        with patch.object(
            period_reload,
            "read_reload_dataframe",
            return_value=(self.new_data, self.company_names),
        ):
            return stage_reload_candidate(source, PERIOD, FILENAME, upload_directory)

    def test_invalid_candidate_does_not_replace_current_zip(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            upload_directory = Path(temporary_directory)
            official_zip = upload_directory / FILENAME
            official_zip.write_bytes(b"current-source")
            invalid = io.BytesIO(build_zip_bytes({"wrong.mdb": b"invalid"}))

            with self.assertRaises(PeriodReloadError):
                stage_reload_candidate(invalid, PERIOD, FILENAME, upload_directory)

            self.assertEqual(official_zip.read_bytes(), b"current-source")

    def test_cancel_discards_candidate_and_preserves_current_zip(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            upload_directory = Path(temporary_directory)
            official_zip = upload_directory / FILENAME
            official_zip.write_bytes(b"current-source")
            candidate = self._stage(upload_directory)

            cancel_staged_reload(candidate.token, PERIOD, upload_directory)

            self.assertEqual(official_zip.read_bytes(), b"current-source")
            self.assertFalse(
                (upload_directory / ".reload-staging" / candidate.token).exists()
            )

    def test_confirm_replaces_period_and_invalidates_derived_tables(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            upload_directory = root / "uploads"
            upload_directory.mkdir()
            official_zip = upload_directory / FILENAME
            official_mdb = upload_directory / "2026-2.mdb"
            official_zip.write_bytes(b"current-source")
            official_mdb.write_bytes(b"old-extracted-source")
            database = root / "reports.sqlite"
            create_reload_database(database)
            candidate = self._stage(upload_directory)
            candidate_bytes = (
                upload_directory / ".reload-staging" / candidate.token / FILENAME
            ).read_bytes()

            with patch.object(
                period_reload,
                "read_reload_dataframe",
                return_value=(self.new_data, self.company_names),
            ):
                result = confirm_staged_reload(
                    candidate.token,
                    PERIOD,
                    upload_directory,
                    database,
                )

            self.assertEqual(result["old_rows"], 2)
            self.assertEqual(result["new_rows"], 2)
            self.assertEqual(result["new_companies"], 2)
            self.assertEqual(official_zip.read_bytes(), candidate_bytes)
            self.assertFalse(official_mdb.exists())
            self.assertFalse(
                (upload_directory / ".reload-staging" / candidate.token).exists()
            )

            with sqlite3.connect(database) as connection:
                target_rows = connection.execute(
                    "SELECT cod_cia, importe FROM datos_balance WHERE periodo = ? ORDER BY cod_cia",
                    (PERIOD,),
                ).fetchall()
                other_rows = connection.execute(
                    "SELECT COUNT(*) FROM datos_balance WHERE periodo = 202601"
                ).fetchone()[0]
                self.assertEqual(target_rows, [("0001", 100), ("0004", 400)])
                self.assertEqual(other_rows, 1)
                for table_name in period_reload.DERIVED_PERIOD_TABLES:
                    target_count = connection.execute(
                        f'SELECT COUNT(*) FROM "{table_name}" WHERE periodo = ?',
                        (PERIOD,),
                    ).fetchone()[0]
                    self.assertEqual(target_count, 0)
                for table_name in period_reload.CORRECTED_CURRENT_TABLES:
                    count = connection.execute(
                        f'SELECT COUNT(*) FROM "{table_name}"'
                    ).fetchone()[0]
                    self.assertEqual(count, 0)

    def test_commit_failure_restores_database_zip_and_extracted_mdb(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            upload_directory = root / "uploads"
            upload_directory.mkdir()
            official_zip = upload_directory / FILENAME
            official_mdb = upload_directory / "2026-2.mdb"
            official_zip.write_bytes(b"current-source")
            official_mdb.write_bytes(b"old-extracted-source")
            database = root / "reports.sqlite"
            create_reload_database(database)
            candidate = self._stage(upload_directory)

            with patch.object(
                period_reload,
                "read_reload_dataframe",
                return_value=(self.new_data, self.company_names),
            ), patch.object(
                period_reload,
                "_commit_connection",
                side_effect=sqlite3.OperationalError("forced commit failure"),
            ):
                with self.assertRaises(sqlite3.OperationalError):
                    confirm_staged_reload(
                        candidate.token,
                        PERIOD,
                        upload_directory,
                        database,
                    )

            self.assertEqual(official_zip.read_bytes(), b"current-source")
            self.assertEqual(official_mdb.read_bytes(), b"old-extracted-source")
            self.assertTrue(
                (upload_directory / ".reload-staging" / candidate.token / FILENAME).exists()
            )
            with sqlite3.connect(database) as connection:
                target_rows = connection.execute(
                    "SELECT cod_cia, importe FROM datos_balance WHERE periodo = ? ORDER BY cod_cia",
                    (PERIOD,),
                ).fetchall()
                self.assertEqual(target_rows, [("0001", 10), ("0002", 20)])
                for table_name in period_reload.CORRECTED_CURRENT_TABLES:
                    count = connection.execute(
                        f'SELECT COUNT(*) FROM "{table_name}"'
                    ).fetchone()[0]
                    self.assertEqual(count, 1)

    def test_unrelated_reload_keeps_current_corrected_tables(self):
        with sqlite3.connect(":memory:") as connection:
            for table_name in period_reload.CORRECTED_CURRENT_TABLES:
                connection.execute(
                    f'CREATE TABLE "{table_name}" (periodo INTEGER, value INTEGER)'
                )
                connection.execute(
                    f'INSERT INTO "{table_name}" VALUES (202602, 1)'
                )

            invalidated = period_reload._invalidate_derived_tables(connection, 202601)

            self.assertEqual(invalidated, [])
            for table_name in period_reload.CORRECTED_CURRENT_TABLES:
                count = connection.execute(
                    f'SELECT COUNT(*) FROM "{table_name}"'
                ).fetchone()[0]
                self.assertEqual(count, 1)


class ReloadEndpointTests(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.register_blueprint(data_processing.data_processing_bp)
        self.client = self.app.test_client()

    @patch.dict("os.environ", {"DATABASE": "reports.sqlite"})
    @patch.object(data_processing, "confirm_staged_reload")
    def test_confirm_endpoint_reports_verified_counts(self, confirm_mock):
        confirm_mock.return_value = {
            "old_rows": 10,
            "old_companies": 2,
            "new_rows": 12,
            "new_companies": 3,
            "invalidated_tables": ["base_subramos"],
        }

        response = self.client.post(
            "/api/confirm-reload-period",
            json={"periodo": PERIOD, "reload_token": "a" * 32},
        )

        payload = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["status"], "confirmed")
        self.assertEqual(payload["new_rows"], 12)
        self.assertEqual(payload["new_companies"], 3)

    @patch.dict("os.environ", {"DATABASE": "reports.sqlite"})
    @patch.object(
        data_processing,
        "confirm_staged_reload",
        side_effect=sqlite3.OperationalError("forced failure"),
    )
    def test_confirm_endpoint_reports_reversion_without_technical_detail(self, _):
        response = self.client.post(
            "/api/confirm-reload-period",
            json={"periodo": PERIOD, "reload_token": "a" * 32},
        )

        payload = response.get_json()
        self.assertEqual(response.status_code, 500)
        self.assertEqual(payload["status"], "reverted")
        self.assertIn("restauraron", payload["error"])
        self.assertNotIn("forced failure", payload["error"])

    @patch.object(data_processing, "cancel_staged_reload")
    def test_cancel_endpoint_reports_no_changes(self, cancel_mock):
        response = self.client.post(
            "/api/cancel-reload-period",
            json={"periodo": PERIOD, "reload_token": "a" * 32},
        )

        payload = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["status"], "cancelled")
        self.assertIn("No se modificaron", payload["message"])
        cancel_mock.assert_called_once()


if __name__ == "__main__":
    unittest.main()
