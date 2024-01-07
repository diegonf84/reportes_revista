import pandas as pd
import numpy as np

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