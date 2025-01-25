import pandas as pd
import sqlite3
import logging
import os
from pathlib import Path
from dotenv import load_dotenv
import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_recent_data(conn: sqlite3.Connection) -> tuple[pd.DataFrame, pd.DataFrame]:
   """Obtiene datos necesarios de la base de datos"""
   anio_actual = datetime.datetime.now().year
   periodo_inicial = int(f"{anio_actual - 1}00")

   base = pd.read_sql_query(f"SELECT * FROM base_balance_ultimos_periodos WHERE periodo > {periodo_inicial}", conn)
   filtro = pd.read_sql_query("SELECT * FROM conceptos_reportes", conn)
   params_full = pd.read_sql_query("SELECT * FROM parametros_reportes", conn)

   parametros_reportes = params_full.merge(filtro, on=['reporte','referencia'], how='inner')
   logging.info(f"Base generada con {len(base):,} registros")

   return base, parametros_reportes

def generate_subramos_table(data: pd.DataFrame, codigos: dict) -> pd.DataFrame:
   """Genera tabla agregada por subramos"""
   result = data.copy()

   for concepto, mapping in codigos.items():
       result[concepto] = result['cod_cuenta'].map(mapping) * result['importe']

   return result.groupby(
       by=['cod_cia', 'periodo', 'cod_subramo'],
       as_index=False
   ).agg(
       primas_emitidas=('primas_emitidas', 'sum'),
       primas_devengadas=('primas_devengadas', 'sum'),
       siniestros_devengados=('siniestros_devengados', 'sum'),
       gastos_totales_devengados=('gastos_devengados', 'sum')
   )

def main():
   load_dotenv()
   database_path = os.getenv('DATABASE')

   try:
       with sqlite3.connect(database_path) as conn:
           base, parametros_reportes = get_recent_data(conn)
           
           codigos_map = {
               concepto: dict(zip(
                   parametros_reportes[parametros_reportes['concepto'] == concepto]['cod_cuenta'],
                   parametros_reportes[parametros_reportes['concepto'] == concepto]['signo']
               ))
               for concepto in parametros_reportes['concepto'].unique()
           }

           result_df = generate_subramos_table(base, codigos_map)
           
           # Crear nueva tabla
           conn.execute("DROP TABLE IF EXISTS base_subramos")
           result_df.to_sql('base_subramos', conn, index=False)
           
           count = pd.read_sql_query("SELECT COUNT(*) as count FROM base_subramos", conn)
           logging.info(f"Tabla base_subramos creada con {count['count'].iloc[0]:,} registros")

   except sqlite3.Error as e:
       logging.error(f"Error en base de datos: {e}")

if __name__ == "__main__":
   main()