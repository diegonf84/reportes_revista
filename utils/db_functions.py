import sqlite3
import pandas as pd
import datetime
from typing import List

def insert_info(data: pd.DataFrame, database_path: str, table: str) -> None:
    """
    Función para insertar datos en una tabla existente de SQLite

    Args:
        data (pd.DataFrame): DataFrame para insertar
        database_path (str): Nombre de la base de datos
        table (str): Nombre de la tabla
    """
    with sqlite3.connect(database_path) as conn:
        data.to_sql(table, conn, if_exists='append', index=False)

def load_dataframe(data: pd.DataFrame, database_path: str, table: str) -> None:
    """
    Carga un DataFrame en una tabla de SQLite, creando una nueva tabla o reemplazando la existente.

    Args:
        data (pd.DataFrame): DataFrame a cargar en la base de datos.
        database_path (str): Ruta de la base de datos SQLite.
        table (str): Nombre de la tabla en la base de datos.
    
    Raises:
        sqlite3.Error: Si ocurre un error al trabajar con la base de datos
    """
    try:
        with sqlite3.connect(database_path) as conn:
            conn.execute(f'DROP TABLE IF EXISTS {table}')
            data.to_sql(table, conn, index=False)
    except sqlite3.Error as e:
        print(f"Error al trabajar con la base de datos: {e}")

def list_ultimos_periodos(database_path: str) -> List[int]:
    """
    Obtiene una lista de los valores únicos de la columna 'periodo' para los registros de los últimos 2 años.
    
    Args:
        database_path (str): Ruta al archivo de la base de datos SQLite.
    
    Returns:
        List[int]: Lista de los valores únicos de 'periodo' que cumplen con el criterio.
    
    Raises:
        sqlite3.Error: Si ocurre un error al conectar con la base de datos
    """
    anio_actual = datetime.datetime.now().year
    periodo_inicial = int(f"{anio_actual - 2}00")
    
    try:
        with sqlite3.connect(database_path) as conn:
            query = f"SELECT DISTINCT periodo FROM datos_balance WHERE periodo > {periodo_inicial} ORDER BY periodo"
            df = pd.read_sql_query(query, conn)
            return df['periodo'].tolist()
    except sqlite3.Error as e:
        print(f"Error al conectarse a la base de datos: {e}")
        return []