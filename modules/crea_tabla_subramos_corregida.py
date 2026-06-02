"""
Módulo para crear tabla de subramos corregida basada en período especificado.

Este módulo maneja las diferencias en los ciclos de cierre de las compañías aseguradoras:
- Compañías normales: cierran sus reportes financieros en junio (12 meses: julio-junio)
- Compañías especiales (0829, 0541, 0686): cierran en diciembre (12 meses: enero-diciembre)

Para normalizar los datos y que todas reporten el mismo período de 12 meses, se aplican
correcciones específicas según el trimestre solicitado:

LÓGICA POR TRIMESTRE:

1. MARZO (Trimestre 1):
   - Compañías normales: marzo actual vs marzo anterior (directo)
   - Compañías especiales: necesitan calcular 12 meses terminados en marzo
     * Actual: marzo_actual - junio_anterior + diciembre_anterior
     * Anterior: marzo_anterior - junio_prev_prev + diciembre_prev_prev
   
2. JUNIO (Trimestre 2):
   - Compañías normales: junio actual vs junio anterior (directo)
   - Compañías especiales: necesitan calcular 12 meses terminados en junio
     * Actual: junio_actual + diciembre_anterior - junio_anterior
     * Anterior: junio_anterior + diciembre_prev_prev - junio_prev_prev

3. SEPTIEMBRE (Trimestre 3):
   - Compañías normales: septiembre actual vs septiembre anterior (directo)
   - Compañías especiales: necesitan calcular 12 meses terminados en septiembre
     * Actual: septiembre_actual - junio_actual
     * Anterior: septiembre_anterior - junio_anterior

4. DICIEMBRE (Trimestre 4):
   - Compañías normales: diciembre actual vs diciembre anterior (directo)
   - Compañías especiales: necesitan calcular 12 meses terminados en diciembre
     * Actual: diciembre_actual - junio_actual
     * Anterior: diciembre_anterior - junio_anterior

EXPLICACIÓN DE LAS CORRECCIONES:
Las compañías especiales reportan datos acumulados desde enero, por lo que:
- Para obtener 12 meses terminados en marzo: sumamos enero-marzo + julio-diciembre anterior
- Para obtener 12 meses terminados en junio: sumamos enero-junio + julio-diciembre anterior
- Para obtener 12 meses terminados en septiembre: tomamos enero-septiembre - enero-junio
- Para obtener 12 meses terminados en diciembre: tomamos enero-diciembre - enero-junio

Esto garantiza que todas las compañías reporten el mismo período de 12 meses,
independientemente de su ciclo de cierre fiscal.
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
        select coalesce(a.cod_cia, b.cod_cia) as cod_cia,
        coalesce(a.cod_subramo, b.cod_subramo) as cod_subramo,
        coalesce(a.primas_emit_actual, 0) as primas_emitidas,
        coalesce(b.primas_emit_anterior, 0) as primas_emitidas_anterior
        from primas_actuales_resto a
        full outer join primas_anteriores_resto b on a.cod_cia = b.cod_cia and a.cod_subramo = b.cod_subramo
    ),
    base_final as (
        select *
        from base_cias_comunes
        union all
        select *
        from base_cias_diferentes
    )
    select *, {periods['actual']} as periodo from base_final
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
        select coalesce(a.cod_cia, b.cod_cia) as cod_cia,
        coalesce(a.cod_subramo, b.cod_subramo) as cod_subramo,
        coalesce(a.primas_emit_actual, 0) as primas_emitidas,
        coalesce(b.primas_emit_anterior, 0) as primas_emitidas_anterior
        from primas_actuales_resto a
        full outer join primas_anteriores_resto b on a.cod_cia = b.cod_cia and a.cod_subramo = b.cod_subramo
    ),
    base_final as (
        select *
        from base_cias_comunes
        union all
        select *
        from base_cias_diferentes
    )
    select *, {periods['actual']} as periodo from base_final
    where primas_emitidas <> 0
    """


def build_query_for_june(periods: dict) -> str:
    """Construye query para procesamiento de junio (trimestre 2)."""
    return f"""
    CREATE TABLE base_subramos_corregida_actual AS
    with primas_diferentes_junio_actual as (
        select cod_cia, cod_subramo,
        sum(primas_emitidas) as primas_emit_jun_actual
        from base_subramos
        where periodo in ('{periods["actual"]}')
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
    primas_diferentes_junio_anterior as (
        select cod_cia, cod_subramo,
        sum(primas_emitidas) as primas_emit_jun_anterior
        from base_subramos
        where periodo in ('{periods["junio_anterior"]}')
        and cod_cia in ('0829','0541','0686')
        GROUP by cod_cia, cod_subramo
    ),
    primas_diferentes_junio_prev_prev as (
        select cod_cia, cod_subramo,
        sum(primas_emitidas) as primas_emit_jun_prev_prev
        from base_subramos
        where periodo in ('{periods["junio_prev_prev"]}')
        and cod_cia in ('0829','0541','0686')
        GROUP by cod_cia, cod_subramo
    ),
    primas_diferentes_diciembre_prev_prev as (
        select cod_cia, cod_subramo,
        sum(primas_emitidas) as primas_emit_dic_prev_prev
        from base_subramos
        where periodo in ('{periods["diciembre_prev_prev"]}')
        and cod_cia in ('0829','0541','0686')
        GROUP by cod_cia, cod_subramo
    ),
    base_cias_diferentes as (
        select a.cod_cia, a.cod_subramo, 
        a.primas_emit_jun_actual + b.primas_emit_dic_anterior - c.primas_emit_jun_anterior as primas_emitidas, 
        c.primas_emit_jun_anterior + e.primas_emit_dic_prev_prev - d.primas_emit_jun_prev_prev as primas_emitidas_anterior
        from primas_diferentes_junio_actual a
        join primas_diferentes_diciembre_anterior b on a.cod_cia = b.cod_cia and a.cod_subramo = b.cod_subramo
        join primas_diferentes_junio_anterior c on a.cod_cia = c.cod_cia and a.cod_subramo = c.cod_subramo
        join primas_diferentes_junio_prev_prev d on a.cod_cia = d.cod_cia and a.cod_subramo = d.cod_subramo
        join primas_diferentes_diciembre_prev_prev e on a.cod_cia = e.cod_cia and a.cod_subramo = e.cod_subramo
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
        select coalesce(a.cod_cia, b.cod_cia) as cod_cia,
        coalesce(a.cod_subramo, b.cod_subramo) as cod_subramo,
        coalesce(a.primas_emit_actual, 0) as primas_emitidas,
        coalesce(b.primas_emit_anterior, 0) as primas_emitidas_anterior
        from primas_actuales_resto a
        full outer join primas_anteriores_resto b on a.cod_cia = b.cod_cia and a.cod_subramo = b.cod_subramo
    ),
    base_final as (
        select *
        from base_cias_comunes
        union all
        select *
        from base_cias_diferentes
    )
    select *, {periods['actual']} as periodo from base_final
    where primas_emitidas <> 0
    """


def build_query_for_september(periods: dict) -> str:
    """Construye query para procesamiento de septiembre (trimestre 3)."""
    return f"""
    CREATE TABLE base_subramos_corregida_actual AS
    with primas_dif_sep_actual as (
        select cod_cia, cod_subramo,
        sum(primas_emitidas) as primas_emit_sep_actual
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
    primas_dif_sep_anterior as (
        select cod_cia, cod_subramo,
        sum(primas_emitidas) as primas_emit_sep_anterior
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
        a.primas_emit_sep_actual - b.primas_emit_jun_actual as primas_emitidas,
        c.primas_emit_sep_anterior - d.primas_emit_jun_anterior as primas_emitidas_anterior
        from primas_dif_sep_actual a
        join primas_dif_jun_actual b on a.cod_cia = b.cod_cia and a.cod_subramo = b.cod_subramo
        join primas_dif_sep_anterior c on a.cod_cia = c.cod_cia and a.cod_subramo = c.cod_subramo
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
        select coalesce(a.cod_cia, b.cod_cia) as cod_cia,
        coalesce(a.cod_subramo, b.cod_subramo) as cod_subramo,
        coalesce(a.primas_emit_actual, 0) as primas_emitidas,
        coalesce(b.primas_emit_anterior, 0) as primas_emitidas_anterior
        from primas_actuales_resto a
        full outer join primas_anteriores_resto b on a.cod_cia = b.cod_cia and a.cod_subramo = b.cod_subramo
    ),
    base_final as (
        select *
        from base_cias_comunes
        union all
        select *
        from base_cias_diferentes
    )
    select *, {periods['actual']} as periodo from base_final
    where primas_emitidas <> 0
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
            elif quarter == 2:  # Junio
                query = build_query_for_june(periods)
            elif quarter == 3:  # Septiembre
                query = build_query_for_september(periods)
            elif quarter == 4:  # Diciembre
                query = build_query_for_december(periods)
            else:
                raise ValueError(f"Trimestre inválido: {quarter}")
            
            conn.execute(query)
            
            count = pd.read_sql_query("SELECT COUNT(*) as count FROM base_subramos_corregida_actual", conn)
            logging.info(f"Tabla creada con {count['count'].iloc[0]:,} registros")
            
    except sqlite3.Error as e:
        logging.error(f"Error en base de datos: {e}")
        raise
    except Exception as e:
        logging.error(f"Error inesperado: {e}")
        raise


def export_testing_data(periodo: int) -> None:
    """
    Exporta datos simplificados para testing de la lógica de corrección.
    
    Genera UN SOLO archivo CSV con todas las columnas de períodos side-by-side
    para verificar rápidamente los cálculos.
    
    Args:
        periodo (int): Período a procesar en formato YYYYPP
    """
    validate_period(periodo)
    load_dotenv()
    database_path = os.getenv('DATABASE')
    
    periodo_str = str(periodo)
    quarter = int(periodo_str[4:])
    
    try:
        with sqlite3.connect(database_path) as conn:
            periods = calculate_periods(periodo)
            logging.info(f"Exportando datos de testing para período {periodo} (trimestre {quarter})")
            logging.info(f"Períodos involucrados: {periods}")
            
            # Crear directorio para archivos de testing si no existe
            test_dir = Path(__file__).parent / "testing_data"
            test_dir.mkdir(exist_ok=True)
            
            # Obtener todas las combinaciones de compañías especiales y subramos
            query_base = """
            SELECT DISTINCT cod_cia, cod_subramo
            FROM base_subramos 
            WHERE cod_cia IN ('0829','0541','0686')
            ORDER BY cod_cia, cod_subramo
            """
            base_df = pd.read_sql_query(query_base, conn)
            
            # Función para obtener primas de un período específico
            def get_primas_periodo(periodo_value, nombre_periodo):
                query = f"""
                SELECT cod_cia, cod_subramo, sum(primas_emitidas) as {nombre_periodo}
                FROM base_subramos 
                WHERE periodo = {periodo_value}
                AND cod_cia IN ('0829','0541','0686')
                GROUP BY cod_cia, cod_subramo
                """
                return pd.read_sql_query(query, conn)
            
            # Obtener datos de todos los períodos involucrados
            result_df = base_df.copy()
            
            # Agregar datos del período actual
            actual_df = get_primas_periodo(periodo, f"actual_T{quarter}")
            result_df = result_df.merge(actual_df, on=['cod_cia', 'cod_subramo'], how='left')
            
            # Agregar datos de período anterior (mismo trimestre)
            anterior_df = get_primas_periodo(periods['anterior_mismo_trimestre'], f"anterior_T{quarter}")
            result_df = result_df.merge(anterior_df, on=['cod_cia', 'cod_subramo'], how='left')
            
            # Agregar datos de períodos específicos según trimestre
            for period_name, period_value in periods.items():
                if period_name not in ['actual', 'anterior_mismo_trimestre']:
                    period_df = get_primas_periodo(period_value, period_name)
                    result_df = result_df.merge(period_df, on=['cod_cia', 'cod_subramo'], how='left')
            
            # Llenar valores nulos con 0
            result_df = result_df.fillna(0)
            
            # Calcular los resultados según el trimestre
            if quarter == 1:  # Marzo
                result_df['calculo_actual'] = (result_df[f'actual_T{quarter}'] - 
                                              result_df.get('junio_actual', 0) + 
                                              result_df.get('diciembre_actual', 0))
                result_df['calculo_anterior'] = (result_df[f'anterior_T{quarter}'] - 
                                                result_df.get('junio_anterior', 0) + 
                                                result_df.get('diciembre_anterior', 0))
                result_df['formula'] = "actual_T1 - junio_actual + diciembre_actual"
                
            elif quarter == 2:  # Junio  
                result_df['calculo_actual'] = (result_df[f'actual_T{quarter}'] + 
                                              result_df.get('diciembre_anterior', 0) - 
                                              result_df.get('junio_anterior', 0))
                result_df['calculo_anterior'] = (result_df.get('junio_anterior', 0) + 
                                                result_df.get('diciembre_prev_prev', 0) - 
                                                result_df.get('junio_prev_prev', 0))
                result_df['formula'] = "actual_T2 + diciembre_anterior - junio_anterior"
                
            elif quarter == 3:  # Septiembre
                result_df['calculo_actual'] = (result_df[f'actual_T{quarter}'] -
                                              result_df.get('junio_actual', 0))
                result_df['calculo_anterior'] = (result_df[f'anterior_T{quarter}'] -
                                                result_df.get('junio_anterior', 0))
                result_df['formula'] = "actual_T3 - junio_actual"

            elif quarter == 4:  # Diciembre
                result_df['calculo_actual'] = (result_df[f'actual_T{quarter}'] -
                                              result_df.get('junio_actual', 0))
                result_df['calculo_anterior'] = (result_df[f'anterior_T{quarter}'] -
                                                result_df.get('junio_anterior', 0))
                result_df['formula'] = "actual_T4 - junio_actual"
            
            # Agregar información adicional
            result_df['periodo_procesado'] = periodo
            result_df['trimestre'] = quarter
            result_df['tipo_cia'] = 'especial'
            
            # Reordenar columnas para mejor legibilidad
            cols_base = ['cod_cia', 'cod_subramo', 'periodo_procesado', 'trimestre', 'tipo_cia']
            cols_periodos = [col for col in result_df.columns if col not in cols_base and col not in ['calculo_actual', 'calculo_anterior', 'formula']]
            cols_calculos = ['calculo_actual', 'calculo_anterior', 'formula']
            
            result_df = result_df[cols_base + cols_periodos + cols_calculos]
            
            # Exportar archivo único
            csv_path = test_dir / f"{periodo}_test_simple.csv"
            result_df.to_csv(csv_path, index=False)
            
            print(f"\n✅ Archivo de testing generado: {csv_path}")
            print(f"📊 Datos para período {periodo} (trimestre {quarter})")
            print(f"🏢 {len(result_df)} registros de compañías especiales")
            print(f"📋 Fórmula aplicada: {result_df['formula'].iloc[0] if len(result_df) > 0 else 'N/A'}")
            
    except Exception as e:
        logging.error(f"Error exportando datos de testing: {e}")
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
  python modules/crea_tabla_subramos_corregida.py 202502    # Junio 2025  
  python modules/crea_tabla_subramos_corregida.py 202503    # Septiembre 2025
  python modules/crea_tabla_subramos_corregida.py 202504    # Diciembre 2025

Nota: El módulo aplica correcciones automáticas para las compañías especiales
(códigos 0829, 0541, 0686) que cierran en diciembre en lugar de junio.
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        'periodo', 
        type=int, 
        help='Período a procesar en formato YYYYPP (ej: 202501 para marzo 2025)'
    )
    
    parser.add_argument(
        '--test', 
        action='store_true',
        help='Exportar datos de testing sin ejecutar la lógica principal'
    )
    
    args = parser.parse_args()
    
    if args.test:
        export_testing_data(args.periodo)
    else:
        main(args.periodo)