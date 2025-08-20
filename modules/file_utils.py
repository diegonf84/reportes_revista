"""
Utilidades para verificar existencia y estado de archivos MDB.
"""

import os
from pathlib import Path
from typing import Dict, List, Tuple
from modules.common import periodo_to_filename, get_mdb_files_directory


def check_mdb_file_exists(periodo: int) -> Tuple[bool, str]:
    """
    Verifica si existe el archivo MDB para un período específico.
    
    Args:
        periodo (int): Período en formato YYYYPP
        
    Returns:
        Tuple[bool, str]: (existe, ruta_completa)
    """
    try:
        directorio = get_mdb_files_directory()
        filename = periodo_to_filename(periodo)
        archivo_path = directorio / filename
        
        exists = archivo_path.exists()
        return exists, str(archivo_path)
    except Exception:
        return False, ""


def list_available_mdb_files() -> List[Dict[str, any]]:
    """
    Lista todos los archivos MDB disponibles en el directorio.
    
    Returns:
        List[Dict]: Lista de archivos con información detallada
    """
    try:
        directorio = get_mdb_files_directory()
        if not directorio.exists():
            return []
        
        files = []
        for file_path in directorio.glob("*.zip"):
            try:
                # Extraer información del nombre del archivo
                name = file_path.stem  # nombre sin extensión
                if '-' in name:
                    year_str, quarter_str = name.split('-')
                    year = int(year_str)
                    quarter = int(quarter_str)
                    periodo = int(f"{year}{quarter:02d}")
                    
                    files.append({
                        'filename': file_path.name,
                        'periodo': periodo,
                        'year': year,
                        'quarter': quarter,
                        'size': file_path.stat().st_size,
                        'modified': file_path.stat().st_mtime
                    })
            except (ValueError, IndexError):
                # Ignorar archivos que no siguen el formato esperado
                continue
        
        # Ordenar por período (más reciente primero)
        files.sort(key=lambda x: x['periodo'], reverse=True)
        return files
        
    except Exception:
        return []


def get_file_status(periodo_archivo: int, periodo_anterior: int = None) -> Dict[str, any]:
    """
    Obtiene el estado del archivo MDB actual y del período anterior en la base de datos.
    
    Args:
        periodo_archivo (int): Período del archivo a verificar
        periodo_anterior (int, optional): Período anterior para comparación en BD
        
    Returns:
        Dict: Estado detallado del archivo y periodo en BD
    """
    status = {
        'archivo_actual': {},
        'periodo_anterior_db': {},
        'can_compare': False
    }
    
    # Verificar archivo actual (MDB)
    exists_actual, path_actual = check_mdb_file_exists(periodo_archivo)
    status['archivo_actual'] = {
        'exists': exists_actual,
        'path': path_actual,
        'periodo': periodo_archivo,
        'filename': periodo_to_filename(periodo_archivo) if exists_actual else None
    }
    
    # Verificar período anterior en base de datos (no archivo MDB)
    if periodo_anterior:
        status['periodo_anterior_db'] = {
            'periodo': periodo_anterior,
            'exists_in_db': False  # Se verificará en el endpoint
        }
        
        # Solo se puede comparar si existe el archivo actual
        status['can_compare'] = exists_actual
    
    return status