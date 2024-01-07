import pandas as pd
import numpy as np
import sqlite3
import logging
import os
from dotenv import load_dotenv
from utils.db_functions import *
from utils.other_functions import *

load_dotenv()

# Configuración básica del logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

database_path=os.getenv('DATABASE')


def load_and_transform_file(filepath:str) -> pd.DataFrame:
    """
    Levanta el archivo .txt y lo transforma con las columnas necesarias para incorporarlo a la base de datos

    Args:
        filepath (str): Ruta del archivo a leer
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


def procesar_archivo(file):
    df = load_and_transform_file(file)
    #insert_info(data=df, database_path=database_path, table='datos_balance')
    filas, columnas = df.shape
    logging.info(f"Se insertaron {filas} filas, para el archivo {file}")
