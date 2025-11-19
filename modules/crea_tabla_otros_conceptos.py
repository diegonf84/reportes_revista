import pandas as pd
import sqlite3
import logging
import os
import argparse
from dotenv import load_dotenv
from typing import Dict, Tuple, Optional
from modules.common import setup_logging
from utils.db_manager import db_manager

def get_recent_data(conn: sqlite3.Connection, periodo_especifico: Optional[int] = None) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Obtiene datos del último período disponible (o período especificado) y parámetros
    de reportes para conceptos que no son por subramo.

    Args:
        conn (sqlite3.Connection): Conexión a la base de datos
        periodo_especifico: Período específico a usar (formato YYYYPP).
                          Si es None, usa MAX(periodo).

    Returns:
        Tuple[pd.DataFrame, pd.DataFrame]: Tupla con (datos base del período,
                                          parámetros de reportes filtrados)
    """
    if periodo_especifico is None:
        # DEFAULT: Usar MAX(periodo)
        query = """
        SELECT *
        FROM base_balance_ultimos_periodos
        WHERE periodo = (
            SELECT MAX(periodo)
            FROM base_balance_ultimos_periodos
        )
        """
        logging.info("Modo automático: usando MAX(periodo) de la base de datos")
    else:
        # SPECIFIED: Usar período especificado
        query = f"""
        SELECT *
        FROM base_balance_ultimos_periodos
        WHERE periodo = {periodo_especifico}
        """
        logging.info(f"Modo manual: usando período especificado = {periodo_especifico}")

    base = pd.read_sql_query(query, conn)
    filtro = pd.read_sql_query("SELECT * FROM conceptos_reportes WHERE es_subramo is FALSE", conn)
    params_full = pd.read_sql_query("SELECT * FROM parametros_reportes", conn)

    parametros_reportes = params_full.merge(filtro, on=['reporte','referencia'], how='inner')
    logging.info(f"Base generada con {len(base):,} registros del período {base['periodo'].max()}")

    return base, parametros_reportes

def generate_conceptos_table(data: pd.DataFrame, codigos: Dict[str, Dict[str, int]]) -> pd.DataFrame:
    """
    Genera tabla agregada por diferentes conceptos que no tienen subramo asociado.
    
    Esta función transforma los datos aplicando mapeos de códigos y signos,
    y luego agrupa por compañía y período para calcular diversos indicadores
    financieros.
    
    Args:
        data (pd.DataFrame): DataFrame con los datos base
        codigos (Dict[str, Dict[str, int]]): Diccionario con mapeos de códigos y signos
                                          para cada concepto
        
    Returns:
        pd.DataFrame: DataFrame agregado por compañía y período con los conceptos calculados
    """
    result = data.copy()

    for concepto, mapping in codigos.items():
        result[concepto] = result['cod_cuenta'].map(mapping) * result['importe']

    return result.groupby(
        by=['cod_cia', 'periodo'],
        as_index=False
    ).agg(
        resultado_tecnico=('resultado_tecnico', 'sum'),
        resultado_financiero=('resultado_financiero', 'sum'),
        resultado_operaciones=('resultado_operaciones', 'sum'),
        impuesto_ganancias=('impuesto_ganancias', 'sum'),
        deudas_con_asegurados=('deudas_con_asegurados', 'sum'),
        deudas_con_asegurados_ac_reaseguros=('deudas_con_asegurados_ac_reaseguros', 'sum'),
        disponibilidades=('disponibilidades', 'sum'),
        inmuebles_inversion=('inmuebles_inversion', 'sum'),
        inmuebles_uso_propio=('inmuebles_uso_propio', 'sum'),
        inversiones=('inversiones', 'sum'),
        patrimonio_neto=('patrimonio_neto', 'sum'),
    )

def main(periodo_referencia: Optional[int] = None) -> None:
    """
    Función principal que crea una tabla con conceptos financieros agregados
    del último período disponible (o período especificado) en la base de datos.

    La tabla resultante 'base_otros_conceptos' contiene información financiera
    como resultado técnico, financiero, operaciones, impuestos, deudas,
    disponibilidades, inversiones y patrimonio neto, agregados por compañía.

    Args:
        periodo_referencia: Período de referencia (formato YYYYPP).
                          Si es None, usa MAX(periodo) de la base de datos.

    Raises:
        sqlite3.Error: Si ocurre un error en las operaciones con la base de datos
    """
    try:
        with db_manager.get_connection() as conn:
            base, parametros_reportes = get_recent_data(conn, periodo_referencia)
            
            codigos_map = {
                concepto: dict(zip(
                    parametros_reportes[parametros_reportes['concepto'] == concepto]['cod_cuenta'],
                    parametros_reportes[parametros_reportes['concepto'] == concepto]['signo']
                ))
                for concepto in parametros_reportes['concepto'].unique()
            }

            result_df = generate_conceptos_table(base, codigos_map)
            
            # Crear nueva tabla
            db_manager.drop_table_if_exists("base_otros_conceptos")
            db_manager.insert_dataframe(result_df, "base_otros_conceptos", if_exists='replace')
            
            count = db_manager.get_table_count("base_otros_conceptos")
            logging.info(f"Tabla base_otros_conceptos creada con {count:,} registros")

    except Exception as e:
        logging.error(f"Error creando tabla: {e}")
        raise

if __name__ == "__main__":
    setup_logging()

    parser = argparse.ArgumentParser(
        description='Crea tabla con conceptos financieros agregados',
        epilog="""
Ejemplos:
  python modules/crea_tabla_otros_conceptos.py
    (Usa automáticamente MAX(periodo) de la base de datos)

  python modules/crea_tabla_otros_conceptos.py --periodo 202503
    (Usa específicamente el período 202503)
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument('--periodo', type=int, help='Período específico (formato YYYYPP). Si no se especifica, usa MAX(periodo).')

    args = parser.parse_args()
    main(args.periodo)