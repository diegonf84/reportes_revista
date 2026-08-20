"""Tests for the open-folder endpoint path allow-list.

Phase 4 (lean) — item 8: provide an affordance to open the output folder
from the UI. The endpoint must only open directories that live under one
of the configured output roots. Anything outside the allow-list is
rejected with 403 to prevent arbitrary local file system access.
"""

import os
import unittest
from pathlib import Path
from unittest.mock import patch

from flask import Flask

from app.routes import data_processing


class OpenFolderEndpointTests(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.register_blueprint(
            data_processing.data_processing_bp,
            url_prefix="/data-processing",
        )
        self.client = self.app.test_client()
        self._excel_root = (
            Path(data_processing.project_root) / "excel_final_files"
        ).resolve()

    def _open_folder(self, path: str):
        return self.client.post(
            "/data-processing/api/open-folder",
            json={"path": path},
        )

    @patch("app.routes.data_processing.subprocess")
    def test_open_folder_accepts_path_inside_excel_output_root(self, subprocess_mock):
        with patch.dict(os.environ, {"DATABASE": ":memory:"}):
            response = self._open_folder(str(self._excel_root / "202602"))

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["success"])
        subprocess_mock.Popen.assert_called_once()

    @patch("app.routes.data_processing.subprocess")
    def test_open_folder_rejects_path_outside_allow_list(self, subprocess_mock):
        with patch.dict(os.environ, {"DATABASE": ":memory:"}):
            response = self._open_folder("/etc/passwd")

        self.assertEqual(response.status_code, 403)
        payload = response.get_json()
        self.assertFalse(payload["success"])
        self.assertIn("permitidos", payload["error"])
        subprocess_mock.Popen.assert_not_called()

    @patch("app.routes.data_processing.subprocess")
    def test_open_folder_rejects_non_existent_path(self, subprocess_mock):
        with patch.dict(os.environ, {"DATABASE": ":memory:"}):
            response = self._open_folder(str(self._excel_root / "999999"))

        self.assertEqual(response.status_code, 404)
        payload = response.get_json()
        self.assertFalse(payload["success"])
        subprocess_mock.Popen.assert_not_called()

    def test_open_folder_rejects_missing_path_argument(self):
        with patch.dict(os.environ, {"DATABASE": ":memory:"}):
            response = self.client.post(
                "/data-processing/api/open-folder",
                json={},
            )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.get_json()["success"])

    @patch("app.routes.data_processing.subprocess")
    def test_open_folder_rejects_relative_path_traversal(self, subprocess_mock):
        with patch.dict(os.environ, {"DATABASE": ":memory:"}):
            response = self._open_folder(
                str(self._excel_root / ".." / ".." / "etc")
            )

        self.assertEqual(response.status_code, 403)
        subprocess_mock.Popen.assert_not_called()


if __name__ == "__main__":
    unittest.main()
