"""Tests for the user-facing message sanitization helper.

Phase 4 (lean) — item 6: separate user-facing functional message from
technical diagnostic details. ``flash_user_error`` must never leak the
``str(exception)`` into the user-visible flash and must log the full
technical detail server-side for operators.
"""

import unittest
from unittest.mock import patch

import flask
from flask import Flask

from utils.user_messages import flash_user_error, flash_user_success


def _flashed() -> list[tuple[str, str]]:
    """Return the flashes recorded in the current request's session."""
    return list(flask.session.get("_flashes", []))


class FlashUserErrorTests(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config["SECRET_KEY"] = "test-secret"

    def test_flash_user_error_flashes_only_user_facing_message(self):
        with self.app.test_request_context():
            flash_user_error(
                "No se pudo generar el Excel de Ramos.",
                technical=FileNotFoundError(
                    "/data/internal/excel/ramos/202602_cuadro_principal.xlsx"
                ),
            )

            flashed = _flashed()

        self.assertEqual(len(flashed), 1)
        category, message = flashed[0]
        self.assertEqual(category, "danger")
        self.assertEqual(message, "No se pudo generar el Excel de Ramos.")
        self.assertNotIn("/data/internal", message)
        self.assertNotIn("FileNotFoundError", message)

    def test_flash_user_error_logs_technical_exception_server_side(self):
        with self.app.test_request_context():
            with self.assertLogs(self.app.logger.name, level="ERROR") as cm:
                flash_user_error(
                    "No se pudo cargar el archivo.",
                    technical=ValueError("operador interno: foo"),
                )

        self.assertTrue(
            any("operador interno" in line for line in cm.output),
            cm.output,
        )

    def test_flash_user_error_without_technical_still_works(self):
        with self.app.test_request_context():
            flash_user_error("Acción cancelada por el usuario.")
            flashed = _flashed()

        self.assertEqual(flashed[0], ("danger", "Acción cancelada por el usuario."))


class FlashUserSuccessTests(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config["SECRET_KEY"] = "test-secret"

    def test_flash_user_success_default_category(self):
        with self.app.test_request_context():
            flash_user_success("Pipeline completo.")
            flashed = _flashed()

        self.assertEqual(flashed[0], ("success", "Pipeline completo."))


if __name__ == "__main__":
    unittest.main()
