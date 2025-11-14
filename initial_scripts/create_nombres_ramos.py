import pandas as pd
import os
from pathlib import Path
from dotenv import load_dotenv
import sqlite3
import logging
import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def create_companies_table() -> None:
    """Crea tabla con datos de las compañías desde el CSV"""
    load_dotenv()
    database_path = os.getenv('DATABASE')
    file_path = '../nombres_ramos.csv'

    try:
        # Leer el CSV
        df = pd.read_csv(file_path, sep=',')
        
        with sqlite3.connect(database_path) as conn:
            # Crear la tabla e insertar datos
            df.to_sql('datos_ramos_subramos', conn, if_exists='replace', index=False)
            
            # Verificar cantidad de registros
            count = pd.read_sql_query("SELECT COUNT(*) as count FROM datos_ramos_subramos", conn)
            logging.info(f"Tabla creada con {count['count'].iloc[0]:,} registros")
            
    except pd.errors.EmptyDataError:
        logging.error("El archivo CSV está vacío o no se pudo leer correctamente")
    except sqlite3.Error as e:
        logging.error(f"Error en base de datos: {e}")
    except Exception as e:
        logging.error(f"Error inesperado: {e}")

if __name__ == "__main__":
    create_companies_table()