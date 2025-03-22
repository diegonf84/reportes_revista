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
    output_path = '2024_4_ranking_comparativo_por_ramo.csv'  # Ajusta según necesites
    
    try:
        with sqlite3.connect(database_path) as conn:
            query = """
            with base as (
                select c.nombre_corto,r.ramo_denomincion,
                sum(primas_emitidas) as primas,
                sum(primas_emitidas_anterior) as primas_anterior
                from base_subramos_corregida_actual b
                left join datos_companias c on b.cod_cia = c.cod_cia
                left join datos_ramos_subramos r on r.cod_subramo = b.cod_subramo
                GROUP by 1,2
            )
            select ramo_denomincion, nombre_corto, primas as primas_emitidas,
            round(iif(primas_anterior=0,0,((primas/primas_anterior)-1)*100),2) as variacion, primas_anterior
            from base
            order by ramo_denomincion, nombre_corto
            """
            
            # Ejecutar query y obtener DataFrame
            df = pd.read_sql_query(query, conn)
            for col in ['primas_emitidas','primas_anterior']:
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