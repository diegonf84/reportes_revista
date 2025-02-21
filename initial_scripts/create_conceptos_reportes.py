import pandas as pd
import sqlite3
import os
from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
   load_dotenv()
   database_path = os.getenv('DATABASE')
   
   conn = sqlite3.connect(database_path)
   conn.execute("DROP TABLE IF EXISTS conceptos_reportes")
   # Crear tabla con id autoincremental
   conn.execute('''
   CREATE TABLE IF NOT EXISTS conceptos_reportes (
       id INTEGER PRIMARY KEY AUTOINCREMENT,
       reporte TEXT NOT NULL,
       referencia TEXT NOT NULL, 
       concepto TEXT NOT NULL,
       es_subramo BOOLEAN NOT NULL
   )
   ''')
   
   df = pd.DataFrame({
       'reporte': ['anexo12-am', 'anexo12-am', 'anexo12-bm', 'anexo13-b', 'anexo14-b'],
       'referencia': ['ref1', 'ref2', 'ref6', 'ref7', 'ref2'],
       'concepto': ['primas_emitidas', 'primas_cedidas', 'primas_devengadas', 
                   'siniestros_devengados', 'gastos_devengados'],
       'es_subramo': [True] * 5
   })
   
   df.to_sql('conceptos_reportes', conn, if_exists='append', index=False)
   logging.info(f"Insertados {len(df)} registros en conceptos_reportes")
   conn.close()

if __name__ == "__main__":
   main()