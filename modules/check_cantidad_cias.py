import pandas as pd
import yaml
from utils.other_functions import df_from_mdb

def main(config_path: str):
    # Leer el archivo de configuración YAML
    with open(config_path, 'r') as file:
        config = yaml.safe_load(file)
    
    # Extraer los valores del archivo YAML
    directorio = config['directorio']
    nombre_archivo_zip = config['nombre_archivo_zip']
    nombre_tabla = config['nombre_tabla']
    
    # Llamar a la función db_from_mdb con los valores del archivo YAML
    df = df_from_mdb(directorio, nombre_archivo_zip, nombre_tabla)
    
    # Realiza tus chequeos en el DataFrame `df`
    print(f"La tabla {nombre_tabla} tiene {df['cod_cia'].nunique()} compañias.")

if __name__ == "__main__":
    # Llamar a main con la ruta al archivo de configuración YAML como argumento
    main("../config/config_mdb.yml")