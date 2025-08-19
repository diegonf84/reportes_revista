import pandas as pd
import sqlite3
import logging
import os
import argparse
from pathlib import Path
from dotenv import load_dotenv
from utils.other_functions import df_from_mdb
from modules.common import validate_period, periodo_to_filename, find_file_in_directory, get_mdb_files_directory, setup_logging, format_number


def list_available_periods() -> list[int]:
    """
    Lista todos los períodos disponibles en la base de datos ordenados del más reciente al más antiguo.
    
    Returns:
        list[int]: Lista de períodos disponibles
    """
    load_dotenv()
    database_path = os.getenv('DATABASE')
    
    if not database_path:
        raise ValueError("DATABASE environment variable not set")
    
    query = """
    SELECT DISTINCT periodo 
    FROM datos_balance 
    ORDER BY periodo DESC
    """
    
    with sqlite3.connect(database_path) as conn:
        df = pd.read_sql_query(query, conn)
    
    return df['periodo'].tolist()

def print_periods_info():
    """
    Imprime información detallada de los períodos disponibles.
    """
    try:
        periods = list_available_periods()
        
        if not periods:
            print("No hay períodos disponibles en la base de datos.")
            return
        
        print("Períodos disponibles en la base de datos:")
        
        # Obtener información detallada de cada período
        load_dotenv()
        database_path = os.getenv('DATABASE')
        
        with sqlite3.connect(database_path) as conn:
            for periodo in periods:
                # Contar registros por período
                count_query = "SELECT COUNT(*) as registros FROM datos_balance WHERE periodo = ?"
                count_result = pd.read_sql_query(count_query, conn, params=[periodo])
                registros = count_result['registros'].iloc[0]
                
                # Contar compañías únicas por período
                companies_query = "SELECT COUNT(DISTINCT cod_cia) as companias FROM datos_balance WHERE periodo = ?"
                companies_result = pd.read_sql_query(companies_query, conn, params=[periodo])
                companias = companies_result['companias'].iloc[0]
                
                # Formatear período para mostrar
                periodo_str = str(periodo)
                año = periodo_str[:4]
                trimestre = int(periodo_str[4:])
                trimestre_nombres = {1: "Marzo", 2: "Junio", 3: "Septiembre", 4: "Diciembre"}
                trimestre_nombre = trimestre_nombres.get(trimestre, f"T{trimestre}")
                
                print(f"- {periodo} ({trimestre_nombre} {año}): {format_number(registros)} registros, {companias} compañías")
                
    except Exception as e:
        logging.error(f"Error al listar períodos: {e}")
        raise

def main():
    """
    Función principal que lista los períodos disponibles.
    """
    setup_logging()
    print_periods_info()

def get_companies_from_file_legacy(periodo_archivo: int) -> tuple[set, dict]:
    """
    FUNCIÓN LEGACY - NO USAR. Mantener solo para compatibilidad.
    Usar check_cantidad_cias.py en su lugar.
    """
    validate_period(periodo_archivo)
    directorio = get_mdb_files_directory()
    
    filename = periodo_to_filename(periodo_archivo)
    archivo_path = find_file_in_directory(directorio, filename)
    
    logging.info(f'Leyendo archivo: {archivo_path}')
    df = df_from_mdb(str(directorio), filename, "Balance")
    
    # Normalizar códigos y obtener nombres únicos por compañía
    df['cod_cia_norm'] = df['cod_cia'].astype(str).str.zfill(4)
    companies_with_names = df[['cod_cia_norm', 'razon_social']].drop_duplicates()
    
    companies_file = set(companies_with_names['cod_cia_norm'].unique())
    names_dict = dict(zip(companies_with_names['cod_cia_norm'], companies_with_names['razon_social']))
    
    logging.info(f"Compañías en archivo {filename}: {len(companies_file)}")
    return companies_file, names_dict

if __name__ == "__main__":
    main()