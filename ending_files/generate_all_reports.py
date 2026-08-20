import logging
import os
import sys
import argparse
import json
from typing import Union, List

# Add parent directory to path to import utils
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.report_generator import export_query_to_csv
from modules.report_generation import CSV_CONTRACTS, validate_csv_outputs

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
) -> dict:
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
    with open(definitions_file, 'r', encoding='utf-8') as f:
        report_definitions = json.load(f)

    configured_reports = set(report_definitions)
    contracted_reports = set(CSV_CONTRACTS)
    if configured_reports != contracted_reports:
        missing = sorted(contracted_reports - configured_reports)
        unexpected = sorted(configured_reports - contracted_reports)
        raise ValueError(
            "Las definiciones y los contratos CSV no coinciden. "
            f"Faltan={missing}; inesperados={unexpected}"
        )
    
    # Validar si se especificó un reporte específico
    if specific_report:
        if specific_report not in report_definitions:
            raise ValueError(
                f"Reporte '{specific_report}' no encontrado. "
                f"Disponibles: {', '.join(report_definitions.keys())}"
            )
        # Filtrar solo el reporte específico
        report_definitions = {specific_report: report_definitions[specific_report]}
    
    successful = []
    failed = []

    # Generar cada reporte
    for report_name, report_config in report_definitions.items():
        # Construir nombre de archivo dentro del directorio del período
        output_file = os.path.join(period_dir, f"{period}_{report_name}.csv")
        
        logging.info(f"Generando reporte: {report_name}")
        
        try:
            # Procesar query (maneja tanto string como array)
            processed_query = process_query(report_config["query"], period)
            
            row_count = export_query_to_csv(
                query=processed_query,
                output_path=output_file,
                int_columns=report_config.get("int_columns", []),
                separator=report_config.get("separator", ";"),
                decimal=report_config.get("decimal", ",")
            )
            
            if row_count == 0:
                raise ValueError("El reporte no contiene registros")

            logging.info(f"Reporte {report_name} generado en {output_file}")
            print(f"✅ {report_name} completado")
            successful.append(report_name)
        except Exception as e:
            logging.error(f"Error al generar reporte {report_name}: {e}")
            print(f"❌ {report_name} falló: {e}")
            failed.append((report_name, str(e)))

    if not specific_report and not failed:
        try:
            validate_csv_outputs(period_dir, period)
        except Exception as e:
            logging.error(f"Error validando archivos CSV: {e}")
            failed.append(("Validación CSV", str(e)))

    return {
        "successful": successful,
        "failed": failed,
        "status": "success" if not failed else "partial" if successful else "failed",
        "output_directory": period_dir,
    }

if __name__ == "__main__":
    # Get absolute path to script directory for report_definitions.json and output_dir
    script_dir = os.path.dirname(os.path.abspath(__file__))
    default_definitions_path = os.path.join(script_dir, 'report_definitions.json')
    
    parser = argparse.ArgumentParser(description='Genera reportes del mercado asegurador')
    parser.add_argument('period', help='Período para generar reportes (formato YYYYPP)')
    parser.add_argument('--definitions', type=str, default=default_definitions_path,
                        help='Archivo JSON con definiciones de reportes')
    parser.add_argument('--output_dir', type=str, default=script_dir,
                        help='Directorio base donde guardar los reportes')
    parser.add_argument('--report', type=str, 
                        help='Nombre específico del reporte a generar (opcional)')
    
    args = parser.parse_args()
    
    try:
        result = generate_all_reports(
            definitions_file=args.definitions,
            output_dir=args.output_dir,
            period=args.period,
            specific_report=args.report
        )
    except Exception as e:
        logging.error(f"No se pudo iniciar la generación: {e}")
        print(f"❌ Generación CSV falló: {e}")
        sys.exit(1)

    print(
        f"Resumen CSV: {len(result['successful'])} exitosos, "
        f"{len(result['failed'])} fallidos"
    )
    sys.exit(0 if not result['failed'] else 1)
