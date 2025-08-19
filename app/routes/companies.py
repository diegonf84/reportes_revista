"""
Simple routes for company management - CRUD only
Manages datos_companias table with fields: cod_cia (numeric), nombre_corto (text), tipo_cia (text), fecha (timestamp)
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from flask import Blueprint, render_template, request, redirect, url_for, flash
import sqlite3
import logging

from modules.common import setup_logging
from forms.company_forms import CompanyForm

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Create blueprint
companies_bp = Blueprint('companies', __name__, url_prefix='/companies')

# Valid company types
VALID_COMPANY_TYPES = ['Generales', 'Vida', 'Retiro', 'ART', 'M.T.P.P.']

def get_database_path():
    """Get database path from environment"""
    from dotenv import load_dotenv
    load_dotenv()
    return os.getenv('DATABASE')

def get_all_companies():
    """Get all companies from database"""
    database_path = get_database_path()
    if not database_path or not os.path.exists(database_path):
        return []
    
    try:
        with sqlite3.connect(database_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT cod_cia, nombre_corto, tipo_cia, fecha 
                FROM datos_companias 
                ORDER BY cod_cia
            """)
            return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        logger.error(f"Error getting companies: {e}")
        return []

def get_company_by_code(cod_cia):
    """Get single company by code"""
    database_path = get_database_path()
    if not database_path or not os.path.exists(database_path):
        return None
    
    try:
        with sqlite3.connect(database_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT cod_cia, nombre_corto, tipo_cia, fecha 
                FROM datos_companias 
                WHERE cod_cia = ?
            """, (cod_cia,))
            row = cursor.fetchone()
            return dict(row) if row else None
    except Exception as e:
        logger.error(f"Error getting company {cod_cia}: {e}")
        return None

def save_company(cod_cia, nombre_corto, tipo_cia, original_cod_cia=None):
    """Save or update company"""
    database_path = get_database_path()
    if not database_path:
        raise ValueError("Database path not configured")
    
    if tipo_cia not in VALID_COMPANY_TYPES:
        raise ValueError(f"Tipo de compañía inválido")
    
    try:
        with sqlite3.connect(database_path) as conn:
            if original_cod_cia and original_cod_cia != cod_cia:
                # Update with code change
                conn.execute("""
                    UPDATE datos_companias 
                    SET cod_cia = ?, nombre_corto = ?, tipo_cia = ?
                    WHERE cod_cia = ?
                """, (cod_cia, nombre_corto, tipo_cia, original_cod_cia))
            elif original_cod_cia:
                # Update existing (no code change)
                conn.execute("""
                    UPDATE datos_companias 
                    SET nombre_corto = ?, tipo_cia = ?
                    WHERE cod_cia = ?
                """, (nombre_corto, tipo_cia, cod_cia))
            else:
                # Insert new company
                conn.execute("""
                    INSERT INTO datos_companias (cod_cia, nombre_corto, tipo_cia, fecha)
                    VALUES (?, ?, ?, datetime('now'))
                """, (cod_cia, nombre_corto, tipo_cia))
            conn.commit()
            return True
    except Exception as e:
        logger.error(f"Error saving company: {e}")
        raise

def delete_company(cod_cia):
    """Delete company by code"""
    database_path = get_database_path()
    if not database_path:
        raise ValueError("Database path not configured")
    
    try:
        with sqlite3.connect(database_path) as conn:
            cursor = conn.execute("DELETE FROM datos_companias WHERE cod_cia = ?", (cod_cia,))
            conn.commit()
            return cursor.rowcount > 0
    except Exception as e:
        logger.error(f"Error deleting company: {e}")
        raise

@companies_bp.route('/')
def list_companies():
    """List all companies"""
    companies = get_all_companies()
    return render_template('companies/list.html', companies=companies)

@companies_bp.route('/add', methods=['GET', 'POST'])
def add_company():
    """Add new company"""
    form = CompanyForm()
    
    if form.validate_on_submit():
        try:
            cod_cia = form.cod_cia.data
            
            # Check if company already exists
            existing = get_company_by_code(cod_cia)
            if existing:
                flash(f'La compañía con código {cod_cia} ya existe', 'error')
                return render_template('companies/add.html', form=form)
            
            # Save company
            save_company(
                cod_cia=cod_cia,
                nombre_corto=form.nombre_corto.data.strip(),
                tipo_cia=form.tipo_cia.data
            )
            
            flash(f'Compañía {cod_cia} agregada exitosamente', 'success')
            return redirect(url_for('companies.list_companies'))
            
        except Exception as e:
            flash(f'Error al agregar compañía: {str(e)}', 'error')
            logger.error(f"Error adding company: {e}")
    
    return render_template('companies/add.html', form=form)

@companies_bp.route('/edit/<int:cod_cia>', methods=['GET', 'POST'])
def edit_company(cod_cia):
    """Edit existing company"""
    company = get_company_by_code(cod_cia)
    if not company:
        flash('Compañía no encontrada', 'error')
        return redirect(url_for('companies.list_companies'))
    
    form = CompanyForm()
    
    if form.validate_on_submit():
        try:
            new_cod_cia = form.cod_cia.data
            
            # If code changed, check if new code exists
            if new_cod_cia != cod_cia:
                existing = get_company_by_code(new_cod_cia)
                if existing:
                    flash(f'El código {new_cod_cia} ya existe', 'error')
                    return render_template('companies/edit.html', form=form, company=company)
            
            # Save company
            save_company(
                cod_cia=new_cod_cia,
                nombre_corto=form.nombre_corto.data.strip(),
                tipo_cia=form.tipo_cia.data,
                original_cod_cia=cod_cia
            )
            
            flash(f'Compañía {new_cod_cia} actualizada exitosamente', 'success')
            return redirect(url_for('companies.list_companies'))
            
        except Exception as e:
            flash(f'Error al actualizar compañía: {str(e)}', 'error')
            logger.error(f"Error updating company: {e}")
    
    # Populate form with existing data
    if request.method == 'GET':
        form.cod_cia.data = company['cod_cia']
        form.nombre_corto.data = company['nombre_corto']
        form.tipo_cia.data = company['tipo_cia']
        form.original_cod_cia.data = cod_cia
    
    return render_template('companies/edit.html', form=form, company=company)

@companies_bp.route('/delete/<int:cod_cia>', methods=['POST'])
def delete_company_route(cod_cia):
    """Delete company"""
    try:
        if delete_company(cod_cia):
            flash(f'Compañía {cod_cia} eliminada exitosamente', 'success')
        else:
            flash('Compañía no encontrada', 'error')
    except Exception as e:
        flash(f'Error al eliminar compañía: {str(e)}', 'error')
        logger.error(f"Error deleting company: {e}")
    
    return redirect(url_for('companies.list_companies'))