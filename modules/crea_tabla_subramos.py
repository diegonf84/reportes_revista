import pandas as pd
import sqlite3
import logging
import os
import argparse
from dotenv import load_dotenv
from typing import Dict, Tuple, Optional

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_data(conn: sqlite3.Connection, periodo_inicial: int) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Obtiene datos necesarios de la base de datos para generar reportes por subramos.

    Args:
        conn (sqlite3.Connection): Conexión a la base de datos
        periodo_inicial (int): Período inicial desde el cual filtrar (formato YYYYPP)

    Returns:
        Tuple[pd.DataFrame, pd.DataFrame]: Tupla con (dataframe base, parámetros de reportes)
    """
    base = pd.read_sql_query(
        f"SELECT * FROM base_balance_ultimos_periodos WHERE periodo >= {periodo_inicial}",
        conn
    )
    
    filtro = pd.read_sql_query(
        "SELECT * FROM conceptos_reportes WHERE es_subramo is TRUE", 
        conn
    )
    
    params_full = pd.read_sql_query(
        "SELECT * FROM parametros_reportes",
        conn
    )

    parametros_reportes = params_full.merge(filtro, on=['reporte','referencia'], how='inner')
    logging.info(f"Base generada con {len(base):,} registros")

    return base, parametros_reportes

def generate_subramos_table(data: pd.DataFrame, codigos: Dict[str, Dict[str, int]]) -> pd.DataFrame:
    """
    Genera tabla agregada por subramos.

    Args:
        data (pd.DataFrame): DataFrame con datos base
        codigos (Dict[str, Dict[str, int]]): Diccionario con mapeos de códigos y signos

    Returns:
        pd.DataFrame: DataFrame agregado por subramos
    """
    result = data.copy()

    for concepto, mapping in codigos.items():
        result[concepto] = result['cod_cuenta'].map(mapping) * result['importe']

    return result.groupby(
        by=['cod_cia', 'periodo', 'cod_subramo'],
        as_index=False
    ).agg(
        primas_emitidas=('primas_emitidas', 'sum'),
        primas_devengadas=('primas_devengadas', 'sum'),
        siniestros_devengados=('siniestros_devengados', 'sum'),
        gastos_totales_devengados=('gastos_devengados', 'sum'),
        primas_cedidas=('primas_cedidas', 'sum')
    )

def main(periodo_inicial: Optional[int] = None) -> None:
    """
    Crea tabla con información agregada por subramos.
    
    Esta función agrupa los datos por compañía, período y subramo, calculando
    diferentes métricas como primas emitidas, primas devengadas, siniestros
    devengados, gastos totales devengados y primas cedidas.

    Args:
        periodo_inicial (Optional[int]): Período inicial desde el cual filtrar los datos.
                                       Si es None, se calculan los últimos 2 años.
    """
    load_dotenv()
    database_path = os.getenv('DATABASE')

    # Si no se especifica periodo, usar los últimos 2 años
    if periodo_inicial is None:
        import datetime
        anio_actual = datetime.datetime.now().year
        periodo_inicial = int(f"{anio_actual - 2}00")

    logging.info(f"Generando tabla de subramos con datos desde el período: {periodo_inicial}")

    try:
        with sqlite3.connect(database_path) as conn:
            base, parametros_reportes = get_data(conn, periodo_inicial)
            
            codigos_map = {
                concepto: dict(zip(
                    parametros_reportes[parametros_reportes['concepto'] == concepto]['cod_cuenta'],
                    parametros_reportes[parametros_reportes['concepto'] == concepto]['signo']
                ))
                for concepto in parametros_reportes['concepto'].unique()
            }

            result_df = generate_subramos_table(base, codigos_map)
            
            # Crear nueva tabla
            conn.execute("DROP TABLE IF EXISTS base_subramos")
            result_df.to_sql('base_subramos', conn, index=False)
            
            count = pd.read_sql_query("SELECT COUNT(*) as count FROM base_subramos", conn)
            logging.info(f"Tabla base_subramos creada con {count['count'].iloc[0]:,} registros")

    except sqlite3.Error as e:
        logging.error(f"Error en base de datos: {e}")
        raise

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Crea tabla agregada por subramos')
    parser.add_argument('--periodo_inicial', type=int, 
                       help='Período inicial (formato YYYYPP) desde el cual filtrar los datos')
    args = parser.parse_args()
    
    main(args.periodo_inicial)