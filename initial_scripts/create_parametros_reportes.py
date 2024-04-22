import pandas as pd
import datetime

import sqlite3

    
def main():
    file_path = '/Users/diego.frigerio/Downloads/PARAMETROSREPORTES.txt'

    pm = pd.read_csv(file_path, sep=';')
    pm.drop(columns=['orden','extra'], inplace=True)
    pm.columns = [x.lower() for x in pm.columns]

    pm['reporte'] = pm['reporte'].str.lower()
    pm['reporte'] = pm['reporte'].str.strip()
    pm['referencia'] = pm['referencia'].str.lower()

    keep = ['anexo13-b', 'anexo14-b', 'anexo14-a', 'anexo13-a', 'resultados',
        'anexo12-bm', 'anexo12-am', 'anexo16', 'anexo8-a', 'anexo11-a',
        'ganaron-perdieron', 'nuevort', 'pasivo','inversiones']

    cd = pm.loc[pm['reporte'].isin(keep), ['reporte','referencia','codigo_completo','signo']]
    cd.reset_index(inplace=True, drop=True)
    cd.sort_values(by=['reporte','referencia'], inplace=True, ignore_index=True)

    cd.rename(columns={'codigo_completo':'cod_cuenta'}, inplace=True)


    # Crear conexión a la base de datos SQLite
    conn = sqlite3.connect('../revista_tr_database.db')

    # SQL para crear la tabla
    create_table_sql = '''
    CREATE TABLE IF NOT EXISTS parametros_reportes (
        reporte TEXT NOT NULL,
        referencia TEXT NOT NULL,
        cod_cuenta TEXT NOT NULL,
        signo INTEGER NOT NULL
    );
    '''

    # Ejecutar el comando para crear la tabla
    conn.execute(create_table_sql)
    # Confirmar (commit) la transacción y cerrar la conexión
    conn.commit()


    # Insertar los datos en la base de datos
    # Si la tabla ya existe, los datos se agregarán a ella
    cd.to_sql('parametros_reportes', conn, if_exists='append', index=False)

    # Cerrar la conexión
    conn.close()

if __name__ == "__main__":
    main()