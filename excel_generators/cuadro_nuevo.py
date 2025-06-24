import pandas as pd
import openpyxl
from openpyxl.styles import Font, Border, Side
import os
import logging
import argparse

def create_excel_cuadro_nuevo(csv_path: str, output_path: str, period: str) -> None:
    """
    Genera archivo Excel formateado para el reporte 'cuadro_nuevo'.
    
    Args:
        csv_path: Ruta al archivo CSV de entrada
        output_path: Ruta donde guardar el Excel
        period: Período del reporte (ej: "202501")
    """
    
    # Leer CSV
    df = pd.read_csv(csv_path)
    
    # Crear workbook y worksheet
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"Cuadro Nuevo {period}"
    
    # Definir estilos
    header_font = Font(name="Arial", size=10, bold=True)
    normal_font = Font(name="Arial", size=10)
    total_font = Font(name="Arial", size=10, bold=True)
    
    # Definir bordes
    thin_border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    
    # Headers de columnas
    headers = [
        "ENTIDAD", "Producción", "Disponibilidades", "Inversiones", 
        "Inmuebles", "Deudas Con Asegurados", "Stros a/c Reas", 
        "Deudas Neto", "Patrimonio Neto"
    ]
    
    # Mapeo de columnas del CSV a headers del Excel
    column_mapping = {
        'nombre_corto': 'ENTIDAD',
        'primas_emitidas': 'Producción',
        'disponibilidades': 'Disponibilidades',
        'inversiones': 'Inversiones',
        'inmuebles': 'Inmuebles',
        'deudas_total_aseg': 'Deudas Con Asegurados',
        'deudas_con_asegurados_ac_reaseguros': 'Stros a/c Reas',
        'deudas_neto': 'Deudas Neto',
        'patrimonio_neto': 'Patrimonio Neto'
    }
    
    current_row = 1
    
    # Procesar cada tipo de compañía
    for tipo_cia in df['tipo_cia'].unique():
        
        # Filtrar datos para este tipo
        data_tipo = df[df['tipo_cia'] == tipo_cia].copy()
        
        # Header del tipo (ej: "ART", "Generales")
        cell_tipo = ws.cell(row=current_row, column=1, value=tipo_cia)
        cell_tipo.font = header_font
        current_row += 1
        
        # Headers de columnas
        for col_idx, header in enumerate(headers, 1):
            cell = ws.cell(row=current_row, column=col_idx, value=header)
            cell.font = header_font
            cell.border = thin_border
        current_row += 1
        
        # Datos de las compañías
        for _, row_data in data_tipo.iterrows():
            col_idx = 1
            for csv_col, excel_header in column_mapping.items():
                value = row_data[csv_col]
                cell = ws.cell(row=current_row, column=col_idx, value=value)
                cell.font = normal_font
                cell.border = thin_border
                
                # Formatear números (excepto la primera columna que es texto)
                if col_idx > 1 and pd.notna(value):
                    cell.number_format = '#,##0,'
                
                col_idx += 1
            current_row += 1
        
        # Fila de totales
        cell_total = ws.cell(row=current_row, column=1, value="Total")
        cell_total.font = total_font
        cell_total.border = thin_border
        
        # Calcular y escribir totales
        for col_idx, (csv_col, excel_header) in enumerate(column_mapping.items(), 1):
            if col_idx > 1:  # Skip primera columna (nombre)
                total_value = data_tipo[csv_col].sum()
                cell = ws.cell(row=current_row, column=col_idx, value=total_value)
                cell.font = total_font
                cell.border = thin_border
                cell.number_format = '#,##0,'
        
        current_row += 2  # Espacio entre tipos
    
    # Ajustar ancho de columnas
    column_widths = [25, 15, 15, 15, 12, 20, 15, 15, 18]
    for col_idx, width in enumerate(column_widths, 1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(col_idx)].width = width
    
    # Guardar archivo
    wb.save(output_path)
    logging.info(f"Excel generado en: {output_path}")

def generate_cuadro_nuevo_excel(period: str, csv_dir: str = None) -> str:
    """
    Función de conveniencia para generar el Excel del cuadro nuevo.
    
    Args:
        period: Período (ej: "202501")
        csv_dir: Directorio donde está el CSV (default: ending_files/{period}/)
        
    Returns:
        Ruta del archivo Excel generado
    """
    # Si no se especifica csv_dir, usar la estructura por defecto
    if csv_dir is None:
        csv_dir = os.path.join("ending_files", period)
    
    # Crear directorio con el nombre del período (igual que generate_all_reports)
    output_dir = "excel_final_files"
    period_dir = os.path.join(output_dir, period)
    os.makedirs(period_dir, exist_ok=True)
    
    # Construir rutas de archivos
    csv_path = os.path.join(csv_dir, f"{period}_cuadro_nuevo.csv")
    output_path = os.path.join(period_dir, f"{period}_cuadro_nuevo.xlsx")
    
    create_excel_cuadro_nuevo(csv_path, output_path, period)
    return output_path

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Genera Excel formateado para cuadro nuevo')
    parser.add_argument('period', help='Período del reporte (ej: 202501)')
    parser.add_argument('--csv_dir', default=None, help='Directorio donde está el CSV (default: ending_files/{period}/)')
    
    args = parser.parse_args()
    
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    try:
        excel_path = generate_cuadro_nuevo_excel(
            period=args.period,
            csv_dir=args.csv_dir
        )
        print(f"✅ Excel generado exitosamente: {excel_path}")
    except FileNotFoundError as e:
        print(f"❌ Error: No se encontró el archivo CSV esperado")
        expected_csv_path = f"ending_files/{args.period}" if args.csv_dir is None else args.csv_dir
        print(f"   Buscando CSV en: {expected_csv_path}/{args.period}_cuadro_nuevo.csv")
    except Exception as e:
        print(f"❌ Error inesperado: {e}")