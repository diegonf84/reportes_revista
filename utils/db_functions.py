import sqlite3
import pandas as pd

def insert_info(data:pd.DataFrame, database_path:str, table:str):
    """_summary_

    Args:
        data (pd.DataFrame): DataFrame para insertar
        database_path (str): Nombre de la base de datos
        table (str): Nombre de la tabla
    """
    conn = sqlite3.connect(database_path)
    data.to_sql(table, conn, if_exists='append', index=False)
    conn.close()