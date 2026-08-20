"""Ordered processing pipeline for one reporting period."""

from __future__ import annotations

import fcntl
import logging
import os
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping

from modules.common import validate_period
from modules.crea_tabla_cias_corregida import create_table_from_query as create_cias
from modules.crea_tabla_otros_conceptos import main as create_concepts
from modules.crea_tabla_ramos import main as create_ramos
from modules.crea_tabla_ramos_corregida import (
    create_ramos_table_from_query as create_corrected_ramos,
)
from modules.crea_tabla_subramos import main as create_subramos
from modules.crea_tabla_subramos_corregida import (
    create_table_from_query as create_corrected_subramos,
)
from modules.crea_tabla_ultimos_periodos import create_recent_periods_table
from modules.report_generation import generate_official_reports


@dataclass(frozen=True)
class PipelineStage:
    key: str
    label: str
    dependencies: tuple[str, ...]


PIPELINE_STAGES = (
    PipelineStage("recent_periods", "Períodos recientes", ()),
    PipelineStage("base_tables", "Bases de subramos y ramos", ("recent_periods",)),
    PipelineStage("concepts", "Conceptos financieros", ("recent_periods",)),
    PipelineStage("corrected_tables", "Tablas corregidas", ("base_tables",)),
    PipelineStage("reports", "Reportes CSV y Excel", ("concepts", "corrected_tables")),
)

TABLE_STAGES = PIPELINE_STAGES[:-1]


class PipelineBusyError(RuntimeError):
    """Raised when another pipeline already owns the database lock."""


class PipelineExecutionError(RuntimeError):
    """Raised after a stage fails and the remaining stages are stopped."""

    def __init__(self, stage: PipelineStage, statuses: list[dict]) -> None:
        super().__init__(
            f"El procesamiento se detuvo en {stage.label}. "
            "Las etapas posteriores no se ejecutaron."
        )
        self.stage = stage
        self.statuses = statuses


def _connect(database_path: str | Path) -> sqlite3.Connection:
    path = Path(database_path).expanduser().resolve()
    if not path.is_file():
        raise ValueError("La base de datos configurada no existe.")
    return sqlite3.connect(path)


@contextmanager
def pipeline_lock(database_path: str | Path, period: int):
    """Hold a non-blocking cross-process lock for this database pipeline."""
    path = Path(database_path).expanduser().resolve()
    lock_path = path.with_name(f".{path.name}.pipeline.lock")
    handle = lock_path.open("a+", encoding="utf-8")
    try:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise PipelineBusyError(
                "Ya hay un procesamiento activo sobre esta base de datos."
            ) from error
        handle.seek(0)
        handle.truncate()
        handle.write(f"pid={os.getpid()} periodo={period}\n")
        handle.flush()
        yield
    finally:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        finally:
            handle.close()


def _default_stage_actions(
    project_root: str | Path,
    database_path: str | Path,
) -> Mapping[str, Callable[[int], object]]:
    return {
        "recent_periods": create_recent_periods_table,
        "base_tables": lambda period: (create_subramos(period), create_ramos(period)),
        "concepts": create_concepts,
        "corrected_tables": lambda period: (
            create_corrected_subramos(period),
            create_corrected_ramos(period),
            create_cias(period),
        ),
        "reports": lambda period: generate_official_reports(
            project_root, database_path, period
        ),
    }


def _assert_period_exists(database_path: str | Path, period: int) -> None:
    with _connect(database_path) as connection:
        exists = connection.execute(
            "SELECT 1 FROM datos_balance WHERE periodo = ? LIMIT 1",
            (period,),
        ).fetchone()
    if exists is None:
        raise ValueError(f"El período {period} no existe en datos_balance.")


def _validate_table_period(
    database_path: str | Path,
    table_names: tuple[str, ...],
    period: int,
    *,
    exact_period: bool,
) -> None:
    with _connect(database_path) as connection:
        for table_name in table_names:
            exists = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
                (table_name,),
            ).fetchone()
            if exists is None:
                raise RuntimeError(f"No se creó la tabla requerida {table_name}.")
            periods = {
                int(row[0])
                for row in connection.execute(
                    f'SELECT DISTINCT periodo FROM "{table_name}" WHERE periodo IS NOT NULL'
                ).fetchall()
            }
            if period not in periods or (exact_period and periods != {period}):
                raise RuntimeError(
                    f"La tabla {table_name} no quedó actualizada para {period}."
                )
            count = connection.execute(
                f'SELECT COUNT(*) FROM "{table_name}" WHERE periodo = ?',
                (period,),
            ).fetchone()[0]
            if count == 0:
                raise RuntimeError(f"La tabla {table_name} quedó vacía para {period}.")


def _validate_stage_output(
    database_path: str | Path,
    stage_key: str,
    period: int,
) -> None:
    if stage_key == "recent_periods":
        _validate_table_period(
            database_path, ("base_balance_ultimos_periodos",), period, exact_period=False
        )
    elif stage_key == "base_tables":
        _validate_table_period(
            database_path, ("base_subramos", "base_ramos"), period, exact_period=False
        )
    elif stage_key == "concepts":
        _validate_table_period(
            database_path, ("base_otros_conceptos",), period, exact_period=True
        )
    elif stage_key == "corrected_tables":
        _validate_table_period(
            database_path,
            (
                "base_subramos_corregida_actual",
                "base_ramos_corregida_actual",
                "base_cias_corregida_actual",
            ),
            period,
            exact_period=True,
        )


def _initial_statuses(stages: tuple[PipelineStage, ...] = PIPELINE_STAGES) -> list[dict]:
    return [
        {
            "key": stage.key,
            "label": stage.label,
            "dependencies": list(stage.dependencies),
            "status": "pending",
        }
        for stage in stages
    ]


def _run_stages(
    stages: tuple[PipelineStage, ...],
    stage_actions: Mapping[str, Callable[[int], object]],
    database_path: str | Path,
    period: int,
    *,
    validate_outputs: bool,
) -> tuple[list[dict], object | None]:
    statuses = _initial_statuses(stages)
    report_result = None

    for index, stage in enumerate(stages):
        statuses[index]["status"] = "running"
        try:
            result = stage_actions[stage.key](period)
            if validate_outputs:
                _validate_stage_output(database_path, stage.key, period)
            statuses[index]["status"] = "completed"
            if stage.key == "reports":
                report_result = result
        except Exception as error:
            statuses[index]["status"] = "failed"
            logging.exception(
                "Falló la etapa %s del procesamiento para %s", stage.key, period
            )
            raise PipelineExecutionError(stage, statuses) from error

    return statuses, report_result


def run_tables_pipeline(
    period: int,
    database_path: str | Path,
    project_root: str | Path,
    *,
    actions: Mapping[str, Callable[[int], object]] | None = None,
    validate_outputs: bool = True,
) -> dict:
    """Run every table-building stage in dependency order for one period."""
    validate_period(period)
    _assert_period_exists(database_path, period)
    stage_actions = actions or _default_stage_actions(project_root, database_path)
    missing_actions = [stage.key for stage in TABLE_STAGES if stage.key not in stage_actions]
    if missing_actions:
        raise ValueError(f"Faltan acciones del pipeline: {', '.join(missing_actions)}")

    with pipeline_lock(database_path, period):
        statuses, _ = _run_stages(
            TABLE_STAGES,
            stage_actions,
            database_path,
            period,
            validate_outputs=validate_outputs,
        )

    return {
        "periodo": str(period),
        "stages": statuses,
    }


def run_period_pipeline(
    period: int,
    database_path: str | Path,
    project_root: str | Path,
    *,
    actions: Mapping[str, Callable[[int], object]] | None = None,
    validate_outputs: bool = True,
) -> dict:
    """Run every stage in order and stop at the first failure."""
    validate_period(period)
    _assert_period_exists(database_path, period)
    stage_actions = actions or _default_stage_actions(project_root, database_path)
    missing_actions = [stage.key for stage in PIPELINE_STAGES if stage.key not in stage_actions]
    if missing_actions:
        raise ValueError(f"Faltan acciones del pipeline: {', '.join(missing_actions)}")

    with pipeline_lock(database_path, period):
        statuses, report_result = _run_stages(
            PIPELINE_STAGES,
            stage_actions,
            database_path,
            period,
            validate_outputs=validate_outputs,
        )

    return {
        "periodo": str(period),
        "stages": statuses,
        "reports": report_result,
    }
