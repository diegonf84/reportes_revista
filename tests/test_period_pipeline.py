import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from flask import Flask

from app.routes import data_processing
from modules.period_pipeline import (
    PIPELINE_STAGES,
    TABLE_STAGES,
    PipelineBusyError,
    PipelineExecutionError,
    pipeline_lock,
    run_period_pipeline,
    run_tables_pipeline,
)


PERIOD = 202602


def create_database(path: Path) -> None:
    with sqlite3.connect(path) as connection:
        connection.execute(
            "CREATE TABLE datos_balance (periodo INTEGER NOT NULL, importe INTEGER)"
        )
        connection.execute("INSERT INTO datos_balance VALUES (?, 1)", (PERIOD,))


def successful_actions(calls: list[tuple[str, int]]):
    return {
        stage.key: (
            lambda period, stage_key=stage.key: calls.append((stage_key, period))
        )
        for stage in PIPELINE_STAGES
    }


class PeriodPipelineTests(unittest.TestCase):
    def test_tables_pipeline_runs_only_table_stages_with_one_period(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            database = root / "reports.sqlite"
            create_database(database)
            calls = []

            result = run_tables_pipeline(
                PERIOD,
                database,
                root,
                actions=successful_actions(calls),
                validate_outputs=False,
            )

            self.assertEqual(
                calls,
                [(stage.key, PERIOD) for stage in TABLE_STAGES],
            )
            self.assertNotIn("reports", {stage["key"] for stage in result["stages"]})

    def test_pipeline_runs_every_stage_in_order_with_one_period(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            database = root / "reports.sqlite"
            create_database(database)
            calls = []

            result = run_period_pipeline(
                PERIOD,
                database,
                root,
                actions=successful_actions(calls),
                validate_outputs=False,
            )

            self.assertEqual(
                calls,
                [(stage.key, PERIOD) for stage in PIPELINE_STAGES],
            )
            self.assertTrue(
                all(stage["status"] == "completed" for stage in result["stages"])
            )

    def test_pipeline_stops_at_first_failure_and_leaves_later_stages_incomplete(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            database = root / "reports.sqlite"
            create_database(database)
            calls = []
            actions = successful_actions(calls)

            def fail_base(period):
                calls.append(("base_tables", period))
                raise RuntimeError("technical detail")

            actions["base_tables"] = fail_base

            with self.assertRaises(PipelineExecutionError) as captured:
                run_period_pipeline(
                    PERIOD,
                    database,
                    root,
                    actions=actions,
                    validate_outputs=False,
                )

            statuses = {stage["key"]: stage["status"] for stage in captured.exception.statuses}
            self.assertEqual(
                calls,
                [("recent_periods", PERIOD), ("base_tables", PERIOD)],
            )
            self.assertEqual(statuses["recent_periods"], "completed")
            self.assertEqual(statuses["base_tables"], "failed")
            self.assertEqual(statuses["concepts"], "pending")
            self.assertNotIn("technical detail", str(captured.exception))

    def test_database_lock_rejects_a_second_pipeline(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            database = Path(temporary_directory) / "reports.sqlite"
            create_database(database)

            with pipeline_lock(database, PERIOD):
                with self.assertRaises(PipelineBusyError):
                    with pipeline_lock(database, PERIOD):
                        self.fail("The second lock must not be acquired")

class PeriodPipelineEndpointTests(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.register_blueprint(data_processing.data_processing_bp)
        self.client = self.app.test_client()

    @patch.object(data_processing, "render_template", return_value="full-processing")
    def test_full_processing_uses_an_independent_page(self, render_mock):
        response = self.client.get("/full-processing")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_data(as_text=True), "full-processing")
        render_mock.assert_called_once_with("data_processing/full_processing.html")

    @patch.dict(os.environ, {"DATABASE": "reports.sqlite"})
    @patch.object(data_processing, "run_tables_pipeline")
    def test_all_tables_endpoint_uses_one_period_without_reports(self, run_mock):
        run_mock.return_value = {
            "periodo": str(PERIOD),
            "stages": [
                {"key": stage.key, "status": "completed"}
                for stage in TABLE_STAGES
            ],
        }

        response = self.client.post(
            "/api/generate-all-tables",
            json={"periodo": PERIOD},
        )

        payload = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(payload["success"])
        self.assertNotIn("reports", {stage["key"] for stage in payload["stages"]})
        run_mock.assert_called_once_with(PERIOD, "reports.sqlite", data_processing.project_root)

    @patch.dict(os.environ, {"DATABASE": "reports.sqlite"})
    @patch.object(data_processing, "run_period_pipeline")
    def test_full_pipeline_endpoint_returns_stage_statuses(self, run_mock):
        run_mock.return_value = {
            "periodo": str(PERIOD),
            "stages": [{"key": "reports", "status": "completed"}],
            "reports": {"csv_count": 13, "excel_count": 14},
        }

        response = self.client.post(
            "/api/process-full-period",
            json={"periodo": PERIOD},
        )

        payload = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["periodo"], str(PERIOD))
        run_mock.assert_called_once()

    @patch.dict(os.environ, {"DATABASE": "reports.sqlite"})
    @patch.object(
        data_processing,
        "run_period_pipeline",
        side_effect=PipelineBusyError("Ya hay un pipeline activo sobre esta base de datos."),
    )
    def test_full_pipeline_endpoint_reports_busy_database(self, _):
        response = self.client.post(
            "/api/process-full-period",
            json={"periodo": PERIOD},
        )

        payload = response.get_json()
        self.assertEqual(response.status_code, 409)
        self.assertEqual(payload["status"], "busy")


if __name__ == "__main__":
    unittest.main()
