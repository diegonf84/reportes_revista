import pandas as pd
import numpy as np
import datetime
import os
from dotenv import load_dotenv
from utils.other_functions import *
import sqlite3


load_dotenv()

database_path=os.getenv('DATABASE')

tipos_esperados = {
        'cod_cia': 'object',
        'periodo': 'int64',
        'cod_subramo': 'object',
        'importe': 'int64',
        'cod_cuenta': 'object'
    }

def main():
    # Create your connection.
    conn = sqlite3.connect(database_path)

    data = pd.read_sql_query("SELECT * FROM base", conn)
    data.columns = [x.lower() for x in data.columns]
    data['periodo'] = data['periodo'].apply(lambda x: int(x.replace('-','0')))
    data['cod_subramo'] = data['cod_subramo'].map(lambda x: quita_nulos(x))

    # SQL para crear la tabla
    create_table_sql = '''
    CREATE TABLE IF NOT EXISTS datos_balance (
        cod_cia TEXT NOT NULL,
        periodo INTEGER NOT NULL,
        cod_cuenta TEXT NOT NULL,
        cod_subramo TEXT,
        importe INTEGER
    );
    '''

    # Ejecutar el comando para crear la tabla
    conn.execute(create_table_sql)
    # Confirmar (commit) la transacción y cerrar la conexión
    conn.commit()

    if verificar_tipos(data, tipos_esperados):
        data.to_sql('datos_balance', conn, if_exists='append', index=False)
    else:
        raise ValueError("Error en los datos luego de transformar")
    
    conn.close()

if __name__ == "__main__":
    main()