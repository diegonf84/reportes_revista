import pandas as pd
import numpy as np
import sqlite3
import logging

# Configuración básica del logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


database_path = 'revista_tr_database.db'
conn = sqlite3.connect(database_path)
table = 'datos_balance'


def quita_nulos(x):
    if x == '' or x is None:
        return np.nan
    elif x is np.nan:
        return x
    else:
        return x


def verificar_tipos(df, tipos_esperados):
    """
    Verifica si los tipos de datos de las columnas en un DataFrame coinciden con los esperados.

    Parámetros:
    df (pandas.DataFrame): El DataFrame a verificar.
    tipos_esperados (dict): Un diccionario con los nombres de las columnas como claves y los tipos de datos esperados como valores.

    Retorna:
    bool: True si todos los tipos de datos son los esperados, False en caso contrario.
    """
    tipos_actuales = df.dtypes
    return all(tipos_actuales[col] == tipo for col, tipo in tipos_esperados.items())


def load_and_transform_file(filepath):
    """_summary_

    Args:
        filepath (_type_): Ruta del archivo a leer
    Retorna:
    df: Dataframe ya transformado listo para subir.
    """
    data = pd.read_csv(filepath, sep=';', encoding='latin-1',
                       dtype={'cod_cia': 'object'})
    data.drop(columns={'razon_social', 'desc_subramo', 'desc_cuenta',
                       'nivel', 'id_padre'}, inplace=True)
    data['periodo'] = data['periodo'].apply(lambda x: int(x.replace('-', '0')))
    data['importe'] = data['importe'].map(lambda x: int(float(x.replace(',', '.'))))
    data['cod_subramo'] = data['cod_subramo'].map(lambda x: quita_nulos(x))
    data = data[data['importe'] != 0]
    data.reset_index(inplace=True, drop=True)

    tipos_esperados = {
        'cod_cia': 'object',
        'periodo': 'int64',
        'cod_subramo': 'object',
        'importe': 'int64',
        'cod_cuenta': 'object'
    }

    if verificar_tipos(data, tipos_esperados):
        return data
    else:
        raise ValueError("Error en los datos luego de transformar")

    return data


def insert_info(data, conn):
    """_summary_

    Args:
        df (_type_): _description_
        conn (_type_): _description_
    """
    data.to_sql(table, conn, if_exists='append', index=False)
    conn.close()


def procesar_archivo(file):
    df = load_and_transform_file(file)
    insert_info(df, conn)
    filas, columnas = df.shape
    logging.info(f"Se insertaron {filas} filas, para el archivo {file}")
