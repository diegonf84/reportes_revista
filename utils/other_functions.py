import pandas as pd
import numpy as np
import os
import subprocess
import zipfile
import logging

# Configuración básica del logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def verificar_tipos(df:pd.DataFrame, tipos_esperados:dict) -> bool:
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


def quita_nulos(x:pd.Series) -> (float | pd.Series):
    """
    Remueve valores con string vacíos para reemplazarlos por Null

    Args:
        x (Seres): _description_

    Returns:
        _type_: _description_
    """
    if x == '' or x is None:
        return np.nan
    elif x is np.nan:
        return x
    else:
        return x


def df_from_mdb(directorio: str, 
                nombre_archivo_zip: str, 
                nombre_tabla: str) -> pd.DataFrame:
    """
    Función para extraer datos de una tabla específica de un archivo .mdb
    que está dentro de un archivo .zip.

    Args:
        directorio (str): Directorio donde se encuentra el archivo .zip.
        nombre_archivo_zip (str): Nombre del archivo .zip que contiene el archivo .mdb.
        nombre_tabla (str): Nombre de la tabla a extraer del archivo .mdb.
    """
    archivo_zip_path = os.path.join(directorio, nombre_archivo_zip)
    
    # Descomprimir el archivo .zip para obtener el .mdb
    with zipfile.ZipFile(archivo_zip_path, 'r') as zip_ref:
        zip_ref.extractall(directorio)
    archivo_mdb_path = os.path.join(directorio, nombre_archivo_zip.replace(".zip", ".mdb"))
    
    # Verificar si el archivo .mdb existe después de descomprimir
    if not os.path.exists(archivo_mdb_path):
        logging.error("No se encontró un archivo .mdb después de descomprimir.")
        raise FileNotFoundError("No se encontró un archivo .mdb después de descomprimir.")
    
    logging.info(f"Archivo .mdb encontrado: {archivo_mdb_path}")
    
    # Exportar la tabla a un archivo CSV
    output_csv = os.path.join(directorio, nombre_tabla + '.csv')
    with open(output_csv, 'w') as outfile:
        subprocess.call(['mdb-export', archivo_mdb_path, nombre_tabla], stdout=outfile)
    logging.info(f"Tabla {nombre_tabla} exportada a CSV con éxito.")
    
    # Leer el CSV en un DataFrame de pandas
    df = pd.read_csv(output_csv)
    
    # Eliminar el archivo CSV después de su uso
    os.remove(output_csv)
    
    return df
