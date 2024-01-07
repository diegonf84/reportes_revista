import pandas as pd
import numpy as np
import sqlite3
import logging

# Configuración básica del logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


database_path = 'revista_tr_database.db'
conn = sqlite3.connect(database_path)

# Obtengo base inicial
def genero_dataframes(conn):
    base = pd.read_sql_query("SELECT * FROM datos_balance WHERE periodo in (202202,202203,202204,202301)", conn)
    filtro = pd.read_sql_query("SELECT * FROM conceptos_reportes", conn)
    params_full = pd.read_sql_query("SELECT * FROM parametros_reportes", conn)

    parametros_reportes = params_full.merge(filtro, on=['reporte','referencia'], how='inner')

    return base, parametros_reportes


def genero_resultado(data,codigos):
    result = data.copy()

    for i in list(codigos.keys()):
            result[i] = result['cod_cuenta'].map(codigos[i]) * result['importe']

    grouped = result.groupby(by=['cod_cia','periodo','cod_subramo'],
                             as_index=False).agg(primas_emitidas = ('primas_emitidas','sum'), 
                                                 primas_devengadas = ('primas_devengadas','sum'),
                                                 siniestros_devengados = ('siniestros_devengados','sum'),
                                                 gastos_totales_devengados = ('gastos_devengados','sum'))

    return grouped

base, parametros_reportes = genero_dataframes(conn)

# Armar un diccionario con todas las claves que incluya las cuentas del PCU y sus respectivo signo
codigos_map = {}
for i in parametros_reportes['concepto'].unique():
    codigos_map[i] = dict(zip(parametros_reportes[parametros_reportes['concepto'] == i]['cod_cuenta'],
                        parametros_reportes[parametros_reportes['concepto'] == i]['signo']))
    

final = genero_resultado(base,codigos_map)

conn.close()