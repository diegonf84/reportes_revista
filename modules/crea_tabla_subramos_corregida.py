"""
Módulo para crear tabla de subramos corregida basada en período especificado.

Este módulo reemplaza los archivos específicos de diciembre y marzo con una 
implementación parametrizada que funciona para cualquier período.
"""

import pandas as pd
import os
import argparse
from pathlib import Path
from dotenv import load_dotenv
import sqlite3
import logging
from .common import validate_period, setup_logging

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
    CREATE TABLE base_subramos_corregida_actual AS
    with primas_diferentes_marzo_actual as (
        select cod_cia, cod_subramo,
        sum(primas_emitidas) as primas_emit_mar_actual
        from base_subramos
        where periodo in ('{periods["actual"]}')
        and cod_cia in ('0829','0541','0686')
        GROUP by cod_cia, cod_subramo
    ),
    primas_diferentes_junio_actual as (
        select cod_cia, cod_subramo,
        sum(primas_emitidas) as primas_emit_jun_actual
        from base_subramos
        where periodo in ('{periods["junio_actual"]}')
        and cod_cia in ('0829','0541','0686')
        GROUP by cod_cia, cod_subramo
    ),
    primas_diferentes_diciembre_actual as (
        select cod_cia, cod_subramo,
        sum(primas_emitidas) as primas_emit_dic_actual
        from base_subramos
        where periodo in ('{periods["diciembre_actual"]}')
        and cod_cia in ('0829','0541','0686')
        GROUP by cod_cia, cod_subramo
    ),
    primas_diferentes_marzo_anterior as (
        select cod_cia, cod_subramo,
        sum(primas_emitidas) as primas_emit_mar_anterior
        from base_subramos
        where periodo in ('{periods["anterior_mismo_trimestre"]}')
        and cod_cia in ('0829','0541','0686')
        GROUP by cod_cia, cod_subramo
    ),
    primas_diferentes_junio_anterior as (
        select cod_cia, cod_subramo,
        sum(primas_emitidas) as primas_emit_jun_anterior
        from base_subramos
        where periodo in ('{periods["junio_anterior"]}')
        and cod_cia in ('0829','0541','0686')
        GROUP by cod_cia, cod_subramo
    ),
    primas_diferentes_diciembre_anterior as (
        select cod_cia, cod_subramo,
        sum(primas_emitidas) as primas_emit_dic_anterior
        from base_subramos
        where periodo in ('{periods["diciembre_anterior"]}')
        and cod_cia in ('0829','0541','0686')
        GROUP by cod_cia, cod_subramo
    ),
    base_cias_diferentes as (
        select a.cod_cia, a.cod_subramo, 
        a.primas_emit_mar_actual - b.primas_emit_jun_actual + c.primas_emit_dic_actual as primas_emitidas, 
        d.primas_emit_mar_anterior - e.primas_emit_jun_anterior + f.primas_emit_dic_anterior as primas_emitidas_anterior
        from primas_diferentes_marzo_actual a
        join primas_diferentes_junio_actual b on a.cod_cia = b.cod_cia and a.cod_subramo = b.cod_subramo
        join primas_diferentes_diciembre_actual c on a.cod_cia = c.cod_cia and a.cod_subramo = c.cod_subramo
        join primas_diferentes_marzo_anterior d on a.cod_cia = d.cod_cia and a.cod_subramo = d.cod_subramo
        join primas_diferentes_junio_anterior e on a.cod_cia = e.cod_cia and a.cod_subramo = e.cod_subramo
        join primas_diferentes_diciembre_anterior f on a.cod_cia = f.cod_cia and a.cod_subramo = f.cod_subramo
    ),
    primas_actuales_resto as (
        select cod_cia, cod_subramo,
        sum(primas_emitidas) as primas_emit_actual
        from base_subramos
        where periodo in ('{periods["actual"]}')
        and cod_cia not in ('0829','0541','0686')
        GROUP by cod_cia,cod_subramo
    ),
    primas_anteriores_resto as (
        select cod_cia, cod_subramo,
        sum(primas_emitidas) as primas_emit_anterior
        from base_subramos
        where periodo in ('{periods["anterior_mismo_trimestre"]}')
        and cod_cia not in ('0829','0541','0686')
        GROUP by cod_cia,cod_subramo
    ),
    base_cias_comunes as (
        select a.cod_cia, a.cod_subramo, a.primas_emit_actual as primas_emitidas, 
        iif(b.primas_emit_anterior is null, 0, b.primas_emit_anterior) as primas_emitidas_anterior
        from primas_actuales_resto a
        left join primas_anteriores_resto b on a.cod_cia = b.cod_cia and a.cod_subramo = b.cod_subramo
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
    CREATE TABLE base_subramos_corregida_actual AS
    with primas_dif_dic_actual as (
        select cod_cia, cod_subramo,
        sum(primas_emitidas) as primas_emit_dic_actual
        from base_subramos
        where periodo in ('{periods["actual"]}')
        and cod_cia in ('0829','0541','0686')
        GROUP by cod_cia,cod_subramo
    ),
    primas_dif_jun_actual as (
        select cod_cia, cod_subramo,
        sum(primas_emitidas) as primas_emit_jun_actual
        from base_subramos
        where periodo in ('{periods["junio_actual"]}')
        and cod_cia in ('0829','0541','0686')
        GROUP by cod_cia,cod_subramo
    ),
    primas_dif_dic_anterior as (
        select cod_cia, cod_subramo,
        sum(primas_emitidas) as primas_emit_dic_anterior
        from base_subramos
        where periodo in ('{periods["anterior_mismo_trimestre"]}')
        and cod_cia in ('0829','0541','0686')
        GROUP by cod_cia,cod_subramo
    ),
    primas_dif_jun_anterior as (
        select cod_cia, cod_subramo,
        sum(primas_emitidas) as primas_emit_jun_anterior
        from base_subramos
        where periodo in ('{periods["junio_anterior"]}')
        and cod_cia in ('0829','0541','0686')
        GROUP by cod_cia,cod_subramo
    ),
    base_cias_diferentes as (
        select a.cod_cia, a.cod_subramo, 
        a.primas_emit_dic_actual - b.primas_emit_jun_actual as primas_emitidas, 
        c.primas_emit_dic_anterior - d.primas_emit_jun_anterior as primas_emitidas_anterior
        from primas_dif_dic_actual a
        join primas_dif_jun_actual b on a.cod_cia = b.cod_cia and a.cod_subramo = b.cod_subramo
        join primas_dif_dic_anterior c on a.cod_cia = c.cod_cia and a.cod_subramo = c.cod_subramo
        join primas_dif_jun_anterior d on a.cod_cia = d.cod_cia and a.cod_subramo = d.cod_subramo
    ),
    primas_actuales_resto as (
        select cod_cia, cod_subramo,
        sum(primas_emitidas) as primas_emit_actual
        from base_subramos
        where periodo in ('{periods["actual"]}')
        and cod_cia not in ('0829','0541','0686')
        GROUP by cod_cia,cod_subramo
    ),
    primas_anteriores_resto as (
        select cod_cia, cod_subramo,
        sum(primas_emitidas) as primas_emit_anterior
        from base_subramos
        where periodo in ('{periods["anterior_mismo_trimestre"]}')
        and cod_cia not in ('0829','0541','0686')
        GROUP by cod_cia,cod_subramo
    ),
    base_cias_comunes as (
        select a.cod_cia, a.cod_subramo, a.primas_emit_actual as primas_emitidas, 
        iif(b.primas_emit_anterior is null, 0, b.primas_emit_anterior) as primas_emitidas_anterior
        from primas_actuales_resto a
        left join primas_anteriores_resto b on a.cod_cia = b.cod_cia and a.cod_subramo = b.cod_subramo
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


def build_query_for_other_quarters(periods: dict) -> str:
    """Construye query para otros trimestres (2 y 3)."""
    return f"""
    CREATE TABLE base_subramos_corregida_actual AS
    with primas_actuales_todas as (
        select cod_cia, cod_subramo,
        sum(primas_emitidas) as primas_emit_actual
        from base_subramos
        where periodo in ('{periods["actual"]}')
        GROUP by cod_cia,cod_subramo
    ),
    primas_anteriores_todas as (
        select cod_cia, cod_subramo,
        sum(primas_emitidas) as primas_emit_anterior
        from base_subramos
        where periodo in ('{periods["anterior_mismo_trimestre"]}')
        GROUP by cod_cia,cod_subramo
    )
    select a.cod_cia, a.cod_subramo, a.primas_emit_actual as primas_emitidas, 
    iif(b.primas_emit_anterior is null, 0, b.primas_emit_anterior) as primas_emitidas_anterior
    from primas_actuales_todas a
    left join primas_anteriores_todas b on a.cod_cia = b.cod_cia and a.cod_subramo = b.cod_subramo
    where a.primas_emit_actual <> 0
    """


def create_table_from_query(periodo: int) -> None:
    """
    Crea tabla de subramos corregida basada en el período especificado.
    
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
            conn.execute("DROP TABLE IF EXISTS base_subramos_corregida_actual")
            
            periods = calculate_periods(periodo)
            logging.info(f"Procesando período {periodo} (trimestre {quarter})")
            logging.info(f"Períodos calculados: {periods}")
            
            # Seleccionar query según el trimestre
            if quarter == 1:  # Marzo
                query = build_query_for_march(periods)
            elif quarter == 4:  # Diciembre
                query = build_query_for_december(periods)
            else:  # Trimestres 2 y 3
                query = build_query_for_other_quarters(periods)
            
            conn.execute(query)
            
            count = pd.read_sql_query("SELECT COUNT(*) as count FROM base_subramos_corregida_actual", conn)
            logging.info(f"Tabla creada con {count['count'].iloc[0]:,} registros")
            
    except sqlite3.Error as e:
        logging.error(f"Error en base de datos: {e}")
        raise
    except Exception as e:
        logging.error(f"Error inesperado: {e}")
        raise


def main(periodo: int) -> None:
    """
    Función principal para crear tabla de subramos corregida.
    
    Args:
        periodo (int): Período a procesar en formato YYYYPP
    """
    create_table_from_query(periodo)


if __name__ == "__main__":
    setup_logging()
    
    parser = argparse.ArgumentParser(
        description='Crea tabla de subramos corregida para el período especificado',
        epilog="""
Ejemplos:
  python modules/crea_tabla_subramos_corregida.py 202501    # Marzo 2025
  python modules/crea_tabla_subramos_corregida.py 202504    # Diciembre 2025
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