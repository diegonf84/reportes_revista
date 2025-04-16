import pandas as pd
import os
from pathlib import Path
from dotenv import load_dotenv
import sqlite3
import logging
from typing import Dict, Optional, List, Union, Any

def configure_logging() -> None:
    """Configura el sistema de logging con formato estándar."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

def export_query_to_csv(
    query: str, 
    output_path: str, 
    int_columns: Optional[List[str]] = None,
    separator: str = ';',
    decimal: str = ',',
    database_path: Optional[str] = None
) -> None:
    """
    Ejecuta una consulta SQL y exporta los resultados a un archivo CSV.
    
    Args:
        query: Consulta SQL a ejecutar
        output_path: Ruta del archivo CSV de salida
        int_columns: Lista de columnas a convertir a enteros
        separator: Separador para el CSV
        decimal: Marcador decimal para el CSV
        database_path: Ruta a la base de datos (opcional)
    """
    if not database_path:
        load_dotenv()
        database_path = os.getenv('DATABASE')
    
    try:
        with sqlite3.connect(database_path) as conn:
            # Ejecutar query y obtener DataFrame
            df = pd.read_sql_query(query, conn)
            
            # Convertir columnas a entero si se especifica
            if int_columns:
                for col in int_columns:
                    if col in df.columns:
                        df[col] = df[col].astype(int)
            
            # Exportar a CSV
            df.to_csv(output_path, sep=separator, decimal=decimal, index=False)
            
            logging.info(f"Archivo CSV creado con {len(df):,} registros en {output_path}")
            
    except sqlite3.Error as e:
        logging.error(f"Error en base de datos: {e}")
    except Exception as e:
        logging.error(f"Error inesperado: {e}")

def create_table_from_query(
    table_name: str, 
    query: str, 
    database_path: Optional[str] = None
) -> None:
    """
    Crea una tabla en la base de datos a partir de una consulta SQL.
    
    Args:
        table_name: Nombre de la tabla a crear
        query: Consulta SQL para crear la tabla
        database_path: Ruta de la base de datos (opcional)
    """
    if not database_path:
        load_dotenv()
        database_path = os.getenv('DATABASE')
    
    try:
        with sqlite3.connect(database_path) as conn:
            conn.execute(f"DROP TABLE IF EXISTS {table_name}")
            conn.execute(f"CREATE TABLE {table_name} AS {query}")
            
            count = pd.read_sql_query(f"SELECT COUNT(*) as count FROM {table_name}", conn)
            logging.info(f"Tabla {table_name} creada con {count['count'].iloc[0]:,} registros")
            
    except sqlite3.Error as e:
        logging.error(f"Error en base de datos: {e}")
    except Exception as e:
        logging.error(f"Error inesperado: {e}")

def generate_standard_report(
    report_name: str,
    query: str,
    int_columns: Optional[List[str]] = None,
    separator: str = ';',
    decimal: str = ',',
    output_dir: str = '.'
) -> str:
    """
    Genera un reporte estándar ejecutando una consulta y guardando en CSV.
    
    Args:
        report_name: Nombre base del reporte (sin extensión)
        query: Consulta SQL para generar el reporte
        int_columns: Columnas a convertir a enteros
        separator: Separador para el CSV
        decimal: Marcador decimal para el CSV
        output_dir: Directorio donde guardar el archivo
        
    Returns:
        Ruta completa al archivo CSV generado
    """
    configure_logging()
    
    # Determinar año y trimestre actuales si no están en el nombre
    if not any(str(i) in report_name for i in range(2020, 2030)):
        import datetime
        current_year = datetime.datetime.now().year
        current_month = datetime.datetime.now().month
        current_quarter = (current_month - 1) // 3 + 1
        report_name = f"{current_year}_{current_quarter}_{report_name}"
    
    # Asegurar que tenga extensión .csv
    if not report_name.endswith('.csv'):
        report_name += '.csv'
    
    output_path = os.path.join(output_dir, report_name)
    
    export_query_to_csv(
        query=query,
        output_path=output_path,
        int_columns=int_columns,
        separator=separator,
        decimal=decimal
    )
    
    return output_path