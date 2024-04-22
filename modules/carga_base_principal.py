import pandas as pd
import yaml
import sqlite3
import logging
import os
from dotenv import load_dotenv
from utils.other_functions import *
from utils.db_functions import insert_info,list_ultimos_periodos

load_dotenv()

database_path=os.getenv('DATABASE')

with open("../config_for_load.yml", 'r') as file:
        config = yaml.safe_load(file)
    
# Extraer los valores del archivo YAML
directorio = config['directorio']
nombre_archivo_zip = config['nombre_archivo_zip']
nombre_tabla = config['nombre_tabla']

def load_and_transform_data(df:pd.DataFrame) -> pd.DataFrame:
    """
    Levanta el archivo .txt y lo transforma con las columnas necesarias para incorporarlo a la base de datos

    Args:
        filepath (str): Ruta del archivo a leer
    Retorna:
    df: Dataframe ya transformado listo para subir.
    """
    data = df.copy()
    data.drop(columns={'razon_social', 'desc_subramo', 'desc_cuenta',
                       'nivel', 'id_padre'}, inplace=True)
    data['periodo'] = data['periodo'].apply(lambda x: int(x.replace('-', '0')))
    data['cod_subramo'] = data['cod_subramo'].map(lambda x: quita_nulos(x))
    data['cod_cia'] = data['cod_cia'].astype(str).str.zfill(4)
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

if __name__ == "__main__":
    # Primero chequeamos que el período no esté
    periodos = list_ultimos_periodos(database_path=database_path)
    nombre_archivo = os.path.splitext(os.path.basename(nombre_archivo_zip))[0]
    periodo_a_ingresar = int(nombre_archivo.replace("-", "0"))
    
    if periodo_a_ingresar not in periodos:
        logging.info(f'Inicia carga de periodo {periodo_a_ingresar}')
        df = df_from_mdb(directorio, nombre_archivo_zip, nombre_tabla)
        df_for_database = load_and_transform_data(df=df)
        insert_info(data=df_for_database, 
                   database_path=database_path, 
                   table='datos_balance')
        filas, columnas = df_for_database.shape
        logging.info(f"Se insertaron {filas} filas, para el archivo {nombre_archivo_zip}")
    else:
         logging.info(f'El período {periodo_a_ingresar} ya se encuentra en la base')