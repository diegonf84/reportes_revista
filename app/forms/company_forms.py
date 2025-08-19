"""
Simple form for company management
"""

from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, SubmitField, HiddenField, IntegerField
from wtforms.validators import DataRequired, Length, NumberRange

class CompanyForm(FlaskForm):
    """Form for adding/editing companies"""
    cod_cia = IntegerField(
        'Código de Compañía', 
        validators=[
            DataRequired(message='El código es requerido'),
            NumberRange(min=1, max=9999, message='El código debe estar entre 1 y 9999')
        ],
        render_kw={
            'placeholder': 'Ej: 829, 1, 541',
            'class': 'form-control'
        }
    )
    
    nombre_corto = StringField(
        'Nombre Corto',
        validators=[
            DataRequired(message='El nombre corto es requerido'),
            Length(max=100, message='El nombre corto no puede exceder 100 caracteres')
        ],
        render_kw={
            'placeholder': 'Nombre corto de la compañía',
            'class': 'form-control'
        }
    )
    
    tipo_cia = SelectField(
        'Tipo de Compañía',
        choices=[
            ('', 'Seleccione un tipo...'),
            ('Generales', 'Generales'),
            ('Vida', 'Vida'), 
            ('Retiro', 'Retiro'),
            ('ART', 'ART'),
            ('M.T.P.P.', 'M.T.P.P.')
        ],
        validators=[DataRequired(message='Debe seleccionar un tipo de compañía')],
        render_kw={'class': 'form-select'}
    )
    
    # Hidden field for edit mode
    original_cod_cia = HiddenField()
    
    submit = SubmitField('Guardar', render_kw={'class': 'btn btn-primary'})