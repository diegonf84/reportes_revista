import os
import logging
import sqlite3
import json
from io import StringIO
from pathlib import Path
from werkzeug.utils import secure_filename
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from app.forms.processing_forms import (
    CheckCompaniesForm, LoadDataForm, CreateRecentPeriodsForm, 
    CreateBaseSubramosForm, CreateFinancialConceptsForm, CreateSubramosForm, CheckPeriodsForm, UploadMDBForm
)

# Importar módulos existentes
import sys
from pathlib import Path

# Add project root to path for module imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from modules.check_cantidad_cias import main as check_companies_main
from modules.check_ultimos_periodos import print_periods_info, list_available_periods as list_periods
from modules.carga_base_principal import main as load_data_main
from modules.crea_tabla_ultimos_periodos import create_recent_periods_table
from modules.crea_tabla_subramos import main as create_base_subramos_main
from modules.crea_tabla_otros_conceptos import main as create_concepts_main
from modules.crea_tabla_subramos_corregida import create_table_from_query, export_testing_data
from modules.file_utils import check_mdb_file_exists, list_available_mdb_files, get_file_status
from modules.common import get_mdb_files_directory

data_processing_bp = Blueprint('data_processing', __name__)


class LogCapture:
    """Clase para capturar logs y enviarlos como respuesta JSON."""
    def __init__(self):
        self.logs = []
        self.handler = None
        
    def start_capture(self):
        """Inicia la captura de logs."""
        self.logs = []
        
        # Crear handler personalizado
        self.handler = logging.StreamHandler(StringIO())
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        self.handler.setFormatter(formatter)
        
        # Agregar handler al logger raíz
        logger = logging.getLogger()
        logger.addHandler(self.handler)
        logger.setLevel(logging.INFO)
        
    def get_logs(self):
        """Obtiene los logs capturados."""
        if self.handler:
            log_content = self.handler.stream.getvalue()
            return log_content.split('\n') if log_content else []
        return []
        
    def stop_capture(self):
        """Detiene la captura de logs."""
        if self.handler:
            logger = logging.getLogger()
            logger.removeHandler(self.handler)
            self.handler = None


@data_processing_bp.route('/data-verification')
def data_verification():
    """Página principal para verificación de datos."""
    check_companies_form = CheckCompaniesForm()
    check_periods_form = CheckPeriodsForm()
    upload_form = UploadMDBForm()
    
    return render_template('data_processing/verification.html', 
                         check_companies_form=check_companies_form,
                         check_periods_form=check_periods_form,
                         upload_form=upload_form)


@data_processing_bp.route('/data-loading')
def data_loading():
    """Página principal para carga de datos."""
    form = LoadDataForm()
    return render_template('data_processing/loading.html', form=form)


@data_processing_bp.route('/table-processing')
def table_processing():
    """Página principal para procesamiento de tablas."""
    recent_periods_form = CreateRecentPeriodsForm()
    base_subramos_form = CreateBaseSubramosForm()
    concepts_form = CreateFinancialConceptsForm()
    subramos_form = CreateSubramosForm()
    
    return render_template('data_processing/table_creation.html',
                         recent_periods_form=recent_periods_form,
                         base_subramos_form=base_subramos_form,
                         concepts_form=concepts_form,
                         subramos_form=subramos_form)


@data_processing_bp.route('/api/check-file-status', methods=['POST'])
def api_check_file_status():
    """API endpoint para verificar estado de archivos MDB y períodos en BD."""
    try:
        data = request.get_json()
        periodo_archivo = data.get('periodo_archivo')
        periodo_anterior = data.get('periodo_anterior')
        
        if not periodo_archivo:
            return jsonify({
                'success': False,
                'error': 'período_archivo es requerido'
            }), 400
        
        file_status = get_file_status(periodo_archivo, periodo_anterior)
        
        # Verificar si el período anterior existe en la base de datos
        if periodo_anterior:
            try:
                periods_in_db = list_periods()
                file_status['periodo_anterior_db']['exists_in_db'] = periodo_anterior in periods_in_db
                file_status['can_compare'] = file_status['archivo_actual']['exists'] and periodo_anterior in periods_in_db
            except Exception:
                file_status['periodo_anterior_db']['exists_in_db'] = False
                file_status['can_compare'] = False
        
        return jsonify({
            'success': True,
            'file_status': file_status
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error verificando archivos: {str(e)}'
        }), 400


@data_processing_bp.route('/api/list-mdb-files', methods=['GET'])
def api_list_mdb_files():
    """API endpoint para listar archivos MDB disponibles."""
    try:
        files = list_available_mdb_files()
        return jsonify({
            'success': True,
            'files': files
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error listando archivos: {str(e)}'
        }), 500


@data_processing_bp.route('/api/check-companies', methods=['POST'])
def api_check_companies():
    """API endpoint para verificar compañías."""
    try:
        data = request.get_json()
        periodo_archivo = data.get('periodo_archivo')
        periodo_anterior = data.get('periodo_anterior')
        
        log_capture = LogCapture()
        log_capture.start_capture()
        
        try:
            # Llamar función del módulo (siempre compara MDB con BD)
            check_companies_main(periodo_archivo, periodo_anterior)
            
            logs = log_capture.get_logs()
            log_capture.stop_capture()
            
            message = f'Verificación completada para período {periodo_archivo}'
            if periodo_anterior:
                message += f' comparando archivo MDB con base de datos (período {periodo_anterior})'
            
            return jsonify({
                'success': True,
                'logs': logs,
                'message': message
            })
            
        except Exception as e:
            log_capture.stop_capture()
            return jsonify({
                'success': False,
                'error': str(e),
                'logs': log_capture.get_logs()
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error en la solicitud: {str(e)}'
        }), 400


@data_processing_bp.route('/api/check-periods', methods=['POST'])
def api_check_periods():
    """API endpoint para listar períodos disponibles."""
    try:
        log_capture = LogCapture()
        log_capture.start_capture()
        
        try:
            # Obtener lista de períodos
            periods = list_periods()
            
            logs = log_capture.get_logs()
            log_capture.stop_capture()
            
            return jsonify({
                'success': True,
                'periods': periods,
                'logs': logs,
                'message': f'Encontrados {len(periods)} períodos en la base de datos'
            })
            
        except Exception as e:
            log_capture.stop_capture()
            return jsonify({
                'success': False,
                'error': str(e),
                'logs': log_capture.get_logs()
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error en la solicitud: {str(e)}'
        }), 400


@data_processing_bp.route('/api/upload-mdb', methods=['POST'])
def api_upload_mdb():
    """API endpoint para subir archivos MDB."""
    try:
        form = UploadMDBForm()
        
        if form.validate_on_submit():
            file = form.mdb_file.data
            filename = secure_filename(file.filename)
            
            # Verificar que el archivo tenga el formato correcto (YYYY-P.zip)
            if not filename.lower().endswith('.zip'):
                return jsonify({
                    'success': False,
                    'error': 'El archivo debe ser un ZIP'
                }), 400
            
            # Verificar formato del nombre
            name_without_ext = filename[:-4]  # Remover .zip
            if not name_without_ext.count('-') == 1:
                return jsonify({
                    'success': False,
                    'error': 'El archivo debe tener formato YYYY-P.zip (ej: 2025-1.zip)'
                }), 400
            
            try:
                year_str, quarter_str = name_without_ext.split('-')
                year = int(year_str)
                quarter = int(quarter_str)
                
                if year < 2020 or year > 2030 or quarter < 1 or quarter > 4:
                    raise ValueError("Fuera de rango")
                    
            except (ValueError, IndexError):
                return jsonify({
                    'success': False,
                    'error': 'Formato inválido. Use YYYY-P.zip donde YYYY es el año y P el trimestre (1-4)'
                }), 400
            
            # Guardar archivo
            upload_dir = get_mdb_files_directory()
            upload_dir.mkdir(exist_ok=True)
            
            file_path = upload_dir / filename
            
            # Verificar si el archivo ya existe
            if file_path.exists():
                return jsonify({
                    'success': False,
                    'error': f'El archivo {filename} ya existe. Elimínelo primero si desea reemplazarlo.'
                }), 400
            
            file.save(str(file_path))
            
            return jsonify({
                'success': True,
                'message': f'Archivo {filename} subido exitosamente',
                'filename': filename,
                'path': str(file_path)
            })
            
        else:
            errors = []
            for field, field_errors in form.errors.items():
                errors.extend(field_errors)
            
            return jsonify({
                'success': False,
                'error': 'Errores de validación: ' + ', '.join(errors)
            }), 400
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error subiendo archivo: {str(e)}'
        }), 500


@data_processing_bp.route('/api/load-data', methods=['POST'])
def api_load_data():
    """API endpoint para cargar datos."""
    try:
        data = request.get_json()
        periodo = data.get('periodo')
        
        log_capture = LogCapture()
        log_capture.start_capture()
        
        try:
            # Llamar función del módulo
            load_data_main(periodo)
            
            logs = log_capture.get_logs()
            log_capture.stop_capture()
            
            # Verificar si el período ya existía analizando los logs
            period_already_exists = any(
                'ya existe en la base de datos' in log 
                for log in logs if log.strip()
            )
            
            if period_already_exists:
                message = f'El período {periodo} ya existe en la base de datos'
                action_type = 'already_exists'
            else:
                message = f'Datos cargados exitosamente para período {periodo}'
                action_type = 'newly_loaded'
            
            return jsonify({
                'success': True,
                'logs': logs,
                'message': message,
                'action_type': action_type
            })
            
        except Exception as e:
            log_capture.stop_capture()
            return jsonify({
                'success': False,
                'error': str(e),
                'logs': log_capture.get_logs()
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error en la solicitud: {str(e)}'
        }), 400


@data_processing_bp.route('/api/create-recent-periods', methods=['POST'])
def api_create_recent_periods():
    """API endpoint para crear tabla de períodos recientes."""
    try:
        data = request.get_json()
        periodo_inicial = data.get('periodo_inicial')
        
        log_capture = LogCapture()
        log_capture.start_capture()
        
        try:
            # Llamar función del módulo
            create_recent_periods_table(periodo_inicial)
            
            logs = log_capture.get_logs()
            log_capture.stop_capture()
            
            return jsonify({
                'success': True,
                'logs': logs,
                'message': 'Tabla de períodos recientes creada exitosamente'
            })
            
        except Exception as e:
            log_capture.stop_capture()
            return jsonify({
                'success': False,
                'error': str(e),
                'logs': log_capture.get_logs()
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error en la solicitud: {str(e)}'
        }), 400


@data_processing_bp.route('/api/create-base-subramos', methods=['POST'])
def api_create_base_subramos():
    """API endpoint para crear tabla base de subramos."""
    try:
        data = request.get_json()
        periodo_inicial = data.get('periodo_inicial')
        
        log_capture = LogCapture()
        log_capture.start_capture()
        
        try:
            # Llamar función del módulo
            create_base_subramos_main(periodo_inicial)
            
            logs = log_capture.get_logs()
            log_capture.stop_capture()
            
            return jsonify({
                'success': True,
                'logs': logs,
                'message': 'Tabla base de subramos creada exitosamente'
            })
            
        except Exception as e:
            log_capture.stop_capture()
            return jsonify({
                'success': False,
                'error': str(e),
                'logs': log_capture.get_logs()
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error en la solicitud: {str(e)}'
        }), 400


@data_processing_bp.route('/api/create-concepts', methods=['POST'])
def api_create_concepts():
    """API endpoint para crear tabla de conceptos financieros."""
    try:
        log_capture = LogCapture()
        log_capture.start_capture()
        
        try:
            # Llamar función del módulo
            create_concepts_main()
            
            logs = log_capture.get_logs()
            log_capture.stop_capture()
            
            return jsonify({
                'success': True,
                'logs': logs,
                'message': 'Tabla de conceptos financieros creada exitosamente'
            })
            
        except Exception as e:
            log_capture.stop_capture()
            return jsonify({
                'success': False,
                'error': str(e),
                'logs': log_capture.get_logs()
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error en la solicitud: {str(e)}'
        }), 400


@data_processing_bp.route('/api/create-subramos', methods=['POST'])
def api_create_subramos():
    """API endpoint para crear tabla de subramos corregida."""
    try:
        data = request.get_json()
        periodo = data.get('periodo')
        testing_mode = data.get('testing_mode', False)
        
        log_capture = LogCapture()
        log_capture.start_capture()
        
        try:
            if testing_mode:
                # Modo testing: exportar datos para verificación
                export_testing_data(periodo)
                message = f'Archivo de testing creado para período {periodo}. Revisa modules/testing_data/'
            else:
                # Modo producción: crear tabla
                create_table_from_query(periodo)
                message = f'Tabla de subramos corregida creada para período {periodo}'
            
            logs = log_capture.get_logs()
            log_capture.stop_capture()
            
            return jsonify({
                'success': True,
                'logs': logs,
                'message': message,
                'testing_mode': testing_mode
            })
            
        except Exception as e:
            log_capture.stop_capture()
            return jsonify({
                'success': False,
                'error': str(e),
                'logs': log_capture.get_logs()
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error en la solicitud: {str(e)}'
        }), 400