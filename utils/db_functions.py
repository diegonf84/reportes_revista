import sqlite3
import pandas as pd
import datetime

def insert_info(data:pd.DataFrame, database_path:str, table:str):
    """
    Función para insertar datos en una tabla existente de SQLite

    Args:
        data (pd.DataFrame): DataFrame para insertar
        database_path (str): Nombre de la base de datos
        table (str): Nombre de la tabla
    """
    conn = sqlite3.connect(database_path)
    data.to_sql(table, conn, if_exists='append', index=False)
    conn.close()


def load_dataframe(data: pd.DataFrame, database_path:str, table:str):
    """
    Carga un DataFrame en una tabla de SQLite, creando una nueva tabla o reemplazando la existente.

    Parámetros:
    data (pd.DataFrame): DataFrame a cargar en la base de datos.
    table (str): Nombre de la tabla en la base de datos.
    database_path (str): Ruta de la base de datos SQLite.
    """
    try:
        # Conexión a la base de datos SQLite
        conn = sqlite3.connect(database_path)
        
        try:
            # Eliminar la tabla si existe
            conn.execute(f'DROP TABLE IF EXISTS {table}')

            # Crear una nueva tabla a partir del DataFrame
            data.to_sql(table, conn, index=False)

        except sqlite3.Error as e:
            print(f"Error al trabajar con la base de datos: {e}")

        finally:
            # Cerrar la conexión
            conn.close()

    except sqlite3.Error as e:
        print(f"Error al conectarse a la base de datos: {e}")


def list_ultimos_periodos(database_path:str):
    """
    Obtiene una lista de los valores únicos de la columna 'periodo' para los registros de los últimos 2 años.
    
    Args:
        database_path (str): Ruta al archivo de la base de datos SQLite.
    
    Returns:
        list: Lista de los valores únicos de 'periodo' que cumplen con el criterio.
    """
    
    anio_actual = datetime.datetime.now().year
    periodo_inicial = int(f"{anio_actual - 2}00")
    
    try:
       # Conexión a la base de datos SQLite
        conn = sqlite3.connect(database_path)

        # Query
        query = f"SELECT DISTINCT periodo FROM datos_balance WHERE periodo > {periodo_inicial}"
        df = pd.read_sql_query(query, conn)

        # Convertimos la columna 'periodo' del DataFrame en una lista y la retornamos
        periodos_unicos = df['periodo'].tolist()
    
    except sqlite3.Error as e:
            print(f"Error al conectarse a la base de datos: {e}")
    
    finally:
            # Cerrar la conexión
            conn.close()
    
    return periodos_unicos
