import pandas as pd
import yaml
import logging
import os
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict
from utils.other_functions import quita_nulos, verificar_tipos, df_from_mdb
from utils.db_functions import insert_info, list_ultimos_periodos

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def load_config(config_path: Path) -> Dict:
   """Carga configuración desde YAML"""
   with open(config_path, 'r', encoding='utf-8') as file:
       return yaml.safe_load(file)

def load_and_transform_data(df: pd.DataFrame) -> pd.DataFrame:
   """
   Transforma DataFrame para inserción en base de datos

   Args:
       df (pd.DataFrame): DataFrame original

   Returns:
       pd.DataFrame: DataFrame transformado
       
   Raises:
       ValueError: Si los tipos de datos no coinciden con lo esperado
   """
   data = df.copy()
   drop_columns = {'razon_social', 'desc_subramo', 'desc_cuenta', 'nivel', 'id_padre'}
   data.drop(columns=drop_columns, inplace=True)
   
   data['periodo'] = data['periodo'].apply(lambda x: int(x.replace('-', '0')))
   data['cod_subramo'] = data['cod_subramo'].map(quita_nulos)
   data['cod_cia'] = data['cod_cia'].astype(str).str.zfill(4)
   data = data[data['importe'] != 0].reset_index(drop=True)
   
   tipos_esperados = {
       'cod_cia': 'object',
       'periodo': 'int64',
       'cod_subramo': 'object',
       'importe': 'int64',
       'cod_cuenta': 'object'
   }

   if not verificar_tipos(data, tipos_esperados):
       raise ValueError("Error en los tipos de datos luego de transformar")
       
   return data

def main():
   load_dotenv()
   database_path = os.getenv('DATABASE')
   base_path = Path(__file__).parent.parent
   config = load_config(base_path / "config_for_load.yml")
   
   directorio = base_path / config['directorio']
   nombre_archivo = Path(config['nombre_archivo_zip']).stem
   periodo_a_ingresar = int(nombre_archivo.replace("-", "0"))
   
   if periodo_a_ingresar in list_ultimos_periodos(database_path):
       logging.info(f'El período {periodo_a_ingresar} ya existe en la base')
       return

   logging.info(f'Iniciando carga del periodo {periodo_a_ingresar}')
   df = df_from_mdb(str(directorio), config['nombre_archivo_zip'], config['nombre_tabla'])
   df_transformed = load_and_transform_data(df)
   
   insert_info(
       data=df_transformed, 
       database_path=database_path, 
       table='datos_balance'
   )
   
   logging.info(f"Insertadas {len(df_transformed)} filas del archivo {config['nombre_archivo_zip']}")

if __name__ == "__main__":
   main()