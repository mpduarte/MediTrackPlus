import os
import time
import logging
from datetime import datetime
from flask import Flask, render_template
from sqlalchemy import event
from sqlalchemy.exc import DBAPIError, SQLAlchemyError
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from sqlalchemy.orm import DeclarativeBase
from flask_wtf.csrf import CSRFProtect

# Configure logging at module level
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    csrf = CSRFProtect()
    csrf.init_app(app)
    
    # Configure the secret key for sessions
    app.secret_key = os.environ.get("FLASK_SECRET_KEY") or os.urandom(24)
    
    # Configure database connection using environment variables
    database_url = os.environ.get("DATABASE_URL")
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    
    # Enhanced SQLAlchemy engine options with security and connection pooling
    engine_options = {
        'pool_size': 5,
        'pool_timeout': 30,
        'pool_recycle': 1800,
        'max_overflow': 10,
        'pool_pre_ping': True,
        'connect_args': {}
    }
    
    # Configure SSL based on database type
    # Common connection settings
    common_settings = {
        'options': '-c statement_timeout=5000',
        'keepalives': 1,
        'keepalives_idle': 30,
        'keepalives_interval': 10,
        'keepalives_count': 5,
        'application_name': 'MedTracker'
    }
    
    try:
        # Configure SSL settings with enhanced security
        ssl_cert = '/etc/ssl/certs/ca-certificates.crt'
        
        # Configure SSL with enhanced security parameters
        ssl_config = {
            **common_settings,
            'sslmode': 'verify-full',  # Enforce SSL and verify certificates
            'sslrootcert': ssl_cert,
            'connect_timeout': 30,
            'target_session_attrs': 'read-write'  # Ensure we connect to primary
        }
        
        if not os.path.exists(ssl_cert):
            logger.error(f"SSL certificate not found at {ssl_cert}")
            raise FileNotFoundError(f"SSL certificate not found at {ssl_cert}")
            
        logger.info(f"Using SSL certificate: {ssl_cert}")
        logger.info("SSL mode: verify-full (enforced)")
            
        engine_options['connect_args'].update(ssl_config)
        
        # Additional settings for Neon.tech
        if 'PGHOST' in os.environ and 'neon.tech' in os.environ.get('PGHOST', ''):
            engine_options['connect_args'].update({
                'sslcompression': '0',  # Disable SSL compression
                'target_session_attrs': 'read-write'  # Ensure we connect to primary
            })
            logger.info("Configured SSL for Neon.tech database with full verification")
        else:
            logger.info("Configured SSL for database with full verification")

    except Exception as e:
        logger.error(f"Failed to configure SSL: {str(e)}")
        raise
    
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = engine_options
    
    # Configure static files
    app.config["STATIC_FOLDER"] = "static"
    app.config["TEMPLATES_AUTO_RELOAD"] = True
    
    # Initialize database with enhanced error handling
    try:
        db.init_app(app)
        with app.app_context():
            # Test connection
            db.engine.connect()
            logger.info("Database connection established successfully")
    except DBAPIError as e:
        logger.error(f"Database API Error: {str(e)}")
        if "SSL error" in str(e):
            logger.error("SSL Configuration Error - Please verify SSL settings")
        raise
    except SQLAlchemyError as e:
        logger.error(f"SQLAlchemy Error: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected database error: {str(e)}")
        raise
    
    # Initialize login manager
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'
    
    # Register blueprints
    from routes import main_bp
    from auth import auth_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    
    @login_manager.user_loader
    def load_user(id):
        from models import User
        return User.query.get(int(id))
    
    # Health check endpoint
    @app.route('/health')
    def health_check():
        try:
            # Test database connection with detailed status
            with db.engine.connect() as connection:
                # Get SSL mode from engine configuration
                ssl_mode = app.config["SQLALCHEMY_ENGINE_OPTIONS"]["connect_args"].get("sslmode", "Not set")
                
                # Check if connection is alive and get server version
                from sqlalchemy import text
                result = connection.execute(text("SHOW server_version")).scalar()
                server_version = str(result)
                
                # Check SSL status
                ssl_status = connection.execute(text("SHOW ssl")).scalar()
                
                return {
                    "status": "healthy",
                    "timestamp": datetime.now().isoformat(),
                    "database": {
                        "connected": True,
                        "ssl_mode": ssl_mode,
                        "ssl_in_use": ssl_status == "on",
                        "server_version": server_version,
                        "connection_pool": {
                            "size": app.config["SQLALCHEMY_ENGINE_OPTIONS"]["pool_size"],
                            "timeout": app.config["SQLALCHEMY_ENGINE_OPTIONS"]["pool_timeout"],
                            "max_overflow": app.config["SQLALCHEMY_ENGINE_OPTIONS"]["max_overflow"]
                        }
                    }
                }, 200
        except DBAPIError as db_error:
            logger.error(f"Database API Error: {str(db_error)}")
            return {
                "status": "unhealthy",
                "timestamp": datetime.now().isoformat(),
                "database": {
                    "connected": False,
                    "error_type": "Database API Error",
                    "error": str(db_error)
                }
            }, 503
        except SQLAlchemyError as sa_error:
            logger.error(f"SQLAlchemy Error: {str(sa_error)}")
            return {
                "status": "unhealthy",
                "timestamp": datetime.now().isoformat(),
                "database": {
                    "connected": False,
                    "error_type": "SQLAlchemy Error",
                    "error": str(sa_error)
                }
            }, 503
        except Exception as e:
            logger.error(f"Unexpected Error: {str(e)}")
            return {
                "status": "unhealthy",
                "timestamp": datetime.now().isoformat(),
                "database": {
                    "connected": False,
                    "error_type": "Unexpected Error",
                    "error": str(e)
                }
            }, 500

    # Error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('500.html'), 500
    
    # Create database tables
    with app.app_context():
        db.create_all()
    
    return app
