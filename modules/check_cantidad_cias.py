import pandas as pd
import yaml
from pathlib import Path
from utils.other_functions import df_from_mdb
from typing import Dict

def load_config(config_path: Path) -> Dict:
   """
   Carga la configuración desde un archivo YAML.

   Args:
       config_path (Path): Ruta al archivo de configuración

   Returns:
       Dict: Configuración cargada
   """
   with open(config_path, 'r', encoding='utf-8') as file:
       return yaml.safe_load(file)

def check_companies(config_path: str | Path) -> None:
   """
   Verifica la cantidad de compañías únicas en la tabla.

   Args:
       config_path (str | Path): Ruta al archivo de configuración YAML
   """
   config = load_config(Path(config_path))
   
   # Construir ruta absoluta al directorio de archivos
   base_path = Path(__file__).parent.parent
   directorio = base_path / config['directorio']
   
   df = df_from_mdb(
       directorio=str(directorio),
       nombre_archivo_zip=config['nombre_archivo_zip'],
       nombre_tabla=config['nombre_tabla']
   )
   
   num_companies = df['cod_cia'].nunique()
   print(f"La tabla {config['nombre_tabla']} tiene {num_companies:,} compañías.")

if __name__ == "__main__":
   check_companies(Path("../config_for_load.yml"))