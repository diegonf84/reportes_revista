"""
Flask Web Application for Insurance Reporting System
Simple web interface for the insurance reporting console tools
"""

import sys
import os
from pathlib import Path

# Add project root to path so we can import existing modules
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from flask import Flask, render_template, flash, request, redirect, url_for
from dotenv import load_dotenv
import logging

# Import existing utilities
from modules.common import setup_logging
from modules.check_ultimos_periodos import list_available_periods

# Load environment variables
load_dotenv()

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

def create_app():
    """Create and configure Flask application"""
    app = Flask(__name__)
    
    # Configuration
    app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key')
    app.config['DATABASE'] = os.getenv('DATABASE')
    
    # Import and register blueprints
    from routes.companies import companies_bp
    from routes.data_processing import data_processing_bp
    
    app.register_blueprint(companies_bp)
    app.register_blueprint(data_processing_bp, url_prefix='/data-processing')
    
    @app.route('/')
    def dashboard():
        """Main dashboard"""
        try:
            # Get basic system information
            periods = list_available_periods()
            latest_period = periods[0] if periods else None
            
            # Get database info
            database_path = app.config['DATABASE']
            database_exists = os.path.exists(database_path) if database_path else False
            
            stats = {
                'total_periods': len(periods),
                'latest_period': latest_period,
                'database_connected': database_exists
            }
            
            return render_template('dashboard.html', stats=stats, periods=periods[:5])
            
        except Exception as e:
            logger.error(f"Error loading dashboard: {e}")
            flash(f"Error loading dashboard data: {str(e)}", 'error')
            return render_template('dashboard.html', stats={}, periods=[])
    
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return render_template('500.html'), 500
    
    return app

if __name__ == '__main__':
    app = create_app()
    port = int(os.getenv('FLASK_PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    print(f"🚀 Starting Insurance Reporting System Web UI")
    print(f"📊 Dashboard available at: http://localhost:{port}")
    print(f"🔧 Debug mode: {debug}")
    
    app.run(host='127.0.0.1', port=port, debug=debug)