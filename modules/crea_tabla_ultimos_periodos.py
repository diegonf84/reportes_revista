import pandas as pd
import os
from pathlib import Path
from dotenv import load_dotenv
import sqlite3
import logging
import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def create_recent_periods_table() -> None:
   """Crea tabla con datos de balance de períodos recientes"""
   load_dotenv()
   database_path = os.getenv('DATABASE')
   
   anio_actual = datetime.datetime.now().year
   periodo_inicial = int(f"{anio_actual - 2}00")

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

if __name__ == "__main__":
   create_recent_periods_table()