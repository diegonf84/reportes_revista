import pandas as pd
import datetime

import sqlite3

def main():
    conn = sqlite3.connect('../revista_tr_database.db')

    # SQL para crear la tabla
    create_table_sql = '''
    CREATE TABLE IF NOT EXISTS conceptos_reportes (
        reporte TEXT NOT NULL,
        referencia TEXT NOT NULL,
        concepto TEXT NOT NULL
    );
    '''

    # Ejecutar el comando para crear la tabla
    conn.execute(create_table_sql)

    # Confirmar (commit) la transacción y cerrar la conexión
    conn.commit()

    filtro = pd.DataFrame({'reporte':['anexo12-am','anexo12-am','anexo12-bm','anexo13-b','anexo14-b'],
               'referencia':['ref1','ref2','ref6','ref7','ref2'], 
               'concepto':['primas_emitidas','primas_cedidas','primas_devengadas','siniestros_devengados','gastos_devengados']})
    
    # Insertar los datos en la base de datos
    # Si la tabla ya existe, los datos se agregarán a ella
    filtro.to_sql('conceptos_reportes', conn, if_exists='append', index=False)

    # Cerrar la conexión
    conn.close()


if __name__ == "__main__":
    main()