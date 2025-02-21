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
   
   query = """
    SELECT * 
    FROM base_balance_ultimos_periodos 
    WHERE periodo = (
        SELECT MAX(periodo) 
        FROM base_balance_ultimos_periodos
    )
    """
   
   base = pd.read_sql_query(query, conn)
   filtro = pd.read_sql_query("SELECT * FROM conceptos_reportes WHERE es_subramo is FALSE", conn)
   params_full = pd.read_sql_query("SELECT * FROM parametros_reportes", conn)

   parametros_reportes = params_full.merge(filtro, on=['reporte','referencia'], how='inner')
   logging.info(f"Base generada con {len(base):,} registros")

   return base, parametros_reportes

def generate_subramos_table(data: pd.DataFrame, codigos: dict) -> pd.DataFrame:
   
   """Genera tabla agregada por diferentes conceptos que no tienen subramo asociado"""
   
   result = data.copy()

   for concepto, mapping in codigos.items():
       result[concepto] = result['cod_cuenta'].map(mapping) * result['importe']

   return result.groupby(
       by=['cod_cia', 'periodo'],
       as_index=False
   ).agg(
       resultado_tecnico=('resultado_tecnico', 'sum'),
       resultado_financiero=('resultado_financiero', 'sum'),
       resultado_operaciones=('resultado_operaciones', 'sum'),
       impuesto_ganancias=('impuesto_ganancias', 'sum'),
       deudas_con_asegurados=('deudas_con_asegurados', 'sum'),
       deudas_con_asegurados_ac_reaseguros=('deudas_con_asegurados_ac_reaseguros', 'sum'),
       disponibilidades=('disponibilidades', 'sum'),
       inmuebles_inversion=('inmuebles_inversion', 'sum'),
       inmuebles_uso_propio=('inmuebles_uso_propio', 'sum'),
       inversiones=('inversiones', 'sum'),
       patrimonio_neto=('patrimonio_neto', 'sum'),
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
           conn.execute("DROP TABLE IF EXISTS base_otros_conceptos")
           result_df.to_sql('base_otros_conceptos', conn, index=False)
           
           count = pd.read_sql_query("SELECT COUNT(*) as count FROM base_otros_conceptos", conn)
           logging.info(f"Tabla base_otros_conceptos creada con {count['count'].iloc[0]:,} registros")

   except sqlite3.Error as e:
       logging.error(f"Error en base de datos: {e}")

if __name__ == "__main__":
   main()