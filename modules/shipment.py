"""Prepara los archivos Excel finales para envío al destinatario.

Copia los archivos generados en ``excel_final_files/<period>`` al directorio
de envío configurado, aplicando el rename esperado por el destinatario.

Reglas:
- Crea la carpeta ``<base>/<YYYY-N>/envios/`` si no existe (``mkdir -p``).
- Aplica ``SHIPMENT_FILE_MAPPING`` para el nombre final.
- Omite los slugs en ``SHIPMENT_EXCLUDED`` (se generan pero no se envían).
- Sobrescribe archivos existentes (regeneración es idempotente).
"""
from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import TypedDict

logger = logging.getLogger(__name__)


SHIPMENT_BASE_DIR = Path("/Users/diegofrigerio/personal/revista")
PROJECT_ROOT = Path(__file__).resolve().parent.parent
EXCEL_FINAL_DIR = PROJECT_ROOT / "excel_final_files"


# Mapeo: slug técnico (sin prefijo de período) → nombre de envío.
# El prefijo "<YYYY-N> " se agrega automáticamente al construir el destino.
SHIPMENT_FILE_MAPPING: dict[str, str] = {
    "apertura_por_subramo_comparativo": "Apertura por subramo comparativo",
    "cuadro_nuevo": "Cuadro Nuevo",
    "cuadro_principal": "Cuadro Principal",
    "detalle_gastos": "Detalle Gastos",
    "detalle_inmuebles": "Detalle Inmuebles",
    "distribucion_inversiones": "Distribucion Inversiones",
    "ganaron_perdieron": "Ganaron Perdieron",
    "indicadores_solvencia": "Indicadores Solvencia",
    "primas_cedidas_reaseguro": "Primas Cedidas Reaseguro",
    "ranking_comparativo": "Ranking Comparativo",
    "ranking_comparativo_por_ramo": "Ranking Comparativo por ramo",
    "ranking_produccion": "Ranking Produccion",
    "sueldos_y_gastos": "Sueldos y gastos",
}


# Slugs que se generan en excel_final_files pero NO se copian al envío.
SHIPMENT_EXCLUDED: frozenset[str] = frozenset({"apertura_por_subramo"})


class ShipmentResult(TypedDict):
    """Resultado de una corrida de ``prepare_shipment``."""
    copied: list[str]
    skipped: list[str]
    failed: list[dict[str, str]]
    destination: str


def period_to_shipment_dir(period: str) -> Path:
    """Convierte ``202601`` al directorio de envío ``<base>/2026-1/envios``.

    Args:
        period: Período en formato ``YYYYPP`` (ej: ``202601``).

    Returns:
        Path al directorio destino (no se garantiza que exista).

    Raises:
        ValueError: Si el período no tiene el formato esperado.
    """
    if len(period) != 6 or not period.isdigit():
        raise ValueError(f"Período inválido: {period!r}. Esperado YYYYPP (ej: 202601).")
    quarter = period[5]
    if quarter not in "1234":
        raise ValueError(
            f"Trimestre inválido en período {period!r}: {quarter!r}. Esperado 1-4."
        )
    year = period[:4]
    return SHIPMENT_BASE_DIR / f"{year}-{quarter}" / "envios"


def _slug_from_filename(source: Path, period: str) -> str:
    """Extrae el slug técnico del nombre generado (ej: ``cuadro_principal``)."""
    prefix = f"{period}_"
    if not source.stem.startswith(prefix):
        raise ValueError(
            f"Nombre inesperado: {source.name} no comienza con {prefix!r}."
        )
    return source.stem[len(prefix):]


def _resolve_source_files(period: str) -> list[Path]:
    """Devuelve los ``.xlsx`` generados para el período (excluye ``corregido_*``)."""
    source_dir = EXCEL_FINAL_DIR / period
    if not source_dir.exists():
        raise FileNotFoundError(
            f"No existe el directorio origen {source_dir}. "
            f"Generá primero los excels para el período {period}."
        )
    return sorted(p for p in source_dir.glob(f"{period}_*.xlsx") if not p.name.startswith("corregido_"))


def prepare_shipment(period: str) -> ShipmentResult:
    """Copia y renombra los excels finales al directorio de envío.

    - Crea ``<base>/<YYYY-N>/envios/`` si no existe.
    - Por cada archivo origen: omite si está en ``SHIPMENT_EXCLUDED``, falla
      si no está en ``SHIPMENT_FILE_MAPPING``, copia+renombra en el resto.
    - Archivos destino existentes se sobrescriben (``shutil.copy2`` preserva mtime).

    Args:
        period: Período en formato ``YYYYPP``.

    Returns:
        ``ShipmentResult`` con listas de copiados, omitidos y fallidos, y la
        ruta del directorio destino.

    Raises:
        ValueError: Si el período no tiene el formato esperado.
        FileNotFoundError: Si el directorio origen no existe.
    """
    destination = period_to_shipment_dir(period)
    destination.mkdir(parents=True, exist_ok=True)

    year = period[:4]
    quarter = period[5]

    copied: list[str] = []
    skipped: list[str] = []
    failed: list[dict[str, str]] = []

    for source in _resolve_source_files(period):
        try:
            slug = _slug_from_filename(source, period)
        except ValueError as exc:
            failed.append({"source": source.name, "error": str(exc)})
            continue

        if slug in SHIPMENT_EXCLUDED:
            skipped.append(source.name)
            logger.info("Omitido (excluido): %s", source.name)
            continue

        if slug not in SHIPMENT_FILE_MAPPING:
            failed.append({
                "source": source.name,
                "error": (
                    f"No hay mapeo de envío para el slug {slug!r}. "
                    f"Agregalo a SHIPMENT_FILE_MAPPING."
                ),
            })
            continue

        target_name = f"{year}-{quarter} {SHIPMENT_FILE_MAPPING[slug]}.xlsx"
        target = destination / target_name

        try:
            shutil.copy2(source, target)
            copied.append(target_name)
            logger.info("Copiado %s → %s", source.name, target)
        except OSError as exc:
            failed.append({"source": source.name, "error": str(exc)})
            logger.exception("Fallo copiando %s → %s", source, target)

    return ShipmentResult(
        copied=copied,
        skipped=skipped,
        failed=failed,
        destination=str(destination),
    )
