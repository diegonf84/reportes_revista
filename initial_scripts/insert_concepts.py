import pandas as pd
import sqlite3
import os
from dotenv import load_dotenv
from typing import List, Dict
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def validate_data(df: pd.DataFrame) -> bool:
    expected_columns = {'reporte', 'referencia', 'concepto', 'es_subramo'}
    
    if not all(col in df.columns for col in expected_columns):
        raise ValueError(f"Faltan columnas. Requeridas: {expected_columns}")
    
    if not df['es_subramo'].dtype == bool:
        raise ValueError("Campo 'es_subramo' debe ser booleano")
        
    text_columns = ['reporte', 'referencia', 'concepto']
    if not all(df[col].dtype == 'object' for col in text_columns):
        raise ValueError("Los campos de texto deben ser tipo string/object")
        
    return True

def insert_conceptos(new_data: List[Dict]) -> None:
    load_dotenv()
    database_path = os.getenv('DATABASE')
    
    df = pd.DataFrame(new_data)
    validate_data(df)
    
    conn = sqlite3.connect(database_path)
    df.to_sql('conceptos_reportes', conn, if_exists='append', index=False)
    conn.close()
    
    logging.info(f"Insertados {len(df)} nuevos registros")

# Ejemplo de uso
if __name__ == "__main__":
    nuevos_registros = [
        {
            'reporte': 'ganaron-perdieron',
            'referencia': '1-rt',
            'concepto': 'resultado_tecnico',
            'es_subramo': False
        },
        {
            'reporte': 'ganaron-perdieron',
            'referencia': '2-rf',
            'concepto': 'resultado_financiero',
            'es_subramo': False
        },
        {
            'reporte': 'ganaron-perdieron',
            'referencia': '3-roe',
            'concepto': 'resultado_operaciones',
            'es_subramo': False
        },
        {
            'reporte': 'ganaron-perdieron',
            'referencia': '4-ig',
            'concepto': 'impuesto_ganancias',
            'es_subramo': False
        },
        {
            'reporte': 'nuevort',
            'referencia': 'deud',
            'concepto': 'deudas_con_asegurados',
            'es_subramo': False
        },
        {
            'reporte': 'nuevort',
            'referencia': 'deudreas',
            'concepto': 'deudas_con_asegurados_ac_reaseguros',
            'es_subramo': False
        },
        {
            'reporte': 'nuevort',
            'referencia': 'disp',
            'concepto': 'disponibilidades',
            'es_subramo': False
        },
        {
            'reporte': 'nuevort',
            'referencia': 'inm1',
            'concepto': 'inmuebles_inversion',
            'es_subramo': False
        },
        {
            'reporte': 'nuevort',
            'referencia': 'inm2',
            'concepto': 'inmuebles_uso_propio',
            'es_subramo': False
        },
        {
            'reporte': 'nuevort',
            'referencia': 'inv',
            'concepto': 'inversiones',
            'es_subramo': False
        },
        {
            'reporte': 'nuevort',
            'referencia': 'pn',
            'concepto': 'patrimonio_neto',
            'es_subramo': False
        }
    ]
    insert_conceptos(nuevos_registros)