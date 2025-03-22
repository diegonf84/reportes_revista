import pandas as pd
import os
from pathlib import Path
from dotenv import load_dotenv
import sqlite3
import logging
import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def export_query_to_csv() -> None:
    """Ejecuta query y exporta resultados a CSV"""
    load_dotenv()
    database_path = os.getenv('DATABASE')
    output_path = '2024_4_primas_cedidas_reaseguro.csv'  # Ajusta según necesites
    
    try:
        with sqlite3.connect(database_path) as conn:
            query = """
            with base as (
                select cod_cia,
                sum(primas_emitidas) as primas_emit,
                sum(primas_cedidas) as primas_ced
                from base_subramos
                where periodo = '202404'
                GROUP by cod_cia
            )
            select c.tipo_cia, c.nombre_corto,
			b.primas_emit as primas_emitidas,
			b.primas_ced as primas_cedidas,
			round(iif(b.primas_emit = 0,0,(b.primas_ced/b.primas_emit )*100),2) as pct_cesion,
			b.primas_emit  - b.primas_ced  as primas_retenidas,
			round(iif(b.primas_emit  - b.primas_ced = 0,0,((b.primas_emit  - b.primas_ced)/b.primas_emit )*100),2) as pct_ret
            from base b
			left join datos_companias c on b.cod_cia = c.cod_cia
			where b.primas_emit<>0
			order by tipo_cia, nombre_corto
            """
            
            # Ejecutar query y obtener DataFrame
            df = pd.read_sql_query(query, conn)
            for col in ['primas_emitidas','primas_cedidas','primas_retenidas']:
                df[col] = df[col].astype(int)
            # Exportar a CSV
            df.to_csv(output_path, sep=';', decimal=',', index=False)
            
            logging.info(f"Archivo CSV creado con {len(df):,} registros")
            
    except sqlite3.Error as e:
        logging.error(f"Error en base de datos: {e}")
    except Exception as e:
        logging.error(f"Error inesperado: {e}")

if __name__ == "__main__":
    export_query_to_csv()