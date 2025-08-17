import pandas as pd
import os
import argparse
from pathlib import Path
from dotenv import load_dotenv
import sqlite3
import logging
from typing import Optional
from .common import validate_period, setup_logging
from utils.db_manager import db_manager

def create_recent_periods_table(periodo_inicial: Optional[int] = None) -> None:
    """
    Crea una tabla con datos de balance de períodos desde una fecha específica.
    
    Esta función genera una nueva tabla 'base_balance_ultimos_periodos' con los datos
    filtrados a partir del período especificado. Si no se especifica un período,
    se utilizan los últimos 2 años por defecto.

    Args:
        periodo_inicial (Optional[int]): Período inicial desde el cual filtrar los datos,
                                       en formato YYYYPP donde PP es el trimestre (01-04).
                                       Si es None, se calculan los últimos 2 años.
    
    Returns:
        None
    
    Raises:
        sqlite3.Error: Si ocurre un error en las operaciones de base de datos
    """
    # Si no se especifica periodo, usar los últimos 2 años
    if periodo_inicial is None:
        import datetime
        anio_actual = datetime.datetime.now().year
        periodo_inicial = int(f"{anio_actual - 2}00")
    else:
        validate_period(periodo_inicial)

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
        description='Crea tabla con datos de períodos recientes',
        epilog="""
Ejemplos:
  python modules/crea_tabla_ultimos_periodos.py --periodo_inicial 202301
  python modules/crea_tabla_ultimos_periodos.py  # Usa últimos 2 años por defecto
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--periodo_inicial', 
        type=int, 
        help='Período inicial (formato YYYYPP) desde el cual filtrar los datos'
    )
    
    args = parser.parse_args()
    create_recent_periods_table(args.periodo_inicial)