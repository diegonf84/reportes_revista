import json
import logging
import os
import argparse
from typing import Dict, Any
from utils.report_generator import export_query_to_csv

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
            # Reemplazar placeholders en la query con el período actual
            query = report_config["query"].format(period=period)
            
            export_query_to_csv(
                query=query,
                output_path=output_file,
                int_columns=report_config.get("int_columns", []),
                separator=report_config.get("separator", ";"),
                decimal=report_config.get("decimal", ",")
            )
            
            logging.info(f"Reporte {report_name} generado en {output_file}")
        except Exception as e:
            logging.error(f"Error al generar reporte {report_name}: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Genera reportes del mercado asegurador')
    parser.add_argument('--definitions', type=str, default='report_definitions.json',
                        help='Archivo JSON con definiciones de reportes')
    parser.add_argument('--output_dir', type=str, default='./',
                        help='Directorio base donde guardar los reportes')
    parser.add_argument('--period', type=str, default='202404',
                        help='Período para generar reportes (formato YYYYQQ)')
    parser.add_argument('--report', type=str, 
                        help='Nombre específico del reporte a generar (opcional)')
    
    args = parser.parse_args()
    
    generate_all_reports(
        definitions_file=args.definitions,
        output_dir=args.output_dir,
        period=args.period,
        specific_report=args.report
    )