import os
import logging
import platform
import sqlite3
import subprocess
import json
import sys
from io import StringIO
from pathlib import Path
from werkzeug.utils import secure_filename
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from app.forms.processing_forms import (
    CheckCompaniesForm, LoadDataForm, CreateRecentPeriodsForm,
    CreateBaseSubramosForm, CreateFinancialConceptsForm, CreateSubramosForm,
    CheckPeriodsForm, UploadMDBForm, ReportGenerationForm, ConceptoForm,
    ReloadPeriodForm
)

# Add project root to path for module imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from modules.check_cantidad_cias import main as check_companies_main, get_companies_from_file, get_companies_from_db
from modules.check_ultimos_periodos import print_periods_info, list_available_periods as list_periods
from modules.carga_base_principal import main as load_data_main
from utils.db_functions import list_ultimos_periodos
from modules.crea_tabla_ultimos_periodos import create_recent_periods_table
from modules.crea_tabla_subramos import main as create_base_subramos_main
from modules.crea_tabla_ramos import main as create_base_ramos_main
from modules.crea_tabla_otros_conceptos import main as create_concepts_main
from modules.crea_tabla_subramos_corregida import create_table_from_query, export_testing_data
from modules.crea_tabla_ramos_corregida import create_ramos_table_from_query, export_ramos_testing_data
from modules.crea_tabla_cias_corregida import create_table_from_query as create_cias_table_from_query
from modules.file_utils import check_mdb_file_exists, list_available_mdb_files, get_file_status
from modules.common import get_mdb_files_directory
from modules.compare_csv_reports import compare_all_csv_reports, generate_comparison_report
from modules.report_generation import (
    ReportGenerationFailure,
    ReportValidationError,
    generate_official_reports,
)
from modules.period_pipeline import (
    PipelineBusyError,
    PipelineExecutionError,
    pipeline_lock,
    run_period_pipeline,
    run_tables_pipeline,
)
from export_parquet.run_all_and_upload import (
    S3ExportError,
    get_latest_period,
    run_all_and_upload,
)
from modules.period_reload import (
    PeriodReloadError,
    cancel_staged_reload,
    confirm_staged_reload,
    get_period_database_stats,
    stage_reload_candidate,
)
from modules.shipment import prepare_shipment
from utils.user_messages import flash_user_error

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
    reload_form = ReloadPeriodForm()

    return render_template('data_processing/verification.html',
                         check_companies_form=check_companies_form,
                         check_periods_form=check_periods_form,
                         upload_form=upload_form,
                         reload_form=reload_form)


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


@data_processing_bp.route('/full-processing')
def full_processing():
    """Página independiente para procesar tablas y generar reportes."""
    return render_template('data_processing/full_processing.html')


@data_processing_bp.route('/api/process-full-period', methods=['POST'])
def api_process_full_period():
    """Run the complete dependency-ordered pipeline for a selected period."""
    data = request.get_json(silent=True) or {}
    periodo = data.get('periodo')
    database_path = os.getenv('DATABASE')
    if not periodo:
        return jsonify({'success': False, 'error': 'El período es requerido.'}), 400
    if not database_path:
        return jsonify({'success': False, 'error': 'La base de datos no está configurada.'}), 500

    try:
        result = run_period_pipeline(int(periodo), database_path, project_root)
        return jsonify({
            'success': True,
            'message': f'El período {periodo} quedó procesado y sus reportes fueron publicados.',
            **result,
        })
    except PipelineBusyError as error:
        return jsonify({'success': False, 'status': 'busy', 'error': str(error)}), 409
    except PipelineExecutionError as error:
        return jsonify({
            'success': False,
            'status': 'failed',
            'failed_stage': error.stage.key,
            'stages': error.statuses,
            'error': str(error),
        }), 500
    except (TypeError, ValueError) as error:
        return jsonify({'success': False, 'status': 'failed', 'error': str(error)}), 400
    except Exception:
        logging.exception('Error inesperado procesando el período %s', periodo)
        return jsonify({
            'success': False,
            'status': 'failed',
            'error': 'El período no pudo procesarse completamente.',
        }), 500


@data_processing_bp.route('/api/generate-all-tables', methods=['POST'])
def api_generate_all_tables():
    """Generate every required table in dependency order for one period."""
    data = request.get_json(silent=True) or {}
    periodo = data.get('periodo')
    database_path = os.getenv('DATABASE')

    if not periodo:
        return jsonify({'success': False, 'error': 'El período es requerido.'}), 400
    if not database_path:
        return jsonify({'success': False, 'error': 'La base de datos no está configurada.'}), 500

    try:
        result = run_tables_pipeline(int(periodo), database_path, project_root)
        return jsonify({
            'success': True,
            'message': f'Todas las tablas quedaron generadas para el período {periodo}.',
            **result,
        })
    except PipelineBusyError as error:
        return jsonify({'success': False, 'status': 'busy', 'error': str(error)}), 409
    except PipelineExecutionError as error:
        return jsonify({
            'success': False,
            'status': 'failed',
            'failed_stage': error.stage.key,
            'stages': error.statuses,
            'error': str(error),
        }), 500
    except (TypeError, ValueError) as error:
        return jsonify({'success': False, 'status': 'failed', 'error': str(error)}), 400
    except Exception:
        logging.exception('Error inesperado generando tablas para %s', periodo)
        return jsonify({
            'success': False,
            'status': 'failed',
            'error': 'No se pudieron generar todas las tablas.',
        }), 500


@data_processing_bp.route('/api/upload-parquet-to-s3', methods=['POST'])
def api_upload_parquet_to_s3():
    """Regenerate historical Parquet files and upload them using the latest period."""
    database_path = os.getenv('DATABASE')
    if not database_path:
        return jsonify({'success': False, 'error': 'La base de datos no está configurada.'}), 500

    try:
        latest_period = get_latest_period(database_path)
        with pipeline_lock(database_path, latest_period):
            result = run_all_and_upload(
                latest_period,
                database_path=database_path,
            )
        return jsonify({
            'success': True,
            'message': (
                f'Se generaron y subieron {result["uploaded_count"]} archivos Parquet '
                f'hasta el período {latest_period}.'
            ),
            **result,
        })
    except PipelineBusyError as error:
        return jsonify({'success': False, 'status': 'busy', 'error': str(error)}), 409
    except ValueError as error:
        return jsonify({'success': False, 'status': 'failed', 'error': str(error)}), 400
    except S3ExportError as error:
        return jsonify({'success': False, 'status': 'failed', 'error': str(error)}), 500
    except Exception:
        logging.exception('Error inesperado generando y subiendo Parquet a S3')
        return jsonify({
            'success': False,
            'status': 'failed',
            'error': 'No se pudo completar la publicación en S3.',
        }), 500


@data_processing_bp.route('/api/prepare-shipment', methods=['POST'])
def api_prepare_shipment():
    """Copia y renombra los Excel finales al directorio de envío configurado."""
    try:
        data = request.get_json() or {}
        periodo = str(data.get('periodo', '')).strip()
        if not periodo:
            return jsonify({
                'success': False,
                'status': 'failed',
                'error': 'El período es requerido.',
            }), 400

        result = prepare_shipment(periodo)
        copied = result['copied']
        skipped = result['skipped']
        failed = result['failed']
        destination = result['destination']

        if failed and copied:
            status = 'partial'
            success = True  # algunos se copiaron, reportar como éxito parcial
        elif failed and not copied:
            status = 'failed'
            success = False
        else:
            status = 'success'
            success = True

        return jsonify({
            'success': success,
            'status': status,
            'copied': copied,
            'skipped': skipped,
            'failed': failed,
            'destination': destination,
            'message': (
                f'Se copiaron {len(copied)} archivos a {destination}'
                + (f' ({len(skipped)} omitidos, {len(failed)} con error)'
                   if (skipped or failed) else '.')
            ),
        })
    except (ValueError, FileNotFoundError) as error:
        return jsonify({
            'success': False,
            'status': 'failed',
            'error': str(error),
        }), 400
    except Exception:
        logging.exception('Error preparando envío')
        return jsonify({
            'success': False,
            'status': 'failed',
            'error': 'No se pudo preparar el envío.',
        }), 500


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
                import datetime as _dt
                year_str, quarter_str = name_without_ext.split('-')
                year = int(year_str)
                quarter = int(quarter_str)
                _current_year = _dt.datetime.now().year

                if year < 2020 or year > _current_year + 5 or quarter < 1 or quarter > 4:
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
            mdb_path = upload_dir / f'{name_without_ext}.mdb'
            temporary_path = upload_dir / f'.{filename}.uploading'
            replaced_existing = file_path.exists()

            # Guardar primero en un archivo temporal para no perder el ZIP
            # anterior si la nueva carga se interrumpe.
            try:
                file.save(str(temporary_path))
                temporary_path.replace(file_path)

                # El MDB se vuelve a extraer desde el ZIP al validar/cargar.
                # Eliminar el anterior evita usar accidentalmente datos viejos.
                if mdb_path.exists():
                    mdb_path.unlink()
            except Exception:
                if temporary_path.exists():
                    temporary_path.unlink()
                raise

            action = 'reemplazado' if replaced_existing else 'subido'
            
            return jsonify({
                'success': True,
                'message': f'Archivo {filename} {action} exitosamente',
                'filename': filename,
                'path': str(file_path),
                'replaced': replaced_existing
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
        periodo_referencia = data.get('periodo') if data else None

        log_capture = LogCapture()
        log_capture.start_capture()

        try:
            # Llamar función del módulo
            create_recent_periods_table(periodo_referencia)

            logs = log_capture.get_logs()
            log_capture.stop_capture()

            if periodo_referencia:
                message = f'Tabla de períodos recientes creada para período de referencia {periodo_referencia}'
            else:
                message = 'Tabla de períodos recientes creada (usando automáticamente el año actual)'

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


@data_processing_bp.route('/api/create-base-subramos', methods=['POST'])
def api_create_base_subramos():
    """API endpoint para crear tablas base de subramos y ramos."""
    try:
        data = request.get_json()
        periodo_referencia = data.get('periodo') if data else None

        log_capture = LogCapture()
        log_capture.start_capture()

        try:
            # Llamar función del módulo subramos
            create_base_subramos_main(periodo_referencia)

            # Llamar función del módulo ramos
            create_base_ramos_main(periodo_referencia)

            logs = log_capture.get_logs()
            log_capture.stop_capture()

            if periodo_referencia:
                message = f'Tablas base de subramos y ramos creadas para período de referencia {periodo_referencia}'
            else:
                message = 'Tablas base de subramos y ramos creadas (usando automáticamente el año actual)'

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


@data_processing_bp.route('/api/create-concepts', methods=['POST'])
def api_create_concepts():
    """API endpoint para crear tabla de conceptos financieros."""
    try:
        data = request.get_json()
        periodo_referencia = data.get('periodo') if data else None

        log_capture = LogCapture()
        log_capture.start_capture()

        try:
            # Llamar función del módulo
            create_concepts_main(periodo_referencia)

            logs = log_capture.get_logs()
            log_capture.stop_capture()

            if periodo_referencia:
                message = f'Tabla de conceptos financieros creada para período {periodo_referencia}'
            else:
                message = 'Tabla de conceptos financieros creada (usando MAX(periodo) automáticamente)'

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


@data_processing_bp.route('/api/create-subramos', methods=['POST'])
def api_create_subramos():
    """API endpoint para crear tablas de subramos y ramos corregidas."""
    try:
        data = request.get_json()
        periodo = data.get('periodo')
        testing_mode = data.get('testing_mode', False)
        
        log_capture = LogCapture()
        log_capture.start_capture()
        
        try:
            if testing_mode:
                # Modo testing: exportar datos para verificación de ambas tablas
                export_testing_data(periodo)
                export_ramos_testing_data(periodo)
                message = f'Archivos de testing creados para período {periodo}. Revisa modules/testing_data/'
            else:
                # Modo producción: crear ambas tablas
                create_table_from_query(periodo)  # Tabla de subramos corregida
                create_ramos_table_from_query(periodo)  # Tabla de ramos corregida
                create_cias_table_from_query(periodo)  # Tabla de compañías corregida
                message = f'Tablas de subramos, ramos y compañías corregidas creadas para período {periodo}'
            
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


@data_processing_bp.route('/report-generation')
def report_generation():
    """Página para generar todos los reportes CSV y Excel."""
    form = ReportGenerationForm()
    return render_template('data_processing/report_generation.html', form=form)


@data_processing_bp.route('/api/generate-all-reports', methods=['POST'])
def api_generate_all_reports():
    """Genera, valida y publica la salida CSV y Excel oficial de un período."""
    data = request.get_json(silent=True) or {}
    periodo = data.get('periodo')

    if not periodo:
        return jsonify({'success': False, 'error': 'El período es requerido'}), 400

    try:
        periodo_int = int(periodo)
        database_path = os.getenv('DATABASE')
        if not database_path:
            raise ReportValidationError('La base de datos no está configurada.')
        result = generate_official_reports(project_root, database_path, periodo_int)
    except (TypeError, ValueError, ReportValidationError) as error:
        return jsonify({
            'success': False,
            'status': 'failed',
            'error': str(error),
        }), 400
    except ReportGenerationFailure as error:
        payload = {
            'success': False,
            'status': error.status,
            'error': str(error),
            'logs': error.logs,
        }
        if error.failed_csv_reports:
            payload['failed_csv_reports'] = error.failed_csv_reports
        if error.failed_excel_reports:
            payload['failed_excel_reports'] = error.failed_excel_reports
        return jsonify(payload), 500
    except Exception:
        logging.exception('Error inesperado generando reportes para %s', periodo)
        return jsonify({
            'success': False,
            'status': 'failed',
            'error': 'La generación no pudo completarse. La salida oficial no fue modificada.',
        }), 500

    return jsonify({'success': True, **result})


@data_processing_bp.route('/api/compare-csv-reports', methods=['POST'])
def api_compare_csv_reports():
    """API endpoint para comparar archivos CSV entre dos períodos."""
    try:
        data = request.get_json()
        periodo_actual = data.get('periodo_actual')
        periodo_anterior = data.get('periodo_anterior')

        if not periodo_actual or not periodo_anterior:
            return jsonify({
                'success': False,
                'error': 'Se requieren ambos períodos (actual y anterior)'
            }), 400

        # Validar formato de períodos
        for periodo in [periodo_actual, periodo_anterior]:
            if len(str(periodo)) != 6:
                return jsonify({
                    'success': False,
                    'error': 'Los períodos deben tener formato YYYYPP (6 dígitos)'
                }), 400

        logs = []

        try:
            # Ejecutar comparación
            logs.append(f"Comparando período {periodo_actual} vs {periodo_anterior}...")

            # Obtener directorio base del proyecto
            base_dir = os.path.join(project_root, "ending_files")

            results = compare_all_csv_reports(periodo_actual, periodo_anterior, base_dir)

            logs.append(f"Archivos comparados: {results['total_compared']}")

            # Generar reporte TXT
            output_path = os.path.join(base_dir, f"csv_comparison_{periodo_actual}_{periodo_anterior}.txt")
            generate_comparison_report(results, Path(output_path))

            logs.append(f"Reporte guardado en: {output_path}")

            # Preparar resumen para respuesta
            summary = {
                'total_compared': results['total_compared'],
                'only_in_actual': results['only_in_actual'],
                'only_in_previous': results['only_in_previous'],
                'files_with_differences': sum(1 for c in results['comparisons']
                                             if c['count_new'] > 0 or c['count_missing'] > 0)
            }

            return jsonify({
                'success': True,
                'logs': logs,
                'message': f'Comparación completada. Reporte guardado en ending_files/',
                'summary': summary,
                'report_path': output_path,
                'results': results
            })

        except FileNotFoundError as e:
            return jsonify({
                'success': False,
                'error': str(e),
                'logs': logs
            }), 404

        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'Error durante la comparación: {str(e)}',
                'logs': logs
            }), 500

    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error en la solicitud: {str(e)}'
        }), 400


# Helper functions for conceptos management
def get_dropdown_choices():
    """Get unique values from parametros_reportes for dropdown choices."""
    from utils.db_manager import db_manager
    
    try:
        with db_manager.get_connection() as conn:
            # Get unique reportes
            reportes_query = "SELECT DISTINCT reporte FROM parametros_reportes ORDER BY reporte"
            reportes = [row[0] for row in conn.execute(reportes_query).fetchall()]
            reporte_choices = [(r, r) for r in reportes]
            
            # Get unique referencias
            referencias_query = "SELECT DISTINCT referencia FROM parametros_reportes ORDER BY referencia"
            referencias = [row[0] for row in conn.execute(referencias_query).fetchall()]
            referencia_choices = [(r, r) for r in referencias]
            
            return reporte_choices, referencia_choices
    except Exception as e:
        logging.error(f"Error getting dropdown choices: {e}")
        return [], []


# Conceptos CRUD Routes
@data_processing_bp.route('/conceptos')
def list_conceptos():
    """Lista todos los conceptos de reportes."""
    from utils.db_manager import db_manager
    
    try:
        with db_manager.get_connection() as conn:
            query = """
                SELECT id, reporte, referencia, concepto, es_subramo 
                FROM conceptos_reportes 
                ORDER BY reporte, referencia, concepto
            """
            conceptos = conn.execute(query).fetchall()
            
        return render_template('data_processing/conceptos/list.html', conceptos=conceptos)
    
    except Exception as e:
        flash_user_error(
            "No se pudieron cargar los conceptos.",
            technical=e,
        )
        return redirect(url_for('dashboard'))


@data_processing_bp.route('/conceptos/add', methods=['GET', 'POST'])
def add_concepto():
    """Agregar nuevo concepto."""
    from utils.db_manager import db_manager
    
    form = ConceptoForm()
    
    # Populate dropdown choices
    reporte_choices, referencia_choices = get_dropdown_choices()
    form.reporte.choices = reporte_choices
    form.referencia.choices = referencia_choices
    
    if form.validate_on_submit():
        try:
            with db_manager.get_connection() as conn:
                # Check if concept already exists
                check_query = """
                    SELECT id FROM conceptos_reportes 
                    WHERE reporte = ? AND referencia = ? AND concepto = ?
                """
                existing = conn.execute(check_query, (
                    form.reporte.data, 
                    form.referencia.data, 
                    form.concepto.data
                )).fetchone()
                
                if existing:
                    flash('Ya existe un concepto con esa combinación de reporte, referencia y concepto.', 'error')
                    return render_template('data_processing/conceptos/add.html', form=form)
                
                # Insert new concept
                insert_query = """
                    INSERT INTO conceptos_reportes (reporte, referencia, concepto, es_subramo)
                    VALUES (?, ?, ?, ?)
                """
                conn.execute(insert_query, (
                    form.reporte.data,
                    form.referencia.data, 
                    form.concepto.data,
                    form.es_subramo.data
                ))
                conn.commit()
            flash('Concepto agregado exitosamente.', 'success')
            return redirect(url_for('data_processing.list_conceptos'))
            
        except Exception as e:
            flash_user_error(
                "No se pudo agregar el concepto.",
                technical=e,
            )
    
    return render_template('data_processing/conceptos/add.html', form=form)


@data_processing_bp.route('/conceptos/edit/<int:concepto_id>', methods=['GET', 'POST'])
def edit_concepto(concepto_id):
    """Editar concepto existente."""
    from utils.db_manager import db_manager
    
    form = ConceptoForm()
    
    # Populate dropdown choices
    reporte_choices, referencia_choices = get_dropdown_choices()
    form.reporte.choices = reporte_choices
    form.referencia.choices = referencia_choices
    
    try:
        with db_manager.get_connection() as conn:
            # Get current concept
            query = """
                SELECT id, reporte, referencia, concepto, es_subramo 
                FROM conceptos_reportes WHERE id = ?
            """
            concepto = conn.execute(query, (concepto_id,)).fetchone()
            
            if not concepto:
                flash('Concepto no encontrado.', 'error')
                return redirect(url_for('data_processing.list_conceptos'))
            
            if form.validate_on_submit():
                # Check if updated concept already exists (excluding current)
                check_query = """
                    SELECT id FROM conceptos_reportes 
                    WHERE reporte = ? AND referencia = ? AND concepto = ? AND id != ?
                """
                existing = conn.execute(check_query, (
                    form.reporte.data, 
                    form.referencia.data, 
                    form.concepto.data,
                    concepto_id
                )).fetchone()
                
                if existing:
                    flash('Ya existe un concepto con esa combinación de reporte, referencia y concepto.', 'error')
                    return render_template('data_processing/conceptos/edit.html', form=form, concepto_id=concepto_id)
                
                # Update concept
                update_query = """
                    UPDATE conceptos_reportes 
                    SET reporte = ?, referencia = ?, concepto = ?, es_subramo = ?
                    WHERE id = ?
                """
                conn.execute(update_query, (
                    form.reporte.data,
                    form.referencia.data,
                    form.concepto.data,
                    form.es_subramo.data,
                    concepto_id
                ))
                conn.commit()
                flash('Concepto actualizado exitosamente.', 'success')
                return redirect(url_for('data_processing.list_conceptos'))
            
            # Pre-fill form with current values
            if request.method == 'GET':
                form.reporte.data = concepto[1]
                form.referencia.data = concepto[2]
                form.concepto.data = concepto[3]
                form.es_subramo.data = bool(concepto[4])
    
    except Exception as e:
        flash_user_error(
            "No se pudo cargar o actualizar el concepto.",
            technical=e,
        )
        return redirect(url_for('data_processing.list_conceptos'))
    
    return render_template('data_processing/conceptos/edit.html', form=form, concepto_id=concepto_id)


@data_processing_bp.route('/conceptos/delete/<int:concepto_id>', methods=['POST'])
def delete_concepto(concepto_id):
    """Eliminar concepto."""
    from utils.db_manager import db_manager
    
    try:
        with db_manager.get_connection() as conn:
            # Check if concept exists
            check_query = "SELECT id FROM conceptos_reportes WHERE id = ?"
            existing = conn.execute(check_query, (concepto_id,)).fetchone()
            
            if not existing:
                flash('Concepto no encontrado.', 'error')
                return redirect(url_for('data_processing.list_conceptos'))
            
            # Delete concept
            delete_query = "DELETE FROM conceptos_reportes WHERE id = ?"
            conn.execute(delete_query, (concepto_id,))
            conn.commit()
        flash('Concepto eliminado exitosamente.', 'success')
    
    except Exception as e:
        flash_user_error(
            "No se pudo eliminar el concepto.",
            technical=e,
        )

    return redirect(url_for('data_processing.list_conceptos'))


@data_processing_bp.route('/api/upload-and-compare-period', methods=['POST'])
def api_upload_and_compare_period():
    """Valida un ZIP en staging para un período existente y compara compañías."""
    try:
        form = ReloadPeriodForm()

        if not form.validate_on_submit():
            errors = [e for field_errors in form.errors.values() for e in field_errors]
            return jsonify({'success': False, 'error': 'Errores de validación: ' + ', '.join(errors)}), 400

        file = form.mdb_file.data
        filename = secure_filename(file.filename)

        if not filename.lower().endswith('.zip'):
            return jsonify({'success': False, 'error': 'El archivo debe ser un ZIP'}), 400

        name_without_ext = filename[:-4]
        if name_without_ext.count('-') != 1:
            return jsonify({'success': False, 'error': 'El archivo debe tener formato YYYY-P.zip (ej: 2025-1.zip)'}), 400

        try:
            import datetime as _dt2
            year_str, quarter_str = name_without_ext.split('-')
            year = int(year_str)
            quarter = int(quarter_str)
            _current_year2 = _dt2.datetime.now().year
            if year < 2020 or year > _current_year2 + 5 or quarter < 1 or quarter > 4:
                raise ValueError("Fuera de rango")
            periodo = int(f"{year}{quarter:02d}")
        except (ValueError, IndexError):
            return jsonify({'success': False, 'error': 'Formato inválido. Use YYYY-P.zip donde YYYY es el año y P el trimestre (1-4)'}), 400

        # Verificar que el período ya exista en la base de datos
        from dotenv import load_dotenv as _load_dotenv
        _load_dotenv()
        database_path = os.getenv('DATABASE')
        if not database_path:
            raise PeriodReloadError('La base de datos no está configurada.')
        database_stats = get_period_database_stats(database_path, periodo)
        if database_stats['row_count'] == 0:
            return jsonify({
                'success': False,
                'error': f'El período {periodo} no existe en la base de datos. Use la carga normal para períodos nuevos.'
            }), 400

        # El archivo vigente no se toca hasta que el usuario confirme.
        upload_dir = get_mdb_files_directory()
        candidate = stage_reload_candidate(file, periodo, filename, upload_dir)

        # Comparar compañías
        companies_db, names_db = get_companies_from_db(periodo)

        new_companies = sorted(candidate.company_codes - companies_db)
        missing_companies = sorted(companies_db - candidate.company_codes)

        new_list = [
            {'cod': c, 'nombre': candidate.company_names.get(c, f'Sin nombre ({c})')}
            for c in new_companies
        ]
        missing_list = [{'cod': c, 'nombre': names_db.get(c, f'Sin nombre ({c})')} for c in missing_companies]

        return jsonify({
            'success': True,
            'status': 'pending_confirmation',
            'periodo': periodo,
            'filename': filename,
            'reload_token': candidate.token,
            'companies_in_db': len(companies_db),
            'companies_in_file': len(candidate.company_codes),
            'rows_in_file': candidate.row_count,
            'new_companies': new_list,
            'missing_companies': missing_list,
            'message': f'Comparación lista para período {periodo}: {len(companies_db)} compañías en BD, {len(candidate.company_codes)} en archivo nuevo'
        })

    except PeriodReloadError as e:
        return jsonify({'success': False, 'status': 'rejected', 'error': str(e)}), 400
    except Exception as e:
        logging.exception('Error preparando la recarga del período')
        return jsonify({'success': False, 'error': f'Error al comparar: {str(e)}'}), 500


@data_processing_bp.route('/api/confirm-reload-period', methods=['POST'])
def api_confirm_reload_period():
    """Confirma la sustitución transaccional del período y de su ZIP fuente."""
    try:
        data = request.get_json(silent=True) or {}
        periodo = data.get('periodo')
        reload_token = data.get('reload_token')

        if not periodo or not reload_token:
            return jsonify({
                'success': False,
                'status': 'failed',
                'error': 'El período y la recarga pendiente son requeridos.',
            }), 400

        from dotenv import load_dotenv as _load_dotenv
        _load_dotenv()
        database_path = os.getenv('DATABASE')
        if not database_path:
            return jsonify({
                'success': False,
                'status': 'failed',
                'error': 'La base de datos no está configurada.',
            }), 500

        log_capture = LogCapture()
        log_capture.start_capture()

        try:
            result = confirm_staged_reload(
                reload_token,
                int(periodo),
                get_mdb_files_directory(),
                database_path,
            )
            logging.info(
                'Período %s reemplazado: %s filas anteriores, %s filas nuevas',
                periodo,
                result['old_rows'],
                result['new_rows'],
            )
            logs = log_capture.get_logs()
            log_capture.stop_capture()

            return jsonify({
                'success': True,
                'status': 'confirmed',
                'logs': logs,
                **result,
                'message': (
                    f'Período {periodo} recargado correctamente: '
                    f'{result["new_rows"]:,} filas y {result["new_companies"]:,} compañías. '
                    'Las tablas derivadas afectadas quedaron invalidadas y deben regenerarse.'
                ),
            })

        except Exception as e:
            logs = log_capture.get_logs()
            log_capture.stop_capture()
            logging.exception('Recarga revertida para el período %s', periodo)
            return jsonify({
                'success': False,
                'status': 'reverted',
                'error': 'La recarga falló y se restauraron los datos y el archivo anteriores.',
                'logs': logs,
            }), 500

    except Exception as e:
        return jsonify({'success': False, 'error': f'Error en la solicitud: {str(e)}'}), 400


@data_processing_bp.route('/api/cancel-reload-period', methods=['POST'])
def api_cancel_reload_period():
    """Descarta el ZIP pendiente sin modificar el archivo ni los datos vigentes."""
    data = request.get_json(silent=True) or {}
    periodo = data.get('periodo')
    reload_token = data.get('reload_token')
    if not periodo or not reload_token:
        return jsonify({
            'success': False,
            'status': 'failed',
            'error': 'El período y la recarga pendiente son requeridos.',
        }), 400
    try:
        cancel_staged_reload(
            reload_token,
            int(periodo),
            get_mdb_files_directory(),
        )
        return jsonify({
            'success': True,
            'status': 'cancelled',
            'message': f'Recarga del período {periodo} cancelada. No se modificaron datos ni archivos.',
        })
    except PeriodReloadError as error:
        return jsonify({
            'success': False,
            'status': 'failed',
            'error': str(error),
        }), 400


@data_processing_bp.route('/api/open-folder', methods=['POST'])
def api_open_folder():
    """Abre una carpeta de salida del sistema en el explorador del SO.

    Phase 4 (lean) — item 8. La ruta debe estar dentro de uno de los
    directorios raíz permitidos (``excel_final_files/``, ``ending_files/``
    o el directorio de envío configurado en ``modules.shipment``).
    Cualquier ruta fuera de esa lista es rechazada con 403 para evitar
    acceso arbitrario al sistema de archivos local.
    """
    from modules.shipment import SHIPMENT_BASE_DIR

    data = request.get_json(silent=True) or {}
    raw_path = (data.get('path') or '').strip()
    if not raw_path:
        return jsonify({
            'success': False,
            'error': 'La ruta es requerida.',
        }), 400

    try:
        requested = Path(raw_path).expanduser().resolve()
    except (OSError, RuntimeError):
        return jsonify({
            'success': False,
            'error': 'La ruta no es válida.',
        }), 400

    allowed_roots = (
        Path(project_root) / 'excel_final_files',
        Path(project_root) / 'ending_files',
        SHIPMENT_BASE_DIR,
    )
    is_allowed = False
    for root in allowed_roots:
        try:
            requested.relative_to(root.resolve())
            is_allowed = True
            break
        except ValueError:
            continue

    if not is_allowed:
        return jsonify({
            'success': False,
            'error': 'La ruta indicada no está dentro de los directorios permitidos.',
        }), 403

    if not requested.exists() or not requested.is_dir():
        return jsonify({
            'success': False,
            'error': 'La ruta no existe o no es un directorio.',
        }), 404

    system = platform.system()
    try:
        if system == 'Darwin':
            subprocess.Popen(['open', str(requested)])
        elif system == 'Windows':
            subprocess.Popen(['explorer', str(requested)])
        else:
            subprocess.Popen(['xdg-open', str(requested)])
    except (OSError, FileNotFoundError):
        logging.exception('Error abriendo carpeta %s', requested)
        return jsonify({
            'success': False,
            'error': 'No se pudo abrir la carpeta en el sistema operativo.',
        }), 500

    return jsonify({
        'success': True,
        'message': f'Carpeta abierta: {requested}',
    })
