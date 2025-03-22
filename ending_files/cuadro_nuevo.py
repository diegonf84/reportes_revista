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
    output_path = '2024_4_cuadro_nuevo.csv'  # Ajusta según necesites
    
    try:
        with sqlite3.connect(database_path) as conn:
            query = """
            with primas as (
                    select cod_cia, sum(primas_emitidas) as primas_emit
                    from base_subramos
                    where periodo = '202404'
                    GROUP by cod_cia
                    )
            select c.tipo_cia, c.nombre_corto,
            p.primas_emit as primas_emitidas,	
            b.disponibilidades,
            b.inversiones,
            b.inmuebles_inversion + b.inmuebles_uso_propio as inmuebles,
            b.deudas_con_asegurados - b.deudas_con_asegurados_ac_reaseguros as deudas_total_aseg,
            b.deudas_con_asegurados_ac_reaseguros,
            b.deudas_con_asegurados as deudas_neto,
            b.patrimonio_neto
            from base_otros_conceptos b 
            left join datos_companias c on b.cod_cia = c.cod_cia
            left join primas p on b.cod_cia = p.cod_cia
            order by tipo_cia asc, primas_emitidas desc
            """
            
            # Ejecutar query y obtener DataFrame
            df = pd.read_sql_query(query, conn)
            for col in df.iloc[:,2:].columns:
                df[col] = df[col].astype(int)
            # Exportar a CSV
            df.to_csv(output_path, sep=',', index=False)
            
            logging.info(f"Archivo CSV creado con {len(df):,} registros")
            
    except sqlite3.Error as e:
        logging.error(f"Error en base de datos: {e}")
    except Exception as e:
        logging.error(f"Error inesperado: {e}")

if __name__ == "__main__":
    export_query_to_csv()