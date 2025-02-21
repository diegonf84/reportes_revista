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
    output_path = '2024_4_cuadro_principal_suma.csv'  # Ajusta según necesites
    
    try:
        with sqlite3.connect(database_path) as conn:
            query = """
            with datos_base as (
                select cod_cia, cod_subramo,
                sum(primas_devengadas) as primas_deveng,
                sum(primas_emitidas) as primas_emit,
                sum(siniestros_devengados) as stros_deveng,
                sum(gastos_totales_devengados) as gastos
                from base_subramos
                where periodo = '202404'
                GROUP by cod_cia,cod_subramo
            ),
            datos_ramo as (
                select r.ramo_denomincion,
                sum(b.primas_deveng) as primas_devengadas,
                sum(b.primas_emit) as primas_emitidas,
                sum(b.stros_deveng) as siniestros, 
                sum(b.gastos) as gastos
                from datos_base b 
                left join datos_companias c on b.cod_cia = c.cod_cia
                left join datos_ramos_subramos r on r.cod_subramo = b.cod_subramo
                where b.cod_subramo not in ('2.070.01','2.070.02','2.060.01','2.060.02','3.000.99')
                GROUP by r.ramo_denomincion
                HAVING primas_emitidas <>0
            )
            select ramo_denomincion, primas_emitidas, primas_devengadas, 
            round(siniestros/primas_devengadas*100,2) as pct_stros,
            round(gastos/primas_devengadas*100,2) as pct_gastos,
            (primas_devengadas - siniestros - gastos) as resultado,
            round((primas_devengadas - siniestros - gastos)/primas_devengadas*100,2) as pct_result,
            siniestros,gastos
            from datos_ramo
            order by ramo_denomincion asc, primas_emitidas desc
            """
            
            # Ejecutar query y obtener DataFrame
            df = pd.read_sql_query(query, conn)
            for col in ['primas_emitidas','primas_devengadas','resultado']:
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