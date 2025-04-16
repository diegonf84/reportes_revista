import pandas as pd
import sqlite3
import logging
import os
from dotenv import load_dotenv
from typing import Dict, Tuple

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_recent_data(conn: sqlite3.Connection) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Obtiene datos del último período disponible y parámetros de reportes para conceptos 
    que no son por subramo.
    
    Args:
        conn (sqlite3.Connection): Conexión a la base de datos
        
    Returns:
        Tuple[pd.DataFrame, pd.DataFrame]: Tupla con (datos base del último período, 
                                          parámetros de reportes filtrados)
    """
    query = """
    SELECT * 
    FROM base_balance_ultimos_periodos 
    WHERE periodo = (
        SELECT MAX(periodo) 
        FROM base_balance_ultimos_periodos
    )
    """
   
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

def main() -> None:
    """
    Función principal que crea una tabla con conceptos financieros agregados
    del último período disponible en la base de datos.
    
    La tabla resultante 'base_otros_conceptos' contiene información financiera
    como resultado técnico, financiero, operaciones, impuestos, deudas, 
    disponibilidades, inversiones y patrimonio neto, agregados por compañía.
    
    Raises:
        sqlite3.Error: Si ocurre un error en las operaciones con la base de datos
    """
    load_dotenv()
    database_path = os.getenv('DATABASE')

    try:
        with sqlite3.connect(database_path) as conn:
            base, parametros_reportes = get_recent_data(conn)
            
            codigos_map = {
                concepto: dict(zip(
                    parametros_reportes[parametros_reportes['concepto'] == concepto]['cod_cuenta'],
                    parametros_reportes[parametros_reportes['concepto'] == concepto]['signo']
                ))
                for concepto in parametros_reportes['concepto'].unique()
            }

            result_df = generate_conceptos_table(base, codigos_map)
            
            # Crear nueva tabla
            conn.execute("DROP TABLE IF EXISTS base_otros_conceptos")
            result_df.to_sql('base_otros_conceptos', conn, index=False)
            
            count = pd.read_sql_query("SELECT COUNT(*) as count FROM base_otros_conceptos", conn)
            logging.info(f"Tabla base_otros_conceptos creada con {count['count'].iloc[0]:,} registros")

    except sqlite3.Error as e:
        logging.error(f"Error en base de datos: {e}")
        raise

if __name__ == "__main__":
    main()