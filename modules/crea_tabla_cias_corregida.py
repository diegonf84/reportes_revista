"""
Módulo para crear tabla de compañías corregida basada en período especificado.

Este módulo maneja las diferencias en los ciclos de cierre de las compañías aseguradoras:
- Compañías normales: cierran sus reportes financieros en junio (12 meses: julio-junio)
- Compañías especiales (0829, 0541, 0686): cierran en diciembre (12 meses: enero-diciembre)

Para normalizar los datos y que todas reporten el mismo período de 12 meses, se aplican
correcciones específicas según el trimestre solicitado.

DIFERENCIA CON RAMOS/SUBRAMOS:
Este módulo trabaja a nivel de COMPAÑÍA (cod_cia), agregando TODOS los subramos.
Es utilizado por ranking_comparativo que necesita totales por compañía sin importar
cambios en la estructura de ramos/subramos entre períodos.
"""

import pandas as pd
import os
import argparse
from pathlib import Path
from dotenv import load_dotenv
import sqlite3
import logging
from modules.common import validate_period, setup_logging

logger = logging.getLogger(__name__)


def calculate_periods(periodo_actual: int) -> dict:
    """
    Calcula los períodos necesarios basados en el período actual.

    Args:
        periodo_actual (int): Período actual en formato YYYYPP

    Returns:
        dict: Diccionario con todos los períodos calculados
    """
    periodo_str = str(periodo_actual)
    year = int(periodo_str[:4])
    quarter = int(periodo_str[4:])

    # Calcular períodos necesarios
    periods = {
        'actual': periodo_actual,
        'anterior_mismo_trimestre': int(f"{year-1}{quarter:02d}"),
    }

    # Para marzo (trimestre 1), necesitamos datos de diciembre y junio del año anterior
    if quarter == 1:
        periods.update({
            'diciembre_actual': int(f"{year-1}04"),  # Diciembre del año anterior
            'junio_actual': int(f"{year-1}02"),      # Junio del año anterior
            'diciembre_anterior': int(f"{year-2}04"), # Diciembre hace 2 años
            'junio_anterior': int(f"{year-2}02"),     # Junio hace 2 años
        })
    # Para junio (trimestre 2), necesitamos datos de diciembre anterior y junio anterior
    elif quarter == 2:
        periods.update({
            'diciembre_anterior': int(f"{year-1}04"),     # Diciembre año anterior
            'junio_anterior': int(f"{year-1}02"),         # Junio año anterior
            'diciembre_prev_prev': int(f"{year-2}04"),    # Diciembre hace 2 años
            'junio_prev_prev': int(f"{year-2}02"),        # Junio hace 2 años
        })
    # Para septiembre (trimestre 3), necesitamos datos de junio del mismo año
    elif quarter == 3:
        periods.update({
            'junio_actual': int(f"{year}02"),        # Junio del mismo año
            'junio_anterior': int(f"{year-1}02"),    # Junio del año anterior
        })
    # Para diciembre (trimestre 4), necesitamos datos de junio del mismo año
    elif quarter == 4:
        periods.update({
            'junio_actual': int(f"{year}02"),        # Junio del mismo año
            'junio_anterior': int(f"{year-1}02"),    # Junio del año anterior
        })

    return periods


def build_query_for_march(periods: dict) -> str:
    """Construye query para procesamiento de marzo (trimestre 1)."""
    return f"""
    CREATE TABLE base_cias_corregida_actual AS
    with primas_diferentes_marzo_actual as (
        select cod_cia,
        sum(primas_emitidas) as primas_emit_mar_actual
        from base_subramos
        where periodo in ('{periods["actual"]}')
        and cod_cia in ('0829','0541','0686')
        GROUP by cod_cia
    ),
    primas_diferentes_junio_actual as (
        select cod_cia,
        sum(primas_emitidas) as primas_emit_jun_actual
        from base_subramos
        where periodo in ('{periods["junio_actual"]}')
        and cod_cia in ('0829','0541','0686')
        GROUP by cod_cia
    ),
    primas_diferentes_diciembre_actual as (
        select cod_cia,
        sum(primas_emitidas) as primas_emit_dic_actual
        from base_subramos
        where periodo in ('{periods["diciembre_actual"]}')
        and cod_cia in ('0829','0541','0686')
        GROUP by cod_cia
    ),
    primas_diferentes_marzo_anterior as (
        select cod_cia,
        sum(primas_emitidas) as primas_emit_mar_anterior
        from base_subramos
        where periodo in ('{periods["anterior_mismo_trimestre"]}')
        and cod_cia in ('0829','0541','0686')
        GROUP by cod_cia
    ),
    primas_diferentes_junio_anterior as (
        select cod_cia,
        sum(primas_emitidas) as primas_emit_jun_anterior
        from base_subramos
        where periodo in ('{periods["junio_anterior"]}')
        and cod_cia in ('0829','0541','0686')
        GROUP by cod_cia
    ),
    primas_diferentes_diciembre_anterior as (
        select cod_cia,
        sum(primas_emitidas) as primas_emit_dic_anterior
        from base_subramos
        where periodo in ('{periods["diciembre_anterior"]}')
        and cod_cia in ('0829','0541','0686')
        GROUP by cod_cia
    ),
    base_cias_diferentes as (
        select a.cod_cia,
        a.primas_emit_mar_actual - b.primas_emit_jun_actual + c.primas_emit_dic_actual as primas_emitidas,
        d.primas_emit_mar_anterior - e.primas_emit_jun_anterior + f.primas_emit_dic_anterior as primas_emitidas_anterior
        from primas_diferentes_marzo_actual a
        join primas_diferentes_junio_actual b on a.cod_cia = b.cod_cia
        join primas_diferentes_diciembre_actual c on a.cod_cia = c.cod_cia
        join primas_diferentes_marzo_anterior d on a.cod_cia = d.cod_cia
        join primas_diferentes_junio_anterior e on a.cod_cia = e.cod_cia
        join primas_diferentes_diciembre_anterior f on a.cod_cia = f.cod_cia
    ),
    primas_actuales_resto as (
        select cod_cia,
        sum(primas_emitidas) as primas_emit_actual
        from base_subramos
        where periodo in ('{periods["actual"]}')
        and cod_cia not in ('0829','0541','0686')
        GROUP by cod_cia
    ),
    primas_anteriores_resto as (
        select cod_cia,
        sum(primas_emitidas) as primas_emit_anterior
        from base_subramos
        where periodo in ('{periods["anterior_mismo_trimestre"]}')
        and cod_cia not in ('0829','0541','0686')
        GROUP by cod_cia
    ),
    base_cias_comunes as (
        select coalesce(a.cod_cia, b.cod_cia) as cod_cia,
        coalesce(a.primas_emit_actual, 0) as primas_emitidas,
        coalesce(b.primas_emit_anterior, 0) as primas_emitidas_anterior
        from primas_actuales_resto a
        full outer join primas_anteriores_resto b on a.cod_cia = b.cod_cia
    ),
    base_final as (
        select *
        from base_cias_comunes
        union all
        select *
        from base_cias_diferentes
    )
    select * from base_final
    where primas_emitidas <> 0
    """


def build_query_for_december(periods: dict) -> str:
    """Construye query para procesamiento de diciembre (trimestre 4)."""
    return f"""
    CREATE TABLE base_cias_corregida_actual AS
    with primas_dif_dic_actual as (
        select cod_cia,
        sum(primas_emitidas) as primas_emit_dic_actual
        from base_subramos
        where periodo in ('{periods["actual"]}')
        and cod_cia in ('0829','0541','0686')
        GROUP by cod_cia
    ),
    primas_dif_jun_actual as (
        select cod_cia,
        sum(primas_emitidas) as primas_emit_jun_actual
        from base_subramos
        where periodo in ('{periods["junio_actual"]}')
        and cod_cia in ('0829','0541','0686')
        GROUP by cod_cia
    ),
    primas_dif_dic_anterior as (
        select cod_cia,
        sum(primas_emitidas) as primas_emit_dic_anterior
        from base_subramos
        where periodo in ('{periods["anterior_mismo_trimestre"]}')
        and cod_cia in ('0829','0541','0686')
        GROUP by cod_cia
    ),
    primas_dif_jun_anterior as (
        select cod_cia,
        sum(primas_emitidas) as primas_emit_jun_anterior
        from base_subramos
        where periodo in ('{periods["junio_anterior"]}')
        and cod_cia in ('0829','0541','0686')
        GROUP by cod_cia
    ),
    base_cias_diferentes as (
        select a.cod_cia,
        a.primas_emit_dic_actual - b.primas_emit_jun_actual as primas_emitidas,
        c.primas_emit_dic_anterior - d.primas_emit_jun_anterior as primas_emitidas_anterior
        from primas_dif_dic_actual a
        join primas_dif_jun_actual b on a.cod_cia = b.cod_cia
        join primas_dif_dic_anterior c on a.cod_cia = c.cod_cia
        join primas_dif_jun_anterior d on a.cod_cia = d.cod_cia
    ),
    primas_actuales_resto as (
        select cod_cia,
        sum(primas_emitidas) as primas_emit_actual
        from base_subramos
        where periodo in ('{periods["actual"]}')
        and cod_cia not in ('0829','0541','0686')
        GROUP by cod_cia
    ),
    primas_anteriores_resto as (
        select cod_cia,
        sum(primas_emitidas) as primas_emit_anterior
        from base_subramos
        where periodo in ('{periods["anterior_mismo_trimestre"]}')
        and cod_cia not in ('0829','0541','0686')
        GROUP by cod_cia
    ),
    base_cias_comunes as (
        select coalesce(a.cod_cia, b.cod_cia) as cod_cia,
        coalesce(a.primas_emit_actual, 0) as primas_emitidas,
        coalesce(b.primas_emit_anterior, 0) as primas_emitidas_anterior
        from primas_actuales_resto a
        full outer join primas_anteriores_resto b on a.cod_cia = b.cod_cia
    ),
    base_final as (
        select *
        from base_cias_comunes
        union all
        select *
        from base_cias_diferentes
    )
    select * from base_final
    where primas_emitidas <> 0
    """


def build_query_for_june(periods: dict) -> str:
    """Construye query para procesamiento de junio (trimestre 2)."""
    return f"""
    CREATE TABLE base_cias_corregida_actual AS
    with primas_diferentes_junio_actual as (
        select cod_cia,
        sum(primas_emitidas) as primas_emit_jun_actual
        from base_subramos
        where periodo in ('{periods["actual"]}')
        and cod_cia in ('0829','0541','0686')
        GROUP by cod_cia
    ),
    primas_diferentes_diciembre_anterior as (
        select cod_cia,
        sum(primas_emitidas) as primas_emit_dic_anterior
        from base_subramos
        where periodo in ('{periods["diciembre_anterior"]}')
        and cod_cia in ('0829','0541','0686')
        GROUP by cod_cia
    ),
    primas_diferentes_junio_anterior as (
        select cod_cia,
        sum(primas_emitidas) as primas_emit_jun_anterior
        from base_subramos
        where periodo in ('{periods["junio_anterior"]}')
        and cod_cia in ('0829','0541','0686')
        GROUP by cod_cia
    ),
    primas_diferentes_junio_prev_prev as (
        select cod_cia,
        sum(primas_emitidas) as primas_emit_jun_prev_prev
        from base_subramos
        where periodo in ('{periods["junio_prev_prev"]}')
        and cod_cia in ('0829','0541','0686')
        GROUP by cod_cia
    ),
    primas_diferentes_diciembre_prev_prev as (
        select cod_cia,
        sum(primas_emitidas) as primas_emit_dic_prev_prev
        from base_subramos
        where periodo in ('{periods["diciembre_prev_prev"]}')
        and cod_cia in ('0829','0541','0686')
        GROUP by cod_cia
    ),
    base_cias_diferentes as (
        select a.cod_cia,
        a.primas_emit_jun_actual + b.primas_emit_dic_anterior - c.primas_emit_jun_anterior as primas_emitidas,
        c.primas_emit_jun_anterior + e.primas_emit_dic_prev_prev - d.primas_emit_jun_prev_prev as primas_emitidas_anterior
        from primas_diferentes_junio_actual a
        join primas_diferentes_diciembre_anterior b on a.cod_cia = b.cod_cia
        join primas_diferentes_junio_anterior c on a.cod_cia = c.cod_cia
        join primas_diferentes_junio_prev_prev d on a.cod_cia = d.cod_cia
        join primas_diferentes_diciembre_prev_prev e on a.cod_cia = e.cod_cia
    ),
    primas_actuales_resto as (
        select cod_cia,
        sum(primas_emitidas) as primas_emit_actual
        from base_subramos
        where periodo in ('{periods["actual"]}')
        and cod_cia not in ('0829','0541','0686')
        GROUP by cod_cia
    ),
    primas_anteriores_resto as (
        select cod_cia,
        sum(primas_emitidas) as primas_emit_anterior
        from base_subramos
        where periodo in ('{periods["anterior_mismo_trimestre"]}')
        and cod_cia not in ('0829','0541','0686')
        GROUP by cod_cia
    ),
    base_cias_comunes as (
        select coalesce(a.cod_cia, b.cod_cia) as cod_cia,
        coalesce(a.primas_emit_actual, 0) as primas_emitidas,
        coalesce(b.primas_emit_anterior, 0) as primas_emitidas_anterior
        from primas_actuales_resto a
        full outer join primas_anteriores_resto b on a.cod_cia = b.cod_cia
    ),
    base_final as (
        select *
        from base_cias_comunes
        union all
        select *
        from base_cias_diferentes
    )
    select * from base_final
    where primas_emitidas <> 0
    """


def build_query_for_september(periods: dict) -> str:
    """Construye query para procesamiento de septiembre (trimestre 3)."""
    return f"""
    CREATE TABLE base_cias_corregida_actual AS
    with primas_dif_sep_actual as (
        select cod_cia,
        sum(primas_emitidas) as primas_emit_sep_actual
        from base_subramos
        where periodo in ('{periods["actual"]}')
        and cod_cia in ('0829','0541','0686')
        GROUP by cod_cia
    ),
    primas_dif_jun_actual as (
        select cod_cia,
        sum(primas_emitidas) as primas_emit_jun_actual
        from base_subramos
        where periodo in ('{periods["junio_actual"]}')
        and cod_cia in ('0829','0541','0686')
        GROUP by cod_cia
    ),
    primas_dif_sep_anterior as (
        select cod_cia,
        sum(primas_emitidas) as primas_emit_sep_anterior
        from base_subramos
        where periodo in ('{periods["anterior_mismo_trimestre"]}')
        and cod_cia in ('0829','0541','0686')
        GROUP by cod_cia
    ),
    primas_dif_jun_anterior as (
        select cod_cia,
        sum(primas_emitidas) as primas_emit_jun_anterior
        from base_subramos
        where periodo in ('{periods["junio_anterior"]}')
        and cod_cia in ('0829','0541','0686')
        GROUP by cod_cia
    ),
    base_cias_diferentes as (
        select a.cod_cia,
        a.primas_emit_sep_actual - b.primas_emit_jun_actual as primas_emitidas,
        c.primas_emit_sep_anterior - d.primas_emit_jun_anterior as primas_emitidas_anterior
        from primas_dif_sep_actual a
        join primas_dif_jun_actual b on a.cod_cia = b.cod_cia
        join primas_dif_sep_anterior c on a.cod_cia = c.cod_cia
        join primas_dif_jun_anterior d on a.cod_cia = d.cod_cia
    ),
    primas_actuales_resto as (
        select cod_cia,
        sum(primas_emitidas) as primas_emit_actual
        from base_subramos
        where periodo in ('{periods["actual"]}')
        and cod_cia not in ('0829','0541','0686')
        GROUP by cod_cia
    ),
    primas_anteriores_resto as (
        select cod_cia,
        sum(primas_emitidas) as primas_emit_anterior
        from base_subramos
        where periodo in ('{periods["anterior_mismo_trimestre"]}')
        and cod_cia not in ('0829','0541','0686')
        GROUP by cod_cia
    ),
    base_cias_comunes as (
        select coalesce(a.cod_cia, b.cod_cia) as cod_cia,
        coalesce(a.primas_emit_actual, 0) as primas_emitidas,
        coalesce(b.primas_emit_anterior, 0) as primas_emitidas_anterior
        from primas_actuales_resto a
        full outer join primas_anteriores_resto b on a.cod_cia = b.cod_cia
    ),
    base_final as (
        select *
        from base_cias_comunes
        union all
        select *
        from base_cias_diferentes
    )
    select * from base_final
    where primas_emitidas <> 0
    """


def create_table_from_query(periodo: int) -> None:
    """
    Crea tabla de compañías corregida basada en el período especificado.

    Args:
        periodo (int): Período en formato YYYYPP
    """
    validate_period(periodo)
    load_dotenv()
    database_path = os.getenv('DATABASE')

    periodo_str = str(periodo)
    quarter = int(periodo_str[4:])

    try:
        with sqlite3.connect(database_path) as conn:
            conn.execute("DROP TABLE IF EXISTS base_cias_corregida_actual")

            periods = calculate_periods(periodo)
            logging.info(f"Procesando período {periodo} (trimestre {quarter}) para tabla de compañías")
            logging.info(f"Períodos calculados: {periods}")

            # Seleccionar query según el trimestre
            if quarter == 1:  # Marzo
                query = build_query_for_march(periods)
            elif quarter == 2:  # Junio
                query = build_query_for_june(periods)
            elif quarter == 3:  # Septiembre
                query = build_query_for_september(periods)
            elif quarter == 4:  # Diciembre
                query = build_query_for_december(periods)
            else:
                raise ValueError(f"Trimestre inválido: {quarter}")

            conn.execute(query)

            count = pd.read_sql_query("SELECT COUNT(*) as count FROM base_cias_corregida_actual", conn)
            logging.info(f"Tabla base_cias_corregida_actual creada con {count['count'].iloc[0]:,} registros")

    except sqlite3.Error as e:
        logging.error(f"Error en base de datos: {e}")
        raise
    except Exception as e:
        logging.error(f"Error inesperado: {e}")
        raise


def main(periodo: int) -> None:
    """
    Función principal para crear tabla de compañías corregida.

    Args:
        periodo (int): Período a procesar en formato YYYYPP
    """
    create_table_from_query(periodo)


if __name__ == "__main__":
    setup_logging()

    parser = argparse.ArgumentParser(
        description='Crea tabla de compañías corregida para el período especificado',
        epilog="""
Ejemplos:
  python modules/crea_tabla_cias_corregida.py 202501    # Marzo 2025
  python modules/crea_tabla_cias_corregida.py 202502    # Junio 2025
  python modules/crea_tabla_cias_corregida.py 202503    # Septiembre 2025
  python modules/crea_tabla_cias_corregida.py 202504    # Diciembre 2025

Nota: El módulo aplica correcciones automáticas para las compañías especiales
(códigos 0829, 0541, 0686) que cierran en diciembre en lugar de junio.
Esta versión trabaja a nivel de COMPAÑÍA, agregando todos los subramos.
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        'periodo',
        type=int,
        help='Período a procesar en formato YYYYPP (ej: 202501 para marzo 2025)'
    )

    args = parser.parse_args()
    main(args.periodo)
