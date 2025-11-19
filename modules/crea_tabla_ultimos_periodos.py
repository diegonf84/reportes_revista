import pandas as pd
import os
import argparse
from pathlib import Path
from dotenv import load_dotenv
import sqlite3
import logging
from typing import Optional
from modules.common import validate_period, setup_logging
from utils.db_manager import db_manager

def create_recent_periods_table(periodo_referencia: Optional[int] = None) -> None:
    """
    Crea una tabla con datos de balance de períodos desde una fecha específica.

    Esta función genera una nueva tabla 'base_balance_ultimos_periodos' con los datos
    filtrados usando los últimos 2 años desde el período de referencia.

    Args:
        periodo_referencia: Período de referencia (formato YYYYPP).
                          Si es None, usa el año actual.

    Returns:
        None

    Raises:
        sqlite3.Error: Si ocurre un error en las operaciones de base de datos
    """
    # Determinar período inicial (2 años atrás desde la referencia)
    import datetime

    if periodo_referencia is None:
        # DEFAULT: Usar año actual
        anio_actual = datetime.datetime.now().year
        periodo_inicial = int(f"{anio_actual - 2}00")
        logging.info(f"Modo automático: usando período de referencia = año actual ({anio_actual})")
    else:
        # SPECIFIED: Usar período especificado
        year = int(str(periodo_referencia)[:4])
        periodo_inicial = int(f"{year - 2}00")
        logging.info(f"Modo manual: usando período de referencia = {periodo_referencia}")

    logging.info(f"Filtrando datos desde el período: {periodo_inicial}")

    try:
        db_manager.drop_table_if_exists("base_balance_ultimos_periodos")
        
        query = f"""
        CREATE TABLE base_balance_ultimos_periodos AS 
        SELECT * FROM datos_balance 
        WHERE periodo >= {periodo_inicial}
        """
        db_manager.execute_non_query(query)
        
        count = db_manager.get_table_count("base_balance_ultimos_periodos")
        logging.info(f"Tabla creada con {count:,} registros")
        
    except Exception as e:
        logging.error(f"Error creando tabla: {e}")
        raise

if __name__ == "__main__":
    setup_logging()

    parser = argparse.ArgumentParser(
        description='Crea tabla con datos de períodos recientes usando los últimos 2 años',
        epilog="""
Ejemplos:
  python modules/crea_tabla_ultimos_periodos.py
    (Usa automáticamente el año actual como referencia)

  python modules/crea_tabla_ultimos_periodos.py --periodo 202503
    (Usa 202503 como referencia, filtra desde 202303)

Este módulo usa los últimos 2 años desde el período de referencia para garantizar
que todas las correcciones trimestrales tengan suficiente información histórica.
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument('--periodo', type=int, help='Período de referencia (formato YYYYPP). Si no se especifica, usa el año actual.')

    args = parser.parse_args()
    create_recent_periods_table(args.periodo)