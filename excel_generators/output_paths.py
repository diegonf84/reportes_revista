"""Resolve default and staged paths for Excel report generators."""

from pathlib import Path


def resolve_report_directories(
    period: str,
    csv_dir: str | None = None,
    output_dir: str | None = None,
) -> tuple[str, str]:
    project_root = Path(__file__).resolve().parent.parent
    resolved_csv_dir = Path(csv_dir) if csv_dir else project_root / "ending_files" / period
    resolved_output_dir = (
        Path(output_dir) if output_dir else project_root / "excel_final_files" / period
    )
    resolved_output_dir.mkdir(parents=True, exist_ok=True)
    return str(resolved_csv_dir), str(resolved_output_dir)
