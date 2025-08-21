import json
import logging
import os
import argparse
from typing import Dict, Any, Union, List
from utils.report_generator import export_query_to_csv

def process_query(query: Union[str, List[str]], period: str) -> str:
    """
    Procesa una query que puede estar en formato string o array de strings.
    
    Args:
        query: Query en formato string simple o array de strings
        period: Período para reemplazar en la query
        
    Returns:
        str: Query procesada como string único
    """
    if isinstance(query, list):
        # Si es array, unir con espacios y saltos de línea
        query_str = ' '.join(query)
    else:
        # Si es string, usar tal como está
        query_str = query
    
    # Reemplazar placeholder del período
    return query_str.format(period=period)

def generate_all_reports(
    definitions_file: str = 'report_definitions.json',
    output_dir: str = './',
    period: str = '202404',
    specific_report: str = None
) -> None:
    """
    Genera reportes definidos en el archivo JSON de definiciones.
    
    Args:
        definitions_file: Ruta al archivo JSON con definiciones
        output_dir: Directorio base donde se guardarán los reportes
        period: Período para el cual generar reportes (formato YYYYQQ)
        specific_report: Nombre específico del reporte a generar (opcional)
    """
    # Configurar logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # Crear directorio con el nombre del período
    period_dir = os.path.join(output_dir, period)
    os.makedirs(period_dir, exist_ok=True)
    
    # Cargar definiciones desde JSON
    try:
        with open(definitions_file, 'r', encoding='utf-8') as f:
            report_definitions = json.load(f)
    except Exception as e:
        logging.error(f"Error al cargar definiciones: {e}")
        return
    
    # Validar si se especificó un reporte específico
    if specific_report:
        if specific_report not in report_definitions:
            logging.error(f"Reporte '{specific_report}' no encontrado en definiciones")
            logging.info(f"Reportes disponibles: {', '.join(report_definitions.keys())}")
            return
        # Filtrar solo el reporte específico
        report_definitions = {specific_report: report_definitions[specific_report]}
    
    # Generar cada reporte
    for report_name, report_config in report_definitions.items():
        # Construir nombre de archivo dentro del directorio del período
        output_file = os.path.join(period_dir, f"{period}_{report_name}.csv")
        
        logging.info(f"Generando reporte: {report_name}")
        
        try:
            # Procesar query (maneja tanto string como array)
            processed_query = process_query(report_config["query"], period)
            
            export_query_to_csv(
                query=processed_query,
                output_path=output_file,
                int_columns=report_config.get("int_columns", []),
                separator=report_config.get("separator", ";"),
                decimal=report_config.get("decimal", ",")
            )
            
            logging.info(f"Reporte {report_name} generado en {output_file}")
        except Exception as e:
            logging.error(f"Error al generar reporte {report_name}: {e}")

if __name__ == "__main__":
    # Get absolute path to script directory for report_definitions.json
    script_dir = os.path.dirname(os.path.abspath(__file__))
    default_definitions_path = os.path.join(script_dir, 'report_definitions.json')
    
    parser = argparse.ArgumentParser(description='Genera reportes del mercado asegurador')
    parser.add_argument('period', help='Período para generar reportes (formato YYYYPP)')
    parser.add_argument('--definitions', type=str, default=default_definitions_path,
                        help='Archivo JSON con definiciones de reportes')
    parser.add_argument('--output_dir', type=str, default='./',
                        help='Directorio base donde guardar los reportes')
    parser.add_argument('--report', type=str, 
                        help='Nombre específico del reporte a generar (opcional)')
    
    args = parser.parse_args()
    
    generate_all_reports(
        definitions_file=args.definitions,
        output_dir=args.output_dir,
        period=args.period,
        specific_report=args.report
    )