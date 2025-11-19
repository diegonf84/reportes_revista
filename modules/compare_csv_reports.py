"""
Módulo para comparar archivos CSV entre dos períodos.
Genera un reporte de diferencias en las compañías presentes en cada archivo.
"""

import os
import pandas as pd
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Set
from datetime import datetime


def get_csv_files(period_dir: Path) -> List[str]:
    """
    Obtiene la lista de archivos CSV en un directorio de período.

    Args:
        period_dir: Path al directorio del período

    Returns:
        Lista de nombres de archivos CSV (sin la ruta completa)
    """
    if not period_dir.exists():
        return []

    csv_files = [f.name for f in period_dir.glob("*.csv")]
    return sorted(csv_files)


def extract_report_name(filename: str, period: str) -> str:
    """
    Extrae el nombre del reporte removiendo el prefijo del período.

    Args:
        filename: Nombre del archivo (ej: "202503_apertura_por_subramo.csv")
        period: Período (ej: "202503")

    Returns:
        Nombre del reporte sin período (ej: "apertura_por_subramo.csv")
    """
    # Remover prefijo del período + guión bajo
    prefix = f"{period}_"
    if filename.startswith(prefix):
        return filename[len(prefix):]
    return filename


def read_csv_companies(csv_path: Path, separator: str = ';') -> pd.DataFrame:
    """
    Lee un archivo CSV y extrae las compañías únicas con cod_cia y nombre_corto.

    Args:
        csv_path: Path al archivo CSV
        separator: Separador usado en el CSV (default ';')

    Returns:
        DataFrame con columnas cod_cia y nombre_corto de compañías únicas
    """
    try:
        # Intentar leer con el separador especificado
        df = pd.read_csv(csv_path, sep=separator)

        # Si no tiene las columnas esperadas, intentar con otro separador
        if 'cod_cia' not in df.columns or 'nombre_corto' not in df.columns:
            df = pd.read_csv(csv_path, sep=',' if separator == ';' else ';')

        # Verificar que tenga las columnas necesarias
        if 'cod_cia' not in df.columns or 'nombre_corto' not in df.columns:
            logging.warning(f"CSV {csv_path.name} no tiene columnas cod_cia y/o nombre_corto")
            return pd.DataFrame(columns=['cod_cia', 'nombre_corto'])

        # Extraer compañías únicas
        companies = df[['cod_cia', 'nombre_corto']].drop_duplicates().sort_values('cod_cia')

        return companies

    except Exception as e:
        logging.error(f"Error leyendo {csv_path.name}: {str(e)}")
        return pd.DataFrame(columns=['cod_cia', 'nombre_corto'])


def compare_csv_file(actual_path: Path, previous_path: Path, separator: str = ';') -> Dict:
    """
    Compara un archivo CSV entre dos períodos.

    Args:
        actual_path: Path al archivo CSV del período actual
        previous_path: Path al archivo CSV del período anterior
        separator: Separador usado en el CSV

    Returns:
        Diccionario con resultados de la comparación
    """
    actual_companies = read_csv_companies(actual_path, separator)
    previous_companies = read_csv_companies(previous_path, separator)

    # Conjuntos de códigos de compañía
    actual_codes = set(actual_companies['cod_cia'].astype(str))
    previous_codes = set(previous_companies['cod_cia'].astype(str))

    # Compañías nuevas (en actual pero no en anterior)
    new_codes = actual_codes - previous_codes
    new_companies = actual_companies[actual_companies['cod_cia'].astype(str).isin(new_codes)]

    # Compañías faltantes (en anterior pero no en actual)
    missing_codes = previous_codes - actual_codes
    missing_companies = previous_companies[previous_companies['cod_cia'].astype(str).isin(missing_codes)]

    return {
        'file_name': actual_path.name,
        'total_actual': len(actual_companies),
        'total_previous': len(previous_companies),
        'new_companies': new_companies.to_dict('records'),
        'missing_companies': missing_companies.to_dict('records'),
        'count_new': len(new_companies),
        'count_missing': len(missing_companies)
    }


def compare_all_csv_reports(period_actual: str, period_previous: str,
                           base_dir: str = None) -> Dict:
    """
    Compara todos los archivos CSV entre dos períodos.

    Args:
        period_actual: Período actual (ej: "202504")
        period_previous: Período anterior (ej: "202503")
        base_dir: Directorio base donde están los archivos (default: ending_files)

    Returns:
        Diccionario con resultados de todas las comparaciones
    """
    if base_dir is None:
        # Obtener directorio base del proyecto
        script_dir = Path(__file__).parent.parent
        base_dir = script_dir / "ending_files"
    else:
        base_dir = Path(base_dir)

    actual_dir = base_dir / period_actual
    previous_dir = base_dir / period_previous

    # Verificar que los directorios existan
    if not actual_dir.exists():
        raise FileNotFoundError(f"Directorio del período actual no existe: {actual_dir}")

    if not previous_dir.exists():
        raise FileNotFoundError(f"Directorio del período anterior no existe: {previous_dir}")

    # Obtener listas de archivos CSV con nombres completos
    actual_files_full = get_csv_files(actual_dir)
    previous_files_full = get_csv_files(previous_dir)

    # Crear mapeos: report_name -> full_filename
    actual_reports = {extract_report_name(f, period_actual): f for f in actual_files_full}
    previous_reports = {extract_report_name(f, period_previous): f for f in previous_files_full}

    # Reportes comunes (presentes en ambos períodos)
    common_report_names = set(actual_reports.keys()) & set(previous_reports.keys())

    # Reportes solo en actual
    only_actual_names = set(actual_reports.keys()) - set(previous_reports.keys())
    only_actual = [actual_reports[name] for name in only_actual_names]

    # Reportes solo en anterior
    only_previous_names = set(previous_reports.keys()) - set(actual_reports.keys())
    only_previous = [previous_reports[name] for name in only_previous_names]

    # Comparar archivos comunes
    comparisons = []
    for report_name in sorted(common_report_names):
        # Determinar separador según el archivo
        separator = ';'  # Por defecto
        if 'cuadro_nuevo' in report_name or 'detalle_inmuebles' in report_name or \
           'detalle_gastos' in report_name or 'distribucion_inversiones' in report_name or \
           'indicadores_solvencia' in report_name:
            separator = ','

        actual_filename = actual_reports[report_name]
        previous_filename = previous_reports[report_name]

        actual_path = actual_dir / actual_filename
        previous_path = previous_dir / previous_filename

        comparison = compare_csv_file(actual_path, previous_path, separator)
        # Update file_name to show the report name without period
        comparison['file_name'] = report_name
        comparison['actual_file'] = actual_filename
        comparison['previous_file'] = previous_filename
        comparisons.append(comparison)

    return {
        'period_actual': period_actual,
        'period_previous': period_previous,
        'comparisons': comparisons,
        'only_in_actual': sorted(only_actual),
        'only_in_previous': sorted(only_previous),
        'total_compared': len(comparisons)
    }


def generate_comparison_report(comparison_results: Dict, output_path: Path) -> None:
    """
    Genera un reporte en formato TXT con los resultados de la comparación.

    Args:
        comparison_results: Resultados de la comparación
        output_path: Path donde guardar el reporte TXT
    """
    period_actual = comparison_results['period_actual']
    period_previous = comparison_results['period_previous']

    lines = []
    lines.append("=" * 80)
    lines.append("COMPARACIÓN DE ARCHIVOS CSV ENTRE PERÍODOS")
    lines.append("=" * 80)
    lines.append(f"Período Actual:   {period_actual}")
    lines.append(f"Período Anterior: {period_previous}")
    lines.append(f"Fecha de generación: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("=" * 80)
    lines.append("")

    # Archivos solo en un período
    if comparison_results['only_in_actual']:
        lines.append("⚠️  ARCHIVOS PRESENTES SOLO EN PERÍODO ACTUAL:")
        for file in comparison_results['only_in_actual']:
            lines.append(f"   - {file}")
        lines.append("")

    if comparison_results['only_in_previous']:
        lines.append("⚠️  ARCHIVOS PRESENTES SOLO EN PERÍODO ANTERIOR:")
        for file in comparison_results['only_in_previous']:
            lines.append(f"   - {file}")
        lines.append("")

    # Comparaciones detalladas
    lines.append(f"📊 ARCHIVOS COMPARADOS: {comparison_results['total_compared']}")
    lines.append("=" * 80)
    lines.append("")

    for comp in comparison_results['comparisons']:
        lines.append("-" * 80)
        lines.append(f"REPORTE: {comp['file_name']}")
        lines.append("-" * 80)
        lines.append(f"Archivo actual:   {comp.get('actual_file', 'N/A')}")
        lines.append(f"Archivo anterior: {comp.get('previous_file', 'N/A')}")
        lines.append("")
        lines.append(f"Total compañías en período actual:   {comp['total_actual']}")
        lines.append(f"Total compañías en período anterior: {comp['total_previous']}")
        lines.append(f"Compañías nuevas:     {comp['count_new']}")
        lines.append(f"Compañías faltantes:  {comp['count_missing']}")
        lines.append("")

        # Compañías nuevas
        if comp['new_companies']:
            lines.append("✅ COMPAÑÍAS NUEVAS (en actual, no en anterior):")
            for company in comp['new_companies']:
                lines.append(f"   - {company['cod_cia']} | {company['nombre_corto']}")
            lines.append("")

        # Compañías faltantes
        if comp['missing_companies']:
            lines.append("❌ COMPAÑÍAS FALTANTES (en anterior, no en actual):")
            for company in comp['missing_companies']:
                lines.append(f"   - {company['cod_cia']} | {company['nombre_corto']}")
            lines.append("")

        # Si no hay diferencias
        if not comp['new_companies'] and not comp['missing_companies']:
            lines.append("✓ No hay diferencias en las compañías entre períodos")
            lines.append("")

        lines.append("")

    lines.append("=" * 80)
    lines.append("FIN DEL REPORTE")
    lines.append("=" * 80)

    # Escribir archivo
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    logging.info(f"Reporte de comparación generado: {output_path}")


def main(period_actual: str, period_previous: str):
    """
    Función principal para ejecutar la comparación desde línea de comandos.

    Args:
        period_actual: Período actual (ej: "202504")
        period_previous: Período anterior (ej: "202503")
    """
    logging.basicConfig(level=logging.INFO,
                       format='%(asctime)s - %(levelname)s - %(message)s')

    try:
        # Ejecutar comparación
        logging.info(f"Comparando período {period_actual} vs {period_previous}")
        results = compare_all_csv_reports(period_actual, period_previous)

        # Generar reporte
        script_dir = Path(__file__).parent.parent
        output_dir = script_dir / "ending_files"
        output_path = output_dir / f"csv_comparison_{period_actual}_{period_previous}.txt"

        generate_comparison_report(results, output_path)

        logging.info(f"Comparación completada. Archivos comparados: {results['total_compared']}")
        logging.info(f"Reporte guardado en: {output_path}")

        return str(output_path)

    except Exception as e:
        logging.error(f"Error en comparación: {str(e)}")
        raise


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Comparar archivos CSV entre dos períodos')
    parser.add_argument('period_actual', help='Período actual (ej: 202504)')
    parser.add_argument('period_previous', help='Período anterior (ej: 202503)')

    args = parser.parse_args()

    main(args.period_actual, args.period_previous)
