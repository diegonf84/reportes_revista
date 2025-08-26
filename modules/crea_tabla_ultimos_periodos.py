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

def create_recent_periods_table() -> None:
    """
    Crea una tabla con datos de balance de períodos desde una fecha específica.
    
    Esta función genera una nueva tabla 'base_balance_ultimos_periodos' con los datos
    filtrados automáticamente usando los últimos 2 años de datos disponibles.
    
    Returns:
        None
    
    Raises:
        sqlite3.Error: Si ocurre un error en las operaciones de base de datos
    """
    # Usar automáticamente los últimos 2 años
    import datetime
    anio_actual = datetime.datetime.now().year
    periodo_inicial = int(f"{anio_actual - 2}00")

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
        description='Crea tabla con datos de períodos recientes usando automáticamente los últimos 2 años',
        epilog="""
Ejemplo:
  python modules/crea_tabla_ultimos_periodos.py

Este módulo usa automáticamente los últimos 2 años de datos para garantizar
que todas las correcciones trimestrales tengan suficiente información histórica.
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    args = parser.parse_args()
    create_recent_periods_table()