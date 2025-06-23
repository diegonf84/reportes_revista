import pandas as pd
import os
from pathlib import Path
from dotenv import load_dotenv
import sqlite3
import logging
import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def create_table_from_query() -> None:
    """Crea nueva tabla a partir de resultados de una query"""
    load_dotenv()
    database_path = os.getenv('DATABASE')
    
    try:
        with sqlite3.connect(database_path) as conn:
            # Primero eliminamos la tabla si existe
            conn.execute("DROP TABLE IF EXISTS base_subramos_corregida_actual")
            
            # Query para crear la nueva tabla con los resultados
            query = """
            CREATE TABLE base_subramos_corregida_actual AS
            with primas_diferentes_marzo_actual as (
                select cod_cia, cod_subramo,
                sum(primas_emitidas) as primas_emit_mar_actual
                from base_subramos
                where periodo in ('202501')
                and cod_cia in ('0829','0541','0686')
                GROUP by cod_cia, cod_subramo
            ),
            primas_diferentes_junio_actual as (
                select cod_cia, cod_subramo,
                sum(primas_emitidas) as primas_emit_jun_actual
                from base_subramos
                where periodo in ('202402')
                and cod_cia in ('0829','0541','0686')
                GROUP by cod_cia, cod_subramo
            ),
            primas_diferentes_diciembre_actual as (
                select cod_cia, cod_subramo,
                sum(primas_emitidas) as primas_emit_dic_actual
                from base_subramos
                where periodo in ('202404')
                and cod_cia in ('0829','0541','0686')
                GROUP by cod_cia, cod_subramo
            ),
            primas_diferentes_marzo_anterior as (
                select cod_cia, cod_subramo,
                sum(primas_emitidas) as primas_emit_mar_anterior
                from base_subramos
                where periodo in ('202401')
                and cod_cia in ('0829','0541','0686')
                GROUP by cod_cia, cod_subramo
            ),
            primas_diferentes_junio_anterior as (
                select cod_cia, cod_subramo,
                sum(primas_emitidas) as primas_emit_jun_anterior
                from base_subramos
                where periodo in ('202302')
                and cod_cia in ('0829','0541','0686')
                GROUP by cod_cia, cod_subramo
            ),
            primas_diferentes_diciembre_anterior as (
                select cod_cia, cod_subramo,
                sum(primas_emitidas) as primas_emit_dic_anterior
                from base_subramos
                where periodo in ('202304')
                and cod_cia in ('0829','0541','0686')
                GROUP by cod_cia, cod_subramo
            ),
            base_cias_diferentes as (
                select a.cod_cia, a.cod_subramo, 
                a.primas_emit_mar_actual - b.primas_emit_jun_actual + c.primas_emit_dic_actual as primas_emit_actual, 
                d.primas_emit_mar_anterior - e.primas_emit_jun_anterior + f.primas_emit_dic_anterior as primas_emit_anterior
                from primas_diferentes_marzo_actual a
                join primas_diferentes_junio_actual b on a.cod_cia = b.cod_cia and a.cod_subramo = b.cod_subramo
                join primas_diferentes_diciembre_actual c on a.cod_cia = c.cod_cia and a.cod_subramo = c.cod_subramo
                join primas_diferentes_marzo_anterior d on a.cod_cia = d.cod_cia and a.cod_subramo = d.cod_subramo
                join primas_diferentes_junio_anterior e on a.cod_cia = e.cod_cia and a.cod_subramo = e.cod_subramo
                join primas_diferentes_diciembre_anterior f on a.cod_cia = f.cod_cia and a.cod_subramo = f.cod_subramo
            ) ,
            primas_actuales_resto as (
                select cod_cia, cod_subramo,
                sum(primas_emitidas) as primas_emit_actual
                from base_subramos
                where periodo in ('202501')
                and cod_cia not in ('0829','0541','0686')
                GROUP by cod_cia,cod_subramo
            ),
            primas_anteriores_resto as (
                select cod_cia, cod_subramo,
                sum(primas_emitidas) as primas_emit_anterior
                from base_subramos
                where periodo in ('202401')
                and cod_cia not in ('0829','0541','0686')
                GROUP by cod_cia,cod_subramo
            ),
            base_cias_comunes as (
                select a.cod_cia, a.cod_subramo, a.primas_emit_actual as primas_emitidas, 
                iif(b.primas_emit_anterior is null, 0, b.primas_emit_anterior) as primas_emitidas_anterior
                from primas_actuales_resto a
                left join primas_anteriores_resto b on a.cod_cia = b.cod_cia and a.cod_subramo = b.cod_subramo
            ),
            base_final as (
                select *
                from base_cias_comunes
                union all
                select *
                from base_cias_diferentes
            )
            select * from base_final
            where primas_emitidas <>0    
            """
            
            conn.execute(query)
            
            # Verificar cantidad de registros
            count = pd.read_sql_query("SELECT COUNT(*) as count FROM base_subramos_corregida_actual", conn)
            logging.info(f"Tabla creada con {count['count'].iloc[0]:,} registros")
            
    except sqlite3.Error as e:
        logging.error(f"Error en base de datos: {e}")
    except Exception as e:
        logging.error(f"Error inesperado: {e}")

if __name__ == "__main__":
    create_table_from_query()