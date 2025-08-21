from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import IntegerField, BooleanField, SubmitField, SelectField
from wtforms.validators import DataRequired, NumberRange, Optional, ValidationError
import datetime


def validate_period_format(form, field):
    """
    Valida formato de período YYYYPP donde PP debe ser 01-04.
    """
    if field.data is not None:
        period_str = str(field.data)
        if len(period_str) != 6:
            raise ValidationError('El período debe tener 6 dígitos (YYYYPP)')
        
        year = int(period_str[:4])
        quarter = int(period_str[4:])
        
        current_year = datetime.datetime.now().year
        if year < 2020 or year > current_year + 5:
            raise ValidationError(f'Año debe estar entre 2020 y {current_year + 5}')
        
        if quarter < 1 or quarter > 4:
            raise ValidationError('Trimestre debe ser 01, 02, 03 o 04')


class CheckCompaniesForm(FlaskForm):
    """Formulario para verificar cantidad de compañías."""
    periodo_archivo = IntegerField(
        'Período del Archivo', 
        validators=[DataRequired(), validate_period_format],
        render_kw={
            'placeholder': '202501',
            'class': 'form-control',
            'title': 'Formato: YYYYPP (ej: 202501 para Marzo 2025)'
        }
    )
    
    periodo_anterior = IntegerField(
        'Período Anterior (Opcional)', 
        validators=[Optional(), validate_period_format],
        render_kw={
            'placeholder': '202404',
            'class': 'form-control',
            'title': 'Período anterior en la base de datos para comparación (opcional)'
        }
    )
    
    submit = SubmitField('Verificar Compañías', render_kw={'class': 'btn btn-primary'})


class LoadDataForm(FlaskForm):
    """Formulario para cargar datos desde archivo MDB."""
    periodo = IntegerField(
        'Período a Cargar', 
        validators=[DataRequired(), validate_period_format],
        render_kw={
            'placeholder': '202501',
            'class': 'form-control',
            'title': 'Período a cargar desde archivo MDB'
        }
    )
    
    submit = SubmitField('Cargar Datos', render_kw={'class': 'btn btn-success'})


class CreateRecentPeriodsForm(FlaskForm):
    """Formulario para crear tabla de períodos recientes."""
    periodo_inicial = IntegerField(
        'Período Inicial (Opcional)', 
        validators=[Optional(), validate_period_format],
        render_kw={
            'placeholder': '202301',
            'class': 'form-control',
            'title': 'Período inicial desde el cual filtrar (opcional, por defecto últimos 2 años)'
        }
    )
    
    submit = SubmitField('Crear Tabla Períodos', render_kw={'class': 'btn btn-info'})


class CreateBaseSubramosForm(FlaskForm):
    """Formulario para crear tabla base de subramos."""
    periodo_inicial = IntegerField(
        'Período Inicial (Opcional)', 
        validators=[Optional(), validate_period_format],
        render_kw={
            'placeholder': '202301',
            'class': 'form-control',
            'title': 'Período inicial desde el cual filtrar (opcional, por defecto últimos 2 años)'
        }
    )
    
    submit = SubmitField('Crear Tabla Base Subramos', render_kw={'class': 'btn btn-info'})


class CreateFinancialConceptsForm(FlaskForm):
    """Formulario para crear tabla de conceptos financieros."""
    submit = SubmitField('Crear Tabla Conceptos', render_kw={'class': 'btn btn-info'})


class CreateSubramosForm(FlaskForm):
    """Formulario para crear tabla de subramos corregida."""
    periodo = IntegerField(
        'Período', 
        validators=[DataRequired(), validate_period_format],
        render_kw={
            'placeholder': '202501',
            'class': 'form-control',
            'title': 'Período para procesar subramos corregidos'
        }
    )
    
    testing_mode = BooleanField(
        'Modo Testing', 
        render_kw={
            'class': 'form-check-input',
            'title': 'Generar archivo CSV para verificar cálculos antes de ejecutar'
        }
    )
    
    submit = SubmitField('Crear Tabla Subramos', render_kw={'class': 'btn btn-info'})


class CheckPeriodsForm(FlaskForm):
    """Formulario simple para listar períodos disponibles."""
    submit = SubmitField('Listar Períodos', render_kw={'class': 'btn btn-secondary'})


class UploadMDBForm(FlaskForm):
    """Formulario para subir archivos MDB."""
    mdb_file = FileField(
        'Archivo MDB',
        validators=[
            FileRequired('Selecciona un archivo'),
            FileAllowed(['zip'], 'Solo se permiten archivos ZIP')
        ],
        render_kw={
            'class': 'form-control',
            'accept': '.zip'
        }
    )
    
    submit = SubmitField('Subir Archivo', render_kw={'class': 'btn btn-success'})


class ReportGenerationForm(FlaskForm):
    """Formulario para generar todos los reportes CSV y Excel."""
    periodo = IntegerField(
        'Período del Reporte', 
        validators=[DataRequired(), validate_period_format],
        render_kw={
            'placeholder': '202502',
            'class': 'form-control',
            'title': 'Período para generar todos los reportes (formato YYYYPP)'
        }
    )
    
    submit = SubmitField('Generar Todos los Reportes', render_kw={'class': 'btn btn-success btn-lg'})