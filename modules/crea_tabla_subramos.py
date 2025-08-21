"""
Module to create base_subramos table with aggregated insurance data by subramo.

This module processes balance data and creates aggregated metrics per company,
period, and subramo using account mappings defined in conceptos_reportes and
parametros_reportes tables.

The resulting base_subramos table contains:
- primas_emitidas, primas_devengadas
- siniestros_devengados, gastos_totales_devengados  
- primas_cedidas
- gs_prod_comisiones, gs_prod_otros, gs_exp_sueldos, gs_a_c_reaseguro

Usage:
    python modules/crea_tabla_subramos.py [--periodo_inicial YYYYPP]

Example:
    python modules/crea_tabla_subramos.py --periodo_inicial 202301
"""

import pandas as pd
import sqlite3
import logging
import os
import argparse
from dotenv import load_dotenv
from typing import Dict, Tuple, Optional
from modules.common import setup_logging, format_number
from utils.db_manager import db_manager

logger = logging.getLogger(__name__)


def get_data(conn: sqlite3.Connection, periodo_inicial: int) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Obtiene datos necesarios de la base de datos para generar reportes por subramos.

    Args:
        conn (sqlite3.Connection): Conexión a la base de datos
        periodo_inicial (int): Período inicial desde el cual filtrar (formato YYYYPP)

    Returns:
        Tuple[pd.DataFrame, pd.DataFrame]: Tupla con (dataframe base, parámetros de reportes)
    
    Raises:
        ValueError: Si no se encuentran las tablas requeridas
    """
    logger.info(f"Obteniendo datos desde período {periodo_inicial}")
    
    # Verificar que las tablas existan
    required_tables = ['base_balance_ultimos_periodos', 'conceptos_reportes', 'parametros_reportes']
    for table in required_tables:
        if not db_manager.table_exists(table):
            raise ValueError(
                f"Required table '{table}' does not exist. "
                f"Make sure to run the prerequisites modules first."
            )
    
    # Obtener datos base
    base = pd.read_sql_query(
        f"SELECT * FROM base_balance_ultimos_periodos WHERE periodo >= {periodo_inicial}",
        conn
    )
    
    if len(base) == 0:
        raise ValueError(
            f"No data found in base_balance_ultimos_periodos for period >= {periodo_inicial}. "
            f"Make sure to run crea_tabla_ultimos_periodos.py first."
        )
    
    # Obtener filtros para subramos
    filtro = pd.read_sql_query(
        "SELECT * FROM conceptos_reportes WHERE es_subramo = 1", 
        conn
    )
    
    if len(filtro) == 0:
        raise ValueError(
            "No subramo concepts found in conceptos_reportes table. "
            f"Make sure the table is properly configured."
        )
    
    # Obtener parámetros completos
    params_full = pd.read_sql_query(
        "SELECT * FROM parametros_reportes",
        conn
    )
    
    if len(params_full) == 0:
        raise ValueError(
            "No parameters found in parametros_reportes table. "
            f"Make sure the table is properly configured."
        )

    # Hacer merge para obtener solo parámetros de conceptos de subramos
    parametros_reportes = params_full.merge(filtro, on=['reporte', 'referencia'], how='inner')
    
    if len(parametros_reportes) == 0:
        raise ValueError(
            "No matching parameters found for subramo concepts. "
            f"Check the join between parametros_reportes and conceptos_reportes."
        )
    
    logger.info(f"Base data loaded: {format_number(len(base))} records")
    logger.info(f"Subramo concepts: {len(filtro)} concepts")
    logger.info(f"Matching parameters: {len(parametros_reportes)} mappings")
    
    return base, parametros_reportes


def generate_subramos_table(data: pd.DataFrame, codigos: Dict[str, Dict[str, int]]) -> pd.DataFrame:
    """
    Genera tabla agregada por subramos aplicando mapeos de códigos contables.

    Args:
        data (pd.DataFrame): DataFrame con datos base de balance
        codigos (Dict[str, Dict[str, int]]): Diccionario con mapeos de códigos y signos
                                           Estructura: {concepto: {cod_cuenta: signo}}

    Returns:
        pd.DataFrame: DataFrame agregado por cod_cia, periodo, cod_subramo
    """
    logger.info(f"Processing {format_number(len(data))} records with {len(codigos)} concepts")
    
    result = data.copy()
    
    # Log available concepts
    logger.info(f"Available concepts: {list(codigos.keys())}")

    # Aplicar mapeos para cada concepto
    for concepto, mapping in codigos.items():
        if len(mapping) == 0:
            logger.warning(f"No account mappings found for concept: {concepto}")
            result[concepto] = 0
        else:
            # Crear columna mapeando códigos de cuenta con signos
            result[concepto] = result['cod_cuenta'].map(mapping).fillna(0) * result['importe']
            mapped_count = (result['cod_cuenta'].isin(mapping.keys())).sum()
            logger.info(f"Concept '{concepto}': {len(mapping)} account codes, {mapped_count} records matched")

    # Agrupar por compañía, período y subramo
    logger.info("Aggregating data by cod_cia, periodo, cod_subramo...")
    
    aggregated = result.groupby(
        by=['cod_cia', 'periodo', 'cod_subramo'],
        as_index=False
    ).agg(
        primas_emitidas=('primas_emitidas', 'sum'),
        primas_devengadas=('primas_devengadas', 'sum'),
        siniestros_devengados=('siniestros_devengados', 'sum'),
        gastos_totales_devengados=('gastos_devengados', 'sum'),
        primas_cedidas=('primas_cedidas', 'sum'),
        gs_prod_comisiones=('gs_prod_comisiones', 'sum'),
        gs_prod_otros=('gs_prod_otros', 'sum'),
        gs_exp_sueldos=('gs_exp_sueldos', 'sum'),
        gs_a_c_reaseguro=('gs_a_c_reaseg', 'sum'),
    )
    
    logger.info(f"Aggregation complete: {format_number(len(aggregated))} final records")
    
    return aggregated


def main(periodo_inicial: Optional[int] = None) -> None:
    """
    Crea tabla base_subramos con información agregada por subramos.
    
    Esta función agrupa los datos por compañía, período y subramo, calculando
    diferentes métricas como primas emitidas, primas devengadas, siniestros
    devengados, gastos totales devengados y primas cedidas.

    Args:
        periodo_inicial (Optional[int]): Período inicial desde el cual filtrar los datos.
                                       Si es None, se calculan los últimos 2 años.
    """
    load_dotenv()
    database_path = os.getenv('DATABASE')
    
    if not database_path:
        raise ValueError("DATABASE environment variable not set")

    # Si no se especifica periodo, usar los últimos 2 años
    if periodo_inicial is None:
        import datetime
        anio_actual = datetime.datetime.now().year
        periodo_inicial = int(f"{anio_actual - 2}00")

    logger.info(f"Creating base_subramos table with data from period: {periodo_inicial}")
    logger.info(f"Database: {database_path}")

    try:
        with sqlite3.connect(database_path) as conn:
            # Obtener datos y parámetros
            base, parametros_reportes = get_data(conn, periodo_inicial)
            
            # Crear mapeo de códigos por concepto
            logger.info("Building account code mappings...")
            codigos_map = {}
            
            for concepto in parametros_reportes['concepto'].unique():
                concepto_data = parametros_reportes[parametros_reportes['concepto'] == concepto]
                mapping = dict(zip(concepto_data['cod_cuenta'], concepto_data['signo']))
                codigos_map[concepto] = mapping
                logger.info(f"Concept '{concepto}': {len(mapping)} account codes mapped")

            # Generar tabla agregada
            result_df = generate_subramos_table(base, codigos_map)
            
            # Mostrar estadísticas por período
            periods = sorted(result_df['periodo'].unique())
            companies = result_df['cod_cia'].nunique()
            subramos = result_df['cod_subramo'].nunique()
            
            logger.info(f"Final statistics:")
            logger.info(f"  - Periods: {len(periods)} ({periods[0]} to {periods[-1]})")
            logger.info(f"  - Companies: {companies}")
            logger.info(f"  - Subramos: {subramos}")
            logger.info(f"  - Total records: {format_number(len(result_df))}")
            
            # Crear nueva tabla
            logger.info("Creating base_subramos table...")
            conn.execute("DROP TABLE IF EXISTS base_subramos")
            result_df.to_sql('base_subramos', conn, index=False)
            
            # Verificar creación
            count = pd.read_sql_query("SELECT COUNT(*) as count FROM base_subramos", conn)
            logger.info(f"✅ Table base_subramos created successfully with {format_number(count['count'].iloc[0])} records")

    except sqlite3.Error as e:
        logger.error(f"❌ Database error: {e}")
        raise
    except Exception as e:
        logger.error(f"❌ Error creating base_subramos table: {e}")
        raise


if __name__ == "__main__":
    setup_logging()
    
    parser = argparse.ArgumentParser(
        description='Create base_subramos table with aggregated insurance data',
        epilog="""
Examples:
  python modules/crea_tabla_subramos.py
  python modules/crea_tabla_subramos.py --periodo_inicial 202301

Prerequisites:
  1. Run crea_tabla_ultimos_periodos.py first
  2. Ensure conceptos_reportes and parametros_reportes tables are configured

Output:
  Creates base_subramos table with aggregated data by cod_cia, periodo, cod_subramo
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--periodo_inicial', 
        type=int, 
        help='Initial period (YYYYPP format) to filter data from. Default: last 2 years'
    )
    
    args = parser.parse_args()
    
    main(args.periodo_inicial)