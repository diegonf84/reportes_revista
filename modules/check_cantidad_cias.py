import pandas as pd
import logging
import os
import argparse
from pathlib import Path
from dotenv import load_dotenv
from utils.other_functions import df_from_mdb
from .common import validate_period, periodo_to_filename, find_file_in_directory, get_mdb_files_directory, setup_logging

def check_companies_count(periodo: int) -> None:
    """
    Verifica la cantidad de compañías únicas en la tabla Balance del período especificado.

    Args:
        periodo (int): Período en formato YYYYPP (ej: 202503)
    """
    validate_period(periodo)
    
    directorio = get_mdb_files_directory()
    filename = periodo_to_filename(periodo)
    
    try:
        archivo_path = find_file_in_directory(directorio, filename)
        logging.info(f'Procesando archivo: {archivo_path}')
        
        df = df_from_mdb(
            directorio=str(directorio),
            nombre_archivo_zip=filename,
            nombre_tabla="Balance"
        )
        
        num_companies = df['cod_cia'].nunique()
        print(f"El período {periodo} tiene {num_companies:,} compañías en la tabla Balance.")
        
    except Exception as e:
        logging.error(f"Error procesando período {periodo}: {e}")
        raise

if __name__ == "__main__":
    setup_logging()
    
    parser = argparse.ArgumentParser(
        description='Verifica cantidad de compañías en un período específico',
        epilog="""
Ejemplos:
  python modules/check_cantidad_cias.py 202501    # Verifica período 2025-1
  python modules/check_cantidad_cias.py 202503    # Verifica período 2025-3
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        'periodo', 
        type=int, 
        help='Período a verificar en formato YYYYPP (ej: 202503)'
    )
    
    args = parser.parse_args()
    check_companies_count(args.periodo)