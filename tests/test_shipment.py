"""Unit tests for ``modules.shipment``."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from modules import shipment


def _populate_source(source_dir: Path, period: str, slugs: list[str]) -> list[Path]:
    """Create empty ``.xlsx`` files for each slug under ``source_dir/<period>``."""
    period_dir = source_dir / period
    period_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for slug in slugs:
        path = period_dir / f"{period}_{slug}.xlsx"
        path.write_bytes(b"xlsx")
        paths.append(path)
    return paths


class PeriodToShipmentDirTests(unittest.TestCase):
    def test_quarter_1(self):
        with patch.object(shipment, "SHIPMENT_BASE_DIR", Path("/tmp/base")):
            target = shipment.period_to_shipment_dir("202601")
        self.assertEqual(target, Path("/tmp/base/2026-1/envios"))

    def test_quarter_2(self):
        with patch.object(shipment, "SHIPMENT_BASE_DIR", Path("/tmp/base")):
            target = shipment.period_to_shipment_dir("202602")
        self.assertEqual(target, Path("/tmp/base/2026-2/envios"))

    def test_invalid_quarter_raises_value_error(self):
        with patch.object(shipment, "SHIPMENT_BASE_DIR", Path("/tmp/base")):
            with self.assertRaises(ValueError):
                shipment.period_to_shipment_dir("202605")

    def test_wrong_length_raises_value_error(self):
        with patch.object(shipment, "SHIPMENT_BASE_DIR", Path("/tmp/base")):
            with self.assertRaises(ValueError):
                shipment.period_to_shipment_dir("20261")

    def test_non_digit_raises_value_error(self):
        with patch.object(shipment, "SHIPMENT_BASE_DIR", Path("/tmp/base")):
            with self.assertRaises(ValueError):
                shipment.period_to_shipment_dir("2026aa")


class MappingDisjointnessTests(unittest.TestCase):
    def test_excluded_and_mapping_are_disjoint(self):
        self.assertEqual(
            shipment.SHIPMENT_EXCLUDED.intersection(shipment.SHIPMENT_FILE_MAPPING),
            set(),
        )


class PrepareShipmentTests(unittest.TestCase):
    PERIOD = "202601"
    MAPPED_SLUGS = list(shipment.SHIPMENT_FILE_MAPPING.keys())

    def _setup(self) -> tuple[Path, Path]:
        source_root = Path(tempfile.mkdtemp(prefix="shipment_src_"))
        dest_root = Path(tempfile.mkdtemp(prefix="shipment_dst_"))
        _populate_source(source_root, self.PERIOD, self.MAPPED_SLUGS + ["apertura_por_subramo"])
        return source_root, dest_root

    def _patch_paths(self, source_root: Path, dest_root: Path):
        return (
            patch.object(shipment, "EXCEL_FINAL_DIR", source_root),
            patch.object(shipment, "SHIPMENT_BASE_DIR", dest_root),
        )

    def test_copies_mapped_files_and_skips_excluded(self):
        source_root, dest_root = self._setup()
        patch_src, patch_dest = self._patch_paths(source_root, dest_root)
        with patch_src, patch_dest:
            result = shipment.prepare_shipment(self.PERIOD)

        self.assertEqual(result["destination"], str(dest_root / "2026-1" / "envios"))
        self.assertEqual(len(result["copied"]), len(self.MAPPED_SLUGS))
        self.assertEqual(result["skipped"], [f"{self.PERIOD}_apertura_por_subramo.xlsx"])
        self.assertEqual(result["failed"], [])

        expected_names = {
            f"2026-1 {shipment.SHIPMENT_FILE_MAPPING[slug]}.xlsx"
            for slug in self.MAPPED_SLUGS
        }
        actual_names = set(result["copied"])
        self.assertEqual(actual_names, expected_names)

        destination_dir = dest_root / "2026-1" / "envios"
        self.assertTrue(destination_dir.exists())
        for name in actual_names:
            self.assertTrue((destination_dir / name).exists())

    def test_creates_destination_directory_when_missing(self):
        source_root, dest_root = self._setup()
        non_existing_dest = dest_root / "deep" / "nested"
        self.assertFalse(non_existing_dest.exists())

        patch_src, patch_dest = self._patch_paths(source_root, non_existing_dest)
        with patch_src, patch_dest:
            result = shipment.prepare_shipment(self.PERIOD)

        self.assertTrue(Path(result["destination"]).exists())
        self.assertEqual(Path(result["destination"]), non_existing_dest / "2026-1" / "envios")

    def test_overwrites_existing_files_in_destination(self):
        source_root, dest_root = self._setup()
        destination_dir = dest_root / "2026-1" / "envios"
        destination_dir.mkdir(parents=True, exist_ok=True)

        target_name = f"2026-1 {shipment.SHIPMENT_FILE_MAPPING['cuadro_principal']}.xlsx"
        existing_target = destination_dir / target_name
        existing_target.write_bytes(b"stale-content")
        original_mtime = existing_target.stat().st_mtime

        patch_src, patch_dest = self._patch_paths(source_root, dest_root)
        with patch_src, patch_dest:
            shipment.prepare_shipment(self.PERIOD)

        self.assertTrue(existing_target.exists())
        self.assertNotEqual(existing_target.read_bytes(), b"stale-content")
        # shutil.copy2 preserves mtime; verify the source mtime propagated.
        source_file = source_root / self.PERIOD / f"{self.PERIOD}_cuadro_principal.xlsx"
        self.assertEqual(existing_target.stat().st_mtime, source_file.stat().st_mtime)
        # Sanity: the old mtime must have been overwritten.
        self.assertNotEqual(existing_target.stat().st_mtime, original_mtime)

    def test_unknown_slug_is_reported_as_failed(self):
        source_root = Path(tempfile.mkdtemp(prefix="shipment_unknown_"))
        dest_root = Path(tempfile.mkdtemp(prefix="shipment_dst_"))
        _populate_source(source_root, self.PERIOD, ["reporte_misterioso"])

        patch_src, patch_dest = self._patch_paths(source_root, dest_root)
        with patch_src, patch_dest:
            result = shipment.prepare_shipment(self.PERIOD)

        self.assertEqual(len(result["failed"]), 1)
        failure = result["failed"][0]
        self.assertEqual(failure["source"], f"{self.PERIOD}_reporte_misterioso.xlsx")
        self.assertIn("reporte_misterioso", failure["error"])
        self.assertEqual(result["copied"], [])
        self.assertEqual(result["skipped"], [])

    def test_missing_source_directory_raises_file_not_found(self):
        source_root = Path(tempfile.mkdtemp(prefix="shipment_empty_"))
        dest_root = Path(tempfile.mkdtemp(prefix="shipment_dst_"))
        patch_src, patch_dest = self._patch_paths(source_root, dest_root)

        with patch_src, patch_dest:
            with self.assertRaises(FileNotFoundError):
                shipment.prepare_shipment(self.PERIOD)

    def test_invalid_period_raises_value_error(self):
        with self.assertRaises(ValueError):
            shipment.prepare_shipment("2026-1")


if __name__ == "__main__":
    unittest.main()
