"""
Common utilities for modules that process periods.

This module provides shared functionality for period validation,
file handling, and other common operations used across multiple modules.
"""

import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def validate_period(periodo: int) -> None:
    """
    Validates that the period follows the YYYYPP format.
    
    Args:
        periodo (int): Period in format YYYYPP (e.g., 202503)
        
    Raises:
        ValueError: If period format is invalid
        
    Examples:
        >>> validate_period(202501)  # Valid
        >>> validate_period(20251)   # Raises ValueError
    """
    periodo_str = str(periodo)
    if len(periodo_str) != 6:
        raise ValueError(f"Period must be 6 digits (YYYYPP), received: {periodo}")
    
    year = int(periodo_str[:4])
    quarter = int(periodo_str[4:])
    
    if year < 2020 or year > 2030:
        raise ValueError(f"Year must be between 2020-2030, received: {year}")
    
    if quarter < 1 or quarter > 4:
        raise ValueError(f"Quarter must be between 1-4, received: {quarter}")


def periodo_to_filename(periodo: int) -> str:
    """
    Converts internal period format to filename format.
    
    Args:
        periodo (int): Period in format YYYYPP (e.g., 202503)
        
    Returns:
        str: ZIP filename (e.g., "2025-3.zip")
        
    Examples:
        >>> periodo_to_filename(202501)
        "2025-1.zip"
        >>> periodo_to_filename(202503)
        "2025-3.zip"
    """
    validate_period(periodo)
    
    periodo_str = str(periodo)
    year = periodo_str[:4]
    quarter = periodo_str[4:].lstrip('0')  # Remove leading zeros
    
    if not quarter:  # If empty (e.g., 202500)
        quarter = '0'
        
    return f"{year}-{quarter}.zip"


def find_file_in_directory(directorio: Path, filename: str) -> Path:
    """
    Searches for a specific file in the directory.
    
    Args:
        directorio (Path): Directory to search in
        filename (str): Name of file to search for
        
    Returns:
        Path: Complete path to the found file
        
    Raises:
        FileNotFoundError: If the file doesn't exist
    """
    archivo_path = directorio / filename
    
    if not archivo_path.exists():
        # List available files to help the user
        archivos_disponibles = [f.name for f in directorio.glob("*.zip")]
        raise FileNotFoundError(
            f"File {filename} not found in {directorio}.\n"
            f"Available files: {archivos_disponibles}"
        )
    
    return archivo_path


def get_mdb_files_directory() -> Path:
    """
    Returns the standard path to the MDB files directory.
    
    Returns:
        Path: Path to mdb_files_to_load directory
    """
    base_path = Path(__file__).parent.parent
    return base_path / "mdb_files_to_load"


def setup_logging(level: int = logging.INFO) -> None:
    """
    Sets up consistent logging configuration for all modules.
    
    Args:
        level (int): Logging level (default: INFO)
    """
    logging.basicConfig(
        level=level, 
        format='%(asctime)s - %(levelname)s - %(message)s'
    )


def format_number(num: int) -> str:
    """
    Formats numbers with thousand separators for better readability.
    
    Args:
        num (int): Number to format
        
    Returns:
        str: Formatted number string
        
    Examples:
        >>> format_number(1234567)
        "1,234,567"
    """
    return f"{num:,}"