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
    output_path = '2024_4_ganaron_perdieron.csv'  # Ajusta según necesites
    
    try:
        with sqlite3.connect(database_path) as conn:
            query = """
            with primas as (
                select cod_cia, sum(primas_devengadas) as primas_deveng
                from base_subramos
                where periodo = '202404'
                GROUP by cod_cia
            ),
            base_final as (
                select c.tipo_cia, c.nombre_corto,
                p.primas_deveng as primas_devengadas,	
                b.resultado_tecnico,
                b.resultado_financiero,
                b.resultado_operaciones,
                b.impuesto_ganancias
                from   base_otros_conceptos b 
                left join datos_companias c on b.cod_cia = c.cod_cia
                left join primas p on b.cod_cia = p.cod_cia
            )
            select bf.tipo_cia, bf.nombre_corto,
            bf.resultado_tecnico,
            round(bf.resultado_tecnico/bf.primas_devengadas*100,2) as pct_rt,
            bf.resultado_financiero,
            round(bf.resultado_financiero/bf.primas_devengadas*100,2) as pct_rf,
            bf.resultado_operaciones,
            bf.impuesto_ganancias,
            (bf.resultado_tecnico+bf.resultado_financiero+bf.resultado_operaciones+bf.impuesto_ganancias) as resultado,
            round((bf.resultado_tecnico+bf.resultado_financiero+bf.resultado_operaciones+bf.impuesto_ganancias)/bf.primas_devengadas*100,2) as pct_result,
            bf.primas_devengadas
            from base_final bf 
            order by tipo_cia asc, resultado desc
            """
            
            # Ejecutar query y obtener DataFrame
            df = pd.read_sql_query(query, conn)
            for col in ['resultado_tecnico','resultado_financiero','resultado_operaciones',
                        'impuesto_ganancias','resultado','primas_devengadas']:
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