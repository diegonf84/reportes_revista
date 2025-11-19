"""
Inspector Module - Simple Data Investigation Tool

Shows account-level detail for Primas Emitidas from datos_balance table.
Single company, period range, account-level breakdown.
"""

from flask import Blueprint, render_template, request, jsonify
import pandas as pd
import sqlite3
import os
from dotenv import load_dotenv

load_dotenv()

inspector_bp = Blueprint('inspector', __name__)


def get_db_connection():
    """Get database connection."""
    database_path = os.getenv('DATABASE')
    if not database_path:
        raise ValueError("DATABASE environment variable not set")
    return sqlite3.connect(database_path)


@inspector_bp.route('/')
def main():
    """Main inspector page."""
    return render_template('inspector/main.html')


@inspector_bp.route('/api/inspect', methods=['POST'])
def api_inspect():
    """
    Inspect account-level data for Primas Emitidas.

    Expected JSON:
    {
        "cod_cia": "0010",
        "periodo_from": 202401,
        "periodo_to": 202404
    }
    """
    try:
        data = request.get_json()

        cod_cia = data.get('cod_cia', '').strip()
        periodo_from = int(data.get('periodo_from'))
        periodo_to = int(data.get('periodo_to'))

        # Validate
        if not cod_cia:
            return jsonify({'success': False, 'error': 'Código de compañía requerido'}), 400

        if periodo_from > periodo_to:
            return jsonify({'success': False, 'error': 'Período inicial debe ser menor o igual al final'}), 400

        with get_db_connection() as conn:
            # Step 1: Get account codes for primas_emitidas
            query_accounts = """
            SELECT DISTINCT pr.cod_cuenta, pr.signo
            FROM parametros_reportes pr
            JOIN conceptos_reportes cr ON pr.reporte = cr.reporte
                                        AND pr.referencia = cr.referencia
            WHERE cr.concepto = 'primas_emitidas'
            """

            accounts_df = pd.read_sql_query(query_accounts, conn)

            if accounts_df.empty:
                return jsonify({
                    'success': False,
                    'error': 'No se encontraron cuentas configuradas para primas_emitidas'
                }), 500

            account_map = dict(zip(accounts_df['cod_cuenta'], accounts_df['signo']))
            cod_cuentas_str = ','.join([f"'{k}'" for k in account_map.keys()])

            # Step 2: Query datos_balance
            query_data = f"""
            SELECT
                db.periodo,
                db.cod_subramo,
                drs.subramo_denominacion,
                db.cod_cuenta,
                db.importe
            FROM datos_balance db
            LEFT JOIN datos_ramos_subramos drs ON db.cod_subramo = drs.cod_subramo
            WHERE db.cod_cia = '{cod_cia}'
              AND db.periodo BETWEEN {periodo_from} AND {periodo_to}
              AND db.cod_cuenta IN ({cod_cuentas_str})
            ORDER BY db.periodo, db.cod_subramo, db.cod_cuenta
            """

            df = pd.read_sql_query(query_data, conn)

            # Get company name
            query_company = f"SELECT nombre_corto FROM datos_companias WHERE cod_cia = '{cod_cia}'"
            company_result = pd.read_sql_query(query_company, conn)
            company_name = company_result['nombre_corto'].iloc[0] if not company_result.empty else 'Desconocida'

            if df.empty:
                return jsonify({
                    'success': True,
                    'cod_cia': cod_cia,
                    'company_name': company_name,
                    'detail': [],
                    'summary': [],
                    'message': 'No se encontraron datos para esta compañía en el rango de períodos especificado'
                })

            # Step 3: Apply sign and calculate valor
            df['signo'] = df['cod_cuenta'].map(account_map)
            df['valor'] = df['signo'] * df['importe']

            # Step 4: Prepare detail data
            detail_records = df[[
                'periodo', 'cod_subramo', 'subramo_denominacion',
                'cod_cuenta', 'importe', 'signo', 'valor'
            ]].to_dict('records')

            # Step 5: Prepare summary by period
            summary = df.groupby('periodo', as_index=False)['valor'].sum()
            summary.columns = ['periodo', 'total']
            summary_records = summary.to_dict('records')

            return jsonify({
                'success': True,
                'cod_cia': cod_cia,
                'company_name': company_name,
                'detail': detail_records,
                'summary': summary_records
            })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
