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
    output_path = '2024_4_apertura_por_subramo.csv'  # Ajusta según necesites
    
    try:
        with sqlite3.connect(database_path) as conn:
            query = """
            WITH base AS (
                SELECT 
                    c.nombre_corto,
                    r.subramo_denominacion,
                    SUM(b.primas_emitidas) as primas
                FROM base_subramos_corregida_actual b
                LEFT JOIN datos_companias c ON b.cod_cia = c.cod_cia
                LEFT JOIN datos_ramos_subramos r ON r.cod_subramo = b.cod_subramo
                GROUP BY 1, 2
            ),
            totales_subramo AS (
                SELECT 
                    subramo_denominacion,
                    SUM(primas) as total_subramo
                FROM base
                GROUP BY subramo_denominacion
            ),
            porcentajes AS (
                SELECT 
                t1.subramo_denominacion,
                t1.nombre_corto,
                t1.primas,
                (t1.primas * 100.0 / t2.total_subramo) as porcentaje,
                SUM(t1.primas * 100.0 / t2.total_subramo) 
                    OVER (PARTITION BY t1.subramo_denominacion ORDER BY t1.primas DESC) as porcentaje_acumulado
            FROM base t1
            JOIN totales_subramo t2 ON t1.subramo_denominacion = t2.subramo_denominacion
            )
            SELECT *
            FROM porcentajes
            ORDER BY subramo_denominacion, primas DESC
            """
            
            # Ejecutar query y obtener DataFrame
            df = pd.read_sql_query(query, conn)
            for col in ['primas']:
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