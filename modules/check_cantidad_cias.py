import pandas as pd
import sqlite3
import logging
import os
import argparse
from pathlib import Path
from dotenv import load_dotenv
from utils.other_functions import df_from_mdb
from modules.common import validate_period, periodo_to_filename, find_file_in_directory, get_mdb_files_directory, setup_logging

def get_companies_from_file(periodo_archivo: int) -> tuple[set, dict]:
    """
    Obtiene códigos de compañías y nombres del archivo MDB.
    
    Args:
        periodo_archivo (int): Período del archivo a procesar
        
    Returns:
        tuple: (conjunto de códigos, diccionario {codigo: razon_social})
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

def get_companies_from_db(periodo_anterior: int) -> tuple[set, dict]:
    """
    Obtiene códigos de compañías y nombres de la base de datos para un período específico.
    
    Args:
        periodo_anterior (int): Período a consultar en la base de datos
        
    Returns:
        tuple: (conjunto de códigos, diccionario {codigo: nombre_corto})
    """
    validate_period(periodo_anterior)
    load_dotenv()
    database_path = os.getenv('DATABASE')
    
    query = """
    SELECT DISTINCT d.cod_cia, c.nombre_corto
    FROM datos_balance d
    LEFT JOIN datos_companias c ON CAST(d.cod_cia AS INTEGER) = c.cod_cia
    WHERE d.periodo = ?
    """
    
    with sqlite3.connect(database_path) as conn:
        df = pd.read_sql_query(query, conn, params=[periodo_anterior])
    
    if df.empty:
        logging.warning(f"No se encontraron datos para el período {periodo_anterior} en la base de datos")
        return set(), {}
    
    companies_db = set(df['cod_cia'].unique())
    names_dict = {}
    for _, row in df.iterrows():
        if pd.notna(row['nombre_corto']):
            names_dict[row['cod_cia']] = row['nombre_corto']
        else:
            names_dict[row['cod_cia']] = f"Sin nombre (código {row['cod_cia']})"
    
    logging.info(f"Compañías en BD período {periodo_anterior}: {len(companies_db)}")
    return companies_db, names_dict

def compare_companies(companies_file: set, companies_db: set, names_file: dict, names_db: dict, periodo_archivo: int, periodo_anterior: int) -> None:
    """
    Compara las compañías del archivo vs base de datos y reporta diferencias con nombres.
    """
    missing_companies = companies_db - companies_file
    new_companies = companies_file - companies_db
    
    print("\n" + "="*60)
    print(f"COMPARACIÓN DE COMPAÑÍAS")
    print(f"Archivo (período {periodo_archivo}): {len(companies_file)} compañías")
    print(f"Base de datos (período {periodo_anterior}): {len(companies_db)} compañías")
    print("="*60)
    
    if missing_companies:
        print(f"\n⚠️  COMPAÑÍAS FALTANTES EN ARCHIVO ({len(missing_companies)}):")
        for company in sorted(missing_companies):
            name = names_db.get(company, "Sin nombre")
            print(f"  - {company}: {name}")
        print(f"\n❌ ATENCIÓN: Faltan {len(missing_companies)} compañías del período anterior")
        print("   Revisa el archivo antes de proceder con la carga.")
    else:
        print("\n✅ Todas las compañías del período anterior están presentes")
    
    if new_companies:
        print(f"\n📋 COMPAÑÍAS NUEVAS EN ARCHIVO ({len(new_companies)}):")
        for company in sorted(new_companies):
            name = names_file.get(company, "Sin nombre")
            print(f"  - {company}: {name}")
    
    if not missing_companies and not new_companies:
        print("\n✅ Las compañías coinciden exactamente entre períodos")

def check_companies_count(periodo: int) -> None:
    """
    Verifica la cantidad de compañías únicas en la tabla Balance del período especificado.

    Args:
        periodo (int): Período en formato YYYYPP (ej: 202503)
    """
    companies_file, _ = get_companies_from_file(periodo)
    print(f"El período {periodo} tiene {len(companies_file):,} compañías en la tabla Balance.")

def main(periodo_archivo: int, periodo_anterior: int = None) -> None:
    """
    Función principal que valida compañías entre archivo MDB y base de datos.
    
    Args:
        periodo_archivo (int): Período del archivo MDB a validar
        periodo_anterior (int, optional): Período anterior en la base de datos para comparar
    """
    try:
        if periodo_anterior is None:
            # Solo verificar cantidad de compañías
            check_companies_count(periodo_archivo)
        else:
            # Comparar con período anterior
            companies_file, names_file = get_companies_from_file(periodo_archivo)
            companies_db, names_db = get_companies_from_db(periodo_anterior)
            
            compare_companies(companies_file, companies_db, names_file, names_db, periodo_archivo, periodo_anterior)
        
    except Exception as e:
        logging.error(f"Error en la validación: {e}")
        raise

if __name__ == "__main__":
    setup_logging()
    
    parser = argparse.ArgumentParser(
        description='Valida compañías entre archivo MDB y base de datos',
        epilog="""
Ejemplos:
  python modules/check_cantidad_cias.py 202502                # Solo verificar cantidad
  python modules/check_cantidad_cias.py 202502 202501         # Comparar con período anterior
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        'periodo_archivo', 
        type=int, 
        help='Período del archivo MDB a validar (formato YYYYPP)'
    )
    
    parser.add_argument(
        'periodo_anterior', 
        type=int,
        nargs='?',
        help='Período anterior en la base de datos para comparar (formato YYYYPP, opcional)'
    )
    
    args = parser.parse_args()
    
    main(args.periodo_archivo, args.periodo_anterior)