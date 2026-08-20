"""Validation and publication controls for report generation."""

from __future__ import annotations

import shutil
import sqlite3
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping

import pandas as pd
from openpyxl import load_workbook

from modules.common import validate_period


SPECIAL_COMPANY_CODES = (541, 686, 829)
CORRECTED_TABLES = (
    "base_subramos_corregida_actual",
    "base_ramos_corregida_actual",
    "base_cias_corregida_actual",
)
HISTORICAL_TABLES = ("base_subramos", "base_ramos")


@dataclass(frozen=True)
class CsvContract:
    separator: str
    columns: tuple[str, ...]


CSV_CONTRACTS: Mapping[str, CsvContract] = {
    "cuadro_nuevo": CsvContract(
        ",",
        (
            "tipo_cia", "nombre_corto", "cod_cia", "primas_emitidas",
            "disponibilidades", "inversiones", "inmuebles", "deudas_total_aseg",
            "deudas_con_asegurados_ac_reaseguros", "deudas_neto",
            "patrimonio_neto", "inmuebles_inversion", "inmuebles_uso_propio",
        ),
    ),
    "cuadro_principal": CsvContract(
        ";",
        (
            "ramo_denominacion", "nombre_corto", "cod_cia", "primas_emitidas",
            "primas_devengadas", "siniestros", "pct_stros", "gastos",
            "pct_gastos", "resultado", "pct_result",
        ),
    ),
    "ganaron_perdieron": CsvContract(
        ";",
        (
            "tipo_cia", "nombre_corto", "cod_cia", "resultado_tecnico", "pct_rt",
            "resultado_financiero", "pct_rf", "resultado_operaciones",
            "impuesto_ganancias", "resultado", "pct_result", "primas_devengadas",
        ),
    ),
    "apertura_por_subramo": CsvContract(
        ";",
        (
            "subramo_denominacion", "nombre_corto", "cod_cia", "primas",
            "porcentaje", "porcentaje_acumulado",
        ),
    ),
    "apertura_por_subramo_comparativo": CsvContract(
        ";",
        (
            "subramo_denominacion", "nombre_corto", "cod_cia", "primas",
            "primas_anterior", "variacion", "porcentaje", "porcentaje_acumulado",
        ),
    ),
    "primas_cedidas_reaseguro": CsvContract(
        ";",
        (
            "tipo_cia", "nombre_corto", "cod_cia", "primas_emitidas",
            "primas_cedidas", "pct_cesion", "primas_retenidas", "pct_ret",
        ),
    ),
    "ranking_comparativo": CsvContract(
        ";",
        (
            "tipo_cia", "nombre_corto", "cod_cia", "primas_emitidas",
            "variacion", "primas_anterior",
        ),
    ),
    "ranking_comparativo_por_ramo": CsvContract(
        ";",
        (
            "ramo_denominacion", "nombre_corto", "cod_cia", "primas_emitidas",
            "variacion", "primas_anterior",
        ),
    ),
    "sueldos_y_gastos": CsvContract(
        ";",
        (
            "nombre_corto", "cod_cia", "tipo_cia", "total_primas_devengadas",
            "total_gs_prod", "total_sueldos", "total_gs", "gs_reaseguro",
        ),
    ),
    "detalle_inmuebles": CsvContract(
        ",",
        (
            "tipo_cia", "nombre_corto", "cod_cia", "inmuebles_inversion",
            "inmuebles_uso_propio", "inmuebles_total",
        ),
    ),
    "detalle_gastos": CsvContract(
        ",",
        (
            "tipo_cia", "nombre_corto", "cod_cia", "primas_emitidas",
            "total_primas_devengadas", "total_gs_prod", "total_gs_explot",
            "total_gs", "pct_gastos_produccion", "pct_gastos_explotacion",
            "pct_gastos_totales",
        ),
    ),
    "distribucion_inversiones": CsvContract(
        ",",
        (
            "tipo_cia", "nombre_corto", "cod_cia", "total_inv", "total_inv_inm",
            "total_inv_liq", "pct_inmuebles_inversion", "pct_inversiones_liquidas",
        ),
    ),
    "indicadores_solvencia": CsvContract(
        ",",
        (
            "tipo_cia", "nombre_corto", "cod_cia", "inmuebles_inversion",
            "inversiones", "disponibilidades", "deudas_con_asegurados",
        ),
    ),
}

EXCEL_REPORT_NAMES = (
    "apertura_por_subramo",
    "apertura_por_subramo_comparativo",
    "cuadro_nuevo",
    "cuadro_principal",
    "detalle_gastos",
    "detalle_inmuebles",
    "distribucion_inversiones",
    "ganaron_perdieron",
    "indicadores_solvencia",
    "primas_cedidas_reaseguro",
    "ranking_comparativo",
    "ranking_comparativo_por_ramo",
    "ranking_produccion",
    "sueldos_y_gastos",
)


class ReportValidationError(ValueError):
    """Raised when report inputs or staged outputs violate their contract."""


def expected_historical_periods(period: int) -> set[int]:
    """Return the periods required by the corrected-table calculations."""
    validate_period(period)
    year = period // 100
    quarter = period % 100
    previous_same_quarter = int(f"{year - 1}{quarter:02d}")

    if quarter == 1:
        return {
            period,
            previous_same_quarter,
            int(f"{year - 1}02"),
            int(f"{year - 1}04"),
            int(f"{year - 2}02"),
            int(f"{year - 2}04"),
        }
    if quarter == 2:
        return {
            period,
            int(f"{year - 1}02"),
            int(f"{year - 1}04"),
            int(f"{year - 2}02"),
            int(f"{year - 2}04"),
        }
    return {
        period,
        previous_same_quarter,
        int(f"{year}02"),
        int(f"{year - 1}02"),
    }


def _connect_read_only(database_path: str | Path) -> sqlite3.Connection:
    path = Path(database_path).expanduser().resolve()
    if not path.is_file():
        raise ReportValidationError("La base de datos configurada no existe.")
    return sqlite3.connect(f"file:{path}?mode=ro", uri=True)


def _table_exists(connection: sqlite3.Connection, table_name: str) -> bool:
    row = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None


def _periods_in_table(connection: sqlite3.Connection, table_name: str) -> set[int]:
    return {
        int(row[0])
        for row in connection.execute(
            f'SELECT DISTINCT periodo FROM "{table_name}" WHERE periodo IS NOT NULL'
        ).fetchall()
    }


def validate_report_preflight(database_path: str | Path, period: int) -> None:
    """Validate that all period-bound report inputs are current and complete."""
    validate_period(period)
    required_history = expected_historical_periods(period)

    with _connect_read_only(database_path) as connection:
        current_period_tables = (*CORRECTED_TABLES, "base_otros_conceptos")
        for table_name in current_period_tables:
            if not _table_exists(connection, table_name):
                raise ReportValidationError(
                    f"Falta la tabla requerida {table_name}. Procese las tablas antes de generar reportes."
                )

            columns = {
                row[1]
                for row in connection.execute(
                    f'PRAGMA table_info("{table_name}")'
                ).fetchall()
            }
            if "periodo" not in columns:
                raise ReportValidationError(
                    f"La tabla {table_name} no permite verificar su período."
                )

            table_periods = _periods_in_table(connection, table_name)
            if table_periods != {period}:
                displayed = ", ".join(map(str, sorted(table_periods))) or "sin datos"
                raise ReportValidationError(
                    f"La tabla {table_name} no corresponde exclusivamente al período {period} "
                    f"(contiene: {displayed})."
                )

            row_count = connection.execute(
                f'SELECT COUNT(*) FROM "{table_name}"'
            ).fetchone()[0]
            if row_count == 0:
                raise ReportValidationError(f"La tabla {table_name} está vacía.")

        for table_name in HISTORICAL_TABLES:
            if not _table_exists(connection, table_name):
                raise ReportValidationError(f"Falta la tabla histórica requerida {table_name}.")

            available_periods = _periods_in_table(connection, table_name)
            missing_periods = sorted(required_history - available_periods)
            if missing_periods:
                missing = ", ".join(map(str, missing_periods))
                raise ReportValidationError(
                    f"La tabla {table_name} no tiene la cobertura histórica requerida: {missing}."
                )

            placeholders = ",".join("?" for _ in SPECIAL_COMPANY_CODES)
            for required_period in sorted(required_history):
                present_codes = {
                    int(row[0])
                    for row in connection.execute(
                        f"""
                        SELECT DISTINCT CAST(cod_cia AS INTEGER)
                        FROM "{table_name}"
                        WHERE periodo = ?
                          AND CAST(cod_cia AS INTEGER) IN ({placeholders})
                        """,
                        (required_period, *SPECIAL_COMPANY_CODES),
                    ).fetchall()
                }
                missing_codes = sorted(set(SPECIAL_COMPANY_CODES) - present_codes)
                if missing_codes:
                    codes = ", ".join(f"{code:04d}" for code in missing_codes)
                    raise ReportValidationError(
                        f"Faltan compañías especiales en {table_name} para {required_period}: {codes}."
                    )


def expected_csv_filenames(period: str) -> set[str]:
    return {f"{period}_{name}.csv" for name in CSV_CONTRACTS}


def expected_excel_filenames(period: str) -> set[str]:
    return {f"{period}_{name}.xlsx" for name in EXCEL_REPORT_NAMES}


def validate_csv_outputs(directory: str | Path, period: str) -> list[Path]:
    """Validate the exact staged CSV set, schemas and non-empty content."""
    directory = Path(directory)
    expected = expected_csv_filenames(period)
    actual = {path.name for path in directory.glob(f"{period}_*.csv")}
    missing = sorted(expected - actual)
    unexpected = sorted(actual - expected)
    if missing or unexpected:
        details = []
        if missing:
            details.append(f"faltan: {', '.join(missing)}")
        if unexpected:
            details.append(f"sobran: {', '.join(unexpected)}")
        raise ReportValidationError("Conjunto CSV inválido (" + "; ".join(details) + ").")

    validated = []
    for report_name, contract in CSV_CONTRACTS.items():
        path = directory / f"{period}_{report_name}.csv"
        if path.stat().st_size == 0:
            raise ReportValidationError(f"El archivo {path.name} está vacío.")

        dataframe = pd.read_csv(path, sep=contract.separator)
        if dataframe.empty:
            raise ReportValidationError(f"El archivo {path.name} no contiene registros.")
        if tuple(dataframe.columns) != contract.columns:
            raise ReportValidationError(f"El archivo {path.name} no cumple el esquema esperado.")
        validated.append(path)

    return validated


def validate_excel_outputs(directory: str | Path, period: str) -> list[Path]:
    """Validate the exact staged Excel set and basic workbook readability."""
    directory = Path(directory)
    expected = expected_excel_filenames(period)
    actual = {path.name for path in directory.glob(f"{period}_*.xlsx")}
    missing = sorted(expected - actual)
    unexpected = sorted(actual - expected)
    if missing or unexpected:
        details = []
        if missing:
            details.append(f"faltan: {', '.join(missing)}")
        if unexpected:
            details.append(f"sobran: {', '.join(unexpected)}")
        raise ReportValidationError("Conjunto Excel inválido (" + "; ".join(details) + ").")

    validated = []
    for filename in sorted(expected):
        path = directory / filename
        if path.stat().st_size == 0:
            raise ReportValidationError(f"El archivo {filename} está vacío.")

        workbook = load_workbook(path, read_only=True, data_only=False)
        try:
            if not workbook.sheetnames:
                raise ReportValidationError(f"El archivo {filename} no contiene hojas.")
            if not any(
                sheet.max_row > 0 and sheet.max_column > 0
                for sheet in workbook.worksheets
            ):
                raise ReportValidationError(f"El archivo {filename} no contiene datos.")
        finally:
            workbook.close()
        validated.append(path)

    return validated


def publish_staged_directories(
    staged_and_official: Iterable[tuple[str | Path, str | Path]],
) -> None:
    """Replace official directories and restore every prior output on failure."""
    pairs = [(Path(staged), Path(official)) for staged, official in staged_and_official]
    token = uuid.uuid4().hex
    backups: dict[Path, Path] = {}
    published: list[Path] = []

    try:
        for staged, official in pairs:
            if not staged.is_dir():
                raise ReportValidationError(f"No existe el directorio temporal {staged}.")
            official.parent.mkdir(parents=True, exist_ok=True)

            backup = official.with_name(f".{official.name}.backup-{token}")
            if official.exists():
                official.replace(backup)
                backups[official] = backup

            staged.replace(official)
            published.append(official)
    except Exception:
        for official in reversed(published):
            if official.exists():
                shutil.rmtree(official)
        for official, backup in backups.items():
            if backup.exists():
                backup.replace(official)
        raise
    else:
        for backup in backups.values():
            if backup.exists():
                shutil.rmtree(backup)
