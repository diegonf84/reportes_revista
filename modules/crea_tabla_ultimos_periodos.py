import pandas as pd
import os
import argparse
from pathlib import Path
from dotenv import load_dotenv
import sqlite3
import logging
from typing import Optional

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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
    load_dotenv()
    database_path = os.getenv('DATABASE')
    
    # Si no se especifica periodo, usar los últimos 2 años
    if periodo_inicial is None:
        import datetime
        anio_actual = datetime.datetime.now().year
        periodo_inicial = int(f"{anio_actual - 2}00")

    logging.info(f"Filtrando datos desde el período: {periodo_inicial}")

    try:
        with sqlite3.connect(database_path) as conn:
            conn.execute("DROP TABLE IF EXISTS base_balance_ultimos_periodos")
            
            query = f"""
            CREATE TABLE base_balance_ultimos_periodos AS 
            SELECT * FROM datos_balance 
            WHERE periodo >= {periodo_inicial}
            """
            conn.execute(query)
            
            count = pd.read_sql_query("SELECT COUNT(*) as count FROM base_balance_ultimos_periodos", conn)
            logging.info(f"Tabla creada con {count['count'].iloc[0]:,} registros")
            
    except sqlite3.Error as e:
        logging.error(f"Error en base de datos: {e}")
        raise

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Crea tabla con datos de períodos recientes')
    parser.add_argument('--periodo_inicial', type=int, 
                        help='Período inicial (formato YYYYPP) desde el cual filtrar los datos')
    args = parser.parse_args()
    
    create_recent_periods_table(args.periodo_inicial)