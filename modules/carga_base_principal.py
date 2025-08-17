import pandas as pd
import logging
import os
import argparse
from pathlib import Path
from dotenv import load_dotenv
from typing import Optional
from utils.other_functions import quita_nulos, verificar_tipos, df_from_mdb
from utils.db_functions import insert_info, list_ultimos_periodos
from .common import validate_period, periodo_to_filename, find_file_in_directory, get_mdb_files_directory, setup_logging


def load_and_transform_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Transforma DataFrame para inserción en base de datos.

    Args:
        df (pd.DataFrame): DataFrame original con datos crudos del archivo MDB

    Returns:
        pd.DataFrame: DataFrame transformado con tipos de datos y formatos corregidos
       
    Raises:
        ValueError: Si los tipos de datos no coinciden con lo esperado
    """
    data = df.copy()
    drop_columns = {'razon_social', 'desc_subramo', 'desc_cuenta', 'nivel', 'id_padre'}
    
    # Eliminar columnas si existen
    existing_columns = set(data.columns) & drop_columns
    if existing_columns:
        data.drop(columns=list(existing_columns), inplace=True)
    
    data['periodo'] = data['periodo'].apply(lambda x: int(x.replace('-', '0')))
    data['cod_subramo'] = data['cod_subramo'].map(quita_nulos)
    data['cod_cia'] = data['cod_cia'].astype(str).str.zfill(4)
    data = data[data['importe'] != 0].reset_index(drop=True)
    
    tipos_esperados = {
        'cod_cia': 'object',
        'periodo': 'int64',
        'cod_subramo': 'object',
        'importe': 'int64',
        'cod_cuenta': 'object'
    }

    if not verificar_tipos(data, tipos_esperados):
        raise ValueError("Error en los tipos de datos luego de transformar")
       
    return data

def main(periodo: int) -> None:
    """
    Función principal que procesa un archivo MDB del balance de compañías aseguradoras
    y lo carga en la base de datos SQLite.

    Args:
        periodo (int): Período a procesar en formato YYYYPP (ej: 202503)
    """
    validate_period(periodo)
    load_dotenv()
    database_path = os.getenv('DATABASE')
    directorio = get_mdb_files_directory()
    
    # Verificar si el período ya existe
    if periodo in list_ultimos_periodos(database_path):
        logging.info(f'El período {periodo} ya existe en la base de datos')
        return

    # Convertir período al nombre de archivo y buscar
    try:
        filename = periodo_to_filename(periodo)
        archivo_path = find_file_in_directory(directorio, filename)
        logging.info(f'Archivo encontrado: {archivo_path}')
    except (ValueError, FileNotFoundError) as e:
        logging.error(f'Error: {e}')
        return

    # Procesar archivo
    logging.info(f'Iniciando carga del período {periodo}')
    
    try:
        df = df_from_mdb(str(directorio), filename, "Balance")
        df_transformed = load_and_transform_data(df)
        
        insert_info(
            data=df_transformed, 
            database_path=database_path, 
            table='datos_balance'
        )
        
        logging.info(f"Insertadas {len(df_transformed):,} filas del período {periodo}")
        
    except Exception as e:
        logging.error(f"Error procesando el archivo: {e}")
        raise

if __name__ == "__main__":
    setup_logging()
    
    parser = argparse.ArgumentParser(
        description='Carga datos de balance en la base de datos',
        epilog="""
Ejemplos:
  python modules/carga_base_principal.py 202501    # Busca archivo 2025-1.zip
  python modules/carga_base_principal.py 202503    # Busca archivo 2025-3.zip
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        'periodo', 
        type=int, 
        help='Período a procesar en formato YYYYPP (ej: 202503 para 2025 3er trimestre)'
    )
    
    args = parser.parse_args()
    
    main(args.periodo)