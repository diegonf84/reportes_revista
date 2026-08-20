"""Safe staging and transactional replacement for an existing reporting period."""

from __future__ import annotations

import hashlib
import json
import logging
import re
import shutil
import sqlite3
import stat
import subprocess
import time
import uuid
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

import pandas as pd

from modules.carga_base_principal import load_and_transform_data
from modules.common import periodo_to_filename, validate_period
from modules.report_generation import expected_historical_periods


MAX_ZIP_BYTES = 250 * 1024 * 1024
MAX_MDB_BYTES = 1024 * 1024 * 1024
MAX_COMPRESSION_RATIO = 200
STAGING_MAX_AGE_SECONDS = 24 * 60 * 60
TOKEN_PATTERN = re.compile(r"^[0-9a-f]{32}$")

DERIVED_PERIOD_TABLES = (
    "base_balance_ultimos_periodos",
    "base_subramos",
    "base_ramos",
    "base_otros_conceptos",
)
CORRECTED_CURRENT_TABLES = (
    "base_subramos_corregida_actual",
    "base_ramos_corregida_actual",
    "base_cias_corregida_actual",
)


class PeriodReloadError(ValueError):
    """Raised when a reload candidate or transaction is invalid."""


@dataclass(frozen=True)
class StagedPeriodReload:
    token: str
    period: int
    filename: str
    row_count: int
    company_codes: frozenset[str]
    company_names: dict[str, str]


@dataclass
class _PublishedSourceSwap:
    staged_zip: Path
    official_zip: Path
    backup_zip: Path | None
    official_mdb: Path
    backup_mdb: Path | None

    def restore(self) -> None:
        if self.official_zip.exists():
            self.official_zip.replace(self.staged_zip)
        if self.backup_zip and self.backup_zip.exists():
            self.backup_zip.replace(self.official_zip)
        if self.backup_mdb and self.backup_mdb.exists():
            self.backup_mdb.replace(self.official_mdb)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _staging_root(upload_directory: str | Path) -> Path:
    return Path(upload_directory) / ".reload-staging"


def _save_upload_with_limit(uploaded_file: BinaryIO, destination: Path) -> None:
    source = getattr(uploaded_file, "stream", uploaded_file)
    written = 0
    with destination.open("wb") as output:
        while True:
            chunk = source.read(1024 * 1024)
            if not chunk:
                break
            written += len(chunk)
            if written > MAX_ZIP_BYTES:
                raise PeriodReloadError("El archivo ZIP supera el tamaño permitido.")
            output.write(chunk)
    if written == 0:
        raise PeriodReloadError("El archivo ZIP está vacío.")


def cleanup_stale_reload_candidates(upload_directory: str | Path) -> None:
    root = _staging_root(upload_directory)
    if not root.is_dir():
        return
    cutoff = time.time() - STAGING_MAX_AGE_SECONDS
    for candidate in root.iterdir():
        if candidate.is_dir() and candidate.stat().st_mtime < cutoff:
            shutil.rmtree(candidate)


def validate_reload_archive(zip_path: str | Path, period: int) -> zipfile.ZipInfo:
    """Validate size, integrity and the exact single MDB member expected."""
    validate_period(period)
    path = Path(zip_path)
    if not path.is_file() or path.stat().st_size == 0:
        raise PeriodReloadError("El archivo ZIP está vacío o no existe.")
    if path.stat().st_size > MAX_ZIP_BYTES:
        raise PeriodReloadError("El archivo ZIP supera el tamaño permitido.")

    expected_zip = periodo_to_filename(period)
    expected_mdb = expected_zip.removesuffix(".zip") + ".mdb"
    try:
        with zipfile.ZipFile(path) as archive:
            members = archive.infolist()
            if len(members) != 1 or members[0].filename != expected_mdb:
                raise PeriodReloadError(
                    f"El ZIP debe contener únicamente {expected_mdb}."
                )
            member = members[0]
            file_type = (member.external_attr >> 16) & 0o170000
            if member.is_dir() or file_type == stat.S_IFLNK:
                raise PeriodReloadError("El contenido del ZIP no es un MDB regular.")
            if member.file_size <= 0 or member.file_size > MAX_MDB_BYTES:
                raise PeriodReloadError("El archivo MDB tiene un tamaño inválido.")
            if member.compress_size <= 0:
                raise PeriodReloadError("El archivo MDB comprimido está vacío.")
            if member.file_size / member.compress_size > MAX_COMPRESSION_RATIO:
                raise PeriodReloadError("El nivel de compresión del ZIP no es seguro.")
            bad_member = archive.testzip()
            if bad_member is not None:
                raise PeriodReloadError("El archivo ZIP está dañado.")
            return member
    except zipfile.BadZipFile as error:
        raise PeriodReloadError("El archivo no es un ZIP válido.") from error


def _export_balance_table(mdb_path: Path, csv_path: Path) -> None:
    with csv_path.open("wb") as output:
        result = subprocess.run(
            ["mdb-export", str(mdb_path), "Balance"],
            stdout=output,
            stderr=subprocess.PIPE,
            check=False,
        )
    if result.returncode != 0:
        csv_path.unlink(missing_ok=True)
        raise PeriodReloadError("No se pudo leer la tabla Balance del archivo MDB.")
    if not csv_path.is_file() or csv_path.stat().st_size == 0:
        csv_path.unlink(missing_ok=True)
        raise PeriodReloadError("La tabla Balance exportada está vacía.")


def read_reload_dataframe(
    zip_path: str | Path,
    period: int,
    working_directory: str | Path,
) -> tuple[pd.DataFrame, dict[str, str]]:
    """Extract, export and transform a validated candidate in an isolated directory."""
    zip_path = Path(zip_path)
    working_directory = Path(working_directory)
    working_directory.mkdir(parents=True, exist_ok=True)
    member = validate_reload_archive(zip_path, period)
    mdb_path = working_directory / Path(member.filename).name
    csv_path = working_directory / "Balance.csv"
    mdb_path.unlink(missing_ok=True)
    csv_path.unlink(missing_ok=True)

    try:
        with zipfile.ZipFile(zip_path) as archive:
            with archive.open(member) as source, mdb_path.open("wb") as destination:
                shutil.copyfileobj(source, destination)

        _export_balance_table(mdb_path, csv_path)
        raw_data = pd.read_csv(csv_path)
        required_columns = {
            "cod_cia",
            "periodo",
            "cod_cuenta",
            "cod_subramo",
            "importe",
        }
        missing_columns = sorted(required_columns - set(raw_data.columns))
        if missing_columns:
            raise PeriodReloadError(
                "La tabla Balance no contiene las columnas requeridas: "
                + ", ".join(missing_columns)
            )
        if raw_data.empty:
            raise PeriodReloadError("La tabla Balance no contiene registros.")

        company_codes = raw_data["cod_cia"].astype(str).str.zfill(4)
        if "razon_social" in raw_data.columns:
            company_names = dict(
                zip(company_codes, raw_data["razon_social"].fillna("Sin nombre"))
            )
        else:
            company_names = {code: f"Sin nombre ({code})" for code in company_codes.unique()}

        transformed = load_and_transform_data(raw_data)
        periods = {int(value) for value in transformed["periodo"].unique()}
        if periods != {period}:
            displayed = ", ".join(map(str, sorted(periods))) or "sin datos"
            raise PeriodReloadError(
                f"El contenido del archivo no corresponde exclusivamente a {period} "
                f"(contiene: {displayed})."
            )
        if transformed.empty:
            raise PeriodReloadError("El archivo no contiene registros utilizables.")
        return transformed, company_names
    finally:
        mdb_path.unlink(missing_ok=True)
        csv_path.unlink(missing_ok=True)


def stage_reload_candidate(
    uploaded_file: BinaryIO,
    period: int,
    filename: str,
    upload_directory: str | Path,
) -> StagedPeriodReload:
    """Save and validate a candidate without replacing the current source ZIP."""
    validate_period(period)
    expected_filename = periodo_to_filename(period)
    if filename != expected_filename:
        raise PeriodReloadError(f"El archivo debe llamarse {expected_filename}.")

    upload_directory = Path(upload_directory)
    upload_directory.mkdir(parents=True, exist_ok=True)
    cleanup_stale_reload_candidates(upload_directory)
    token = uuid.uuid4().hex
    candidate_directory = _staging_root(upload_directory) / token
    candidate_directory.mkdir(parents=True)
    candidate_zip = candidate_directory / filename
    temporary_zip = candidate_directory / f".{filename}.uploading"

    try:
        _save_upload_with_limit(uploaded_file, temporary_zip)
        temporary_zip.replace(candidate_zip)

        dataframe, company_names = read_reload_dataframe(
            candidate_zip,
            period,
            candidate_directory / "work",
        )
        company_codes = frozenset(dataframe["cod_cia"].astype(str).str.zfill(4).unique())
        manifest = {
            "token": token,
            "period": period,
            "filename": filename,
            "sha256": _sha256(candidate_zip),
            "row_count": len(dataframe),
            "company_count": len(company_codes),
        }
        (candidate_directory / "manifest.json").write_text(
            json.dumps(manifest, sort_keys=True),
            encoding="utf-8",
        )
        return StagedPeriodReload(
            token=token,
            period=period,
            filename=filename,
            row_count=len(dataframe),
            company_codes=company_codes,
            company_names=company_names,
        )
    except Exception:
        shutil.rmtree(candidate_directory, ignore_errors=True)
        raise


def _resolve_candidate(
    token: str,
    period: int,
    upload_directory: str | Path,
) -> tuple[Path, dict]:
    if not isinstance(token, str) or not TOKEN_PATTERN.fullmatch(token):
        raise PeriodReloadError("La recarga pendiente no existe o expiró.")
    candidate_directory = _staging_root(upload_directory) / token
    manifest_path = candidate_directory / "manifest.json"
    if not manifest_path.is_file():
        raise PeriodReloadError("La recarga pendiente no existe o expiró.")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise PeriodReloadError("La recarga pendiente no es válida.") from error
    if manifest.get("token") != token or manifest.get("period") != period:
        raise PeriodReloadError("La recarga pendiente no corresponde al período solicitado.")
    if manifest.get("filename") != periodo_to_filename(period):
        raise PeriodReloadError("La recarga pendiente no contiene el archivo esperado.")
    candidate_zip = candidate_directory / manifest["filename"]
    if not candidate_zip.is_file() or _sha256(candidate_zip) != manifest.get("sha256"):
        raise PeriodReloadError("El archivo pendiente fue modificado y debe cargarse nuevamente.")
    return candidate_directory, manifest


def cancel_staged_reload(token: str, period: int, upload_directory: str | Path) -> None:
    candidate_directory, _ = _resolve_candidate(token, period, upload_directory)
    shutil.rmtree(candidate_directory)


def get_period_database_stats(database_path: str | Path, period: int) -> dict[str, int]:
    validate_period(period)
    database = Path(database_path).expanduser().resolve()
    if not database.is_file():
        raise PeriodReloadError("La base de datos configurada no existe.")
    with sqlite3.connect(f"file:{database}?mode=ro", uri=True) as connection:
        row_count, company_count = connection.execute(
            """
            SELECT COUNT(*), COUNT(DISTINCT cod_cia)
            FROM datos_balance
            WHERE periodo = ?
            """,
            (period,),
        ).fetchone()
    return {"row_count": row_count, "company_count": company_count}


def _insert_dataframe_rows(
    connection: sqlite3.Connection,
    dataframe: pd.DataFrame,
    columns: list[str],
) -> None:
    placeholders = ", ".join("?" for _ in columns)
    quoted_columns = ", ".join(f'"{column}"' for column in columns)
    sql = f'INSERT INTO datos_balance ({quoted_columns}) VALUES ({placeholders})'
    ordered = dataframe[columns]
    chunk_size = 10_000
    for start in range(0, len(ordered), chunk_size):
        rows = list(ordered.iloc[start:start + chunk_size].itertuples(index=False, name=None))
        connection.executemany(sql, rows)


def _invalidate_derived_tables(connection: sqlite3.Connection, period: int) -> list[str]:
    invalidated = []
    for table_name in DERIVED_PERIOD_TABLES:
        exists = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
            (table_name,),
        ).fetchone()
        if not exists:
            continue
        columns = {
            row[1] for row in connection.execute(f'PRAGMA table_info("{table_name}")')
        }
        if "periodo" not in columns:
            continue
        cursor = connection.execute(
            f'DELETE FROM "{table_name}" WHERE periodo = ?',
            (period,),
        )
        if cursor.rowcount:
            invalidated.append(table_name)

    for table_name in CORRECTED_CURRENT_TABLES:
        exists = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
            (table_name,),
        ).fetchone()
        if not exists:
            continue
        columns = {
            row[1] for row in connection.execute(f'PRAGMA table_info("{table_name}")')
        }
        if "periodo" in columns:
            output_periods = {
                int(row[0])
                for row in connection.execute(
                    f'SELECT DISTINCT periodo FROM "{table_name}" WHERE periodo IS NOT NULL'
                )
            }
            if not any(
                period in expected_historical_periods(output_period)
                for output_period in output_periods
            ):
                continue
        cursor = connection.execute(f'DELETE FROM "{table_name}"')
        if cursor.rowcount:
            invalidated.append(table_name)
    return invalidated


def _replace_period_rows(
    connection: sqlite3.Connection,
    period: int,
    dataframe: pd.DataFrame,
) -> dict:
    table_columns = [
        row[1] for row in connection.execute('PRAGMA table_info("datos_balance")')
    ]
    if not table_columns:
        raise PeriodReloadError("No existe la tabla datos_balance.")
    if set(dataframe.columns) != set(table_columns):
        raise PeriodReloadError("Las columnas del archivo no coinciden con datos_balance.")

    periods = {int(value) for value in dataframe["periodo"].unique()}
    if periods != {period} or dataframe.empty:
        raise PeriodReloadError("Los datos preparados no corresponden al período solicitado.")

    old_rows, old_companies = connection.execute(
        "SELECT COUNT(*), COUNT(DISTINCT cod_cia) FROM datos_balance WHERE periodo = ?",
        (period,),
    ).fetchone()
    if old_rows == 0:
        raise PeriodReloadError(f"El período {period} no existe en la base de datos.")

    connection.execute("DROP TABLE IF EXISTS temp.reload_period_backup")
    connection.execute(
        "CREATE TEMP TABLE reload_period_backup AS "
        "SELECT * FROM datos_balance WHERE periodo = ?",
        (period,),
    )
    backup_rows = connection.execute(
        "SELECT COUNT(*) FROM temp.reload_period_backup"
    ).fetchone()[0]
    if backup_rows != old_rows:
        raise PeriodReloadError("No se pudo crear el respaldo transaccional del período.")

    connection.execute("DELETE FROM datos_balance WHERE periodo = ?", (period,))
    _insert_dataframe_rows(connection, dataframe, table_columns)

    new_rows, new_companies, minimum_period, maximum_period = connection.execute(
        """
        SELECT COUNT(*), COUNT(DISTINCT cod_cia), MIN(periodo), MAX(periodo)
        FROM datos_balance
        WHERE periodo = ?
        """,
        (period,),
    ).fetchone()
    expected_companies = dataframe["cod_cia"].nunique()
    if (
        new_rows != len(dataframe)
        or new_companies != expected_companies
        or minimum_period != period
        or maximum_period != period
    ):
        raise PeriodReloadError("La verificación posterior a la carga no coincide.")

    invalidated_tables = _invalidate_derived_tables(connection, period)
    return {
        "old_rows": old_rows,
        "old_companies": old_companies,
        "new_rows": new_rows,
        "new_companies": new_companies,
        "invalidated_tables": invalidated_tables,
    }


def _publish_candidate_source(
    candidate_directory: Path,
    filename: str,
    upload_directory: Path,
) -> _PublishedSourceSwap:
    staged_zip = candidate_directory / filename
    official_zip = upload_directory / filename
    official_mdb = upload_directory / (filename.removesuffix(".zip") + ".mdb")
    backup_zip = candidate_directory / "previous.zip" if official_zip.exists() else None
    backup_mdb = candidate_directory / "previous.mdb" if official_mdb.exists() else None

    swap = _PublishedSourceSwap(
        staged_zip=staged_zip,
        official_zip=official_zip,
        backup_zip=backup_zip,
        official_mdb=official_mdb,
        backup_mdb=backup_mdb,
    )
    try:
        if backup_zip:
            official_zip.replace(backup_zip)
        if backup_mdb:
            official_mdb.replace(backup_mdb)
        staged_zip.replace(official_zip)
        return swap
    except Exception:
        if official_zip.exists() and not staged_zip.exists():
            official_zip.replace(staged_zip)
        if backup_zip and backup_zip.exists():
            backup_zip.replace(official_zip)
        if backup_mdb and backup_mdb.exists():
            backup_mdb.replace(official_mdb)
        raise


def _commit_connection(connection: sqlite3.Connection) -> None:
    connection.commit()


def confirm_staged_reload(
    token: str,
    period: int,
    upload_directory: str | Path,
    database_path: str | Path,
) -> dict:
    """Replace source and database rows, restoring both on any controlled failure."""
    validate_period(period)
    upload_directory = Path(upload_directory)
    candidate_directory, manifest = _resolve_candidate(token, period, upload_directory)
    dataframe, _ = read_reload_dataframe(
        candidate_directory / manifest["filename"],
        period,
        candidate_directory / "work",
    )

    database = Path(database_path).expanduser().resolve()
    if not database.is_file():
        raise PeriodReloadError("La base de datos configurada no existe.")
    connection = sqlite3.connect(database)
    source_swap = None
    try:
        connection.execute("BEGIN IMMEDIATE")
        result = _replace_period_rows(connection, period, dataframe)
        source_swap = _publish_candidate_source(
            candidate_directory,
            manifest["filename"],
            upload_directory,
        )
        _commit_connection(connection)
    except Exception:
        connection.rollback()
        if source_swap is not None:
            source_swap.restore()
        raise
    finally:
        connection.close()

    try:
        shutil.rmtree(candidate_directory)
    except OSError:
        logging.warning("No se pudo limpiar el staging de la recarga %s", token)
    return result
