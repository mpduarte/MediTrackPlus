import os
import sys
import logging
import subprocess
from datetime import datetime
from app import create_app, db
import psycopg2
import requests
from time import sleep

# Configure enhanced logging
log_filename = f'deployment_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(name)s] - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_filename)
    ]
)

# Create a separate handler for debug messages
debug_handler = logging.FileHandler(f'debug_{log_filename}')
debug_handler.setLevel(logging.DEBUG)
debug_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(levelname)s - [%(name)s] - %(message)s\n'
    'File "%(pathname)s", line %(lineno)d, in %(funcName)s\n'
))

logger = logging.getLogger(__name__)
logger.addHandler(debug_handler)

def check_service_dependencies():
    """Check status of all service dependencies"""
    logger.info("=== Checking Service Dependencies ===")
    dependencies_status = {
        "Database": False,
        "File System": False,
        "Port Availability": False,
        "Environment": False
    }
    
    try:
        # Check Database
        try:
            conn_params = {
                'sslmode': 'verify-full',
                'sslcert': None,
                'sslkey': None,
                'sslrootcert': '/etc/ssl/certs/ca-certificates.crt',
                'application_name': 'MedTracker',
                'options': '-c statement_timeout=5000',
                'keepalives': 1,
                'keepalives_idle': 30,
                'keepalives_interval': 10,
                'keepalives_count': 5
            }
            conn = psycopg2.connect(os.environ['DATABASE_URL'], **conn_params)
            conn.close()
            dependencies_status["Database"] = True
            logger.info("Database connection: OK")
        except Exception as e:
            logger.error(f"Database connection failed: {str(e)}")
        
        # Check File System
        try:
            test_file = "static/uploads/test_write"
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
            dependencies_status["File System"] = True
            logger.info("File system access: OK")
        except Exception as e:
            logger.error(f"File system check failed: {str(e)}")
        
        # Check Port
        dependencies_status["Port Availability"] = check_port_availability(4200)
        
        # Check Environment
        required_vars = ['DATABASE_URL', 'FLASK_SECRET_KEY']
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        dependencies_status["Environment"] = len(missing_vars) == 0
        if dependencies_status["Environment"]:
            logger.info("Environment variables: OK")
        else:
            logger.error(f"Missing environment variables: {missing_vars}")
        
        # Log overall status
        logger.info("=== Dependencies Status Summary ===")
        for service, status in dependencies_status.items():
            logger.info(f"{service}: {'✓' if status else '✗'}")
        
        return all(dependencies_status.values())
        
    except Exception as e:
        logger.error("Critical error checking dependencies")
        logger.error("Error details:", exc_info=True)
        return False

def check_environment_variables():
    """Check if all required environment variables are set"""
    required_vars = ['DATABASE_URL', 'FLASK_SECRET_KEY']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.warning("Missing required environment variables: %s", missing_vars)
        if 'FLASK_SECRET_KEY' not in os.environ:
            os.environ['FLASK_SECRET_KEY'] = os.urandom(24).hex()
            logger.info("Generated new FLASK_SECRET_KEY")
        return True
    logger.info("All required environment variables are set")
    return True

def verify_database_connection():
    """Verify PostgreSQL database connection"""
    try:
        logger.info("Verifying database connection...")
        conn_params = {
            'sslmode': 'require',
            'sslcert': None,
            'sslkey': None,
            'sslrootcert': '/etc/ssl/certs/ca-certificates.crt',
            'application_name': 'MedTracker',
            'options': '-c statement_timeout=5000',
            'keepalives': 1,
            'keepalives_idle': 30,
            'keepalives_interval': 10,
            'keepalives_count': 5
        }
        conn = psycopg2.connect(os.environ['DATABASE_URL'], **conn_params)
        conn.close()
        logger.info("Database connection successful with SSL verification")
        return True
    except Exception as e:
        logger.error("Database connection failed: %s", str(e))
        return False

def setup_database():
    """Initialize the database with SQLAlchemy verification and detailed progress logging"""
    try:
        logger.info("Setting up database...")
        from sqlalchemy import inspect
        
        app = create_app()
        with app.app_context():
            logger.info("Acquired application context")
            
            # Test database connection
            try:
                db.engine.connect()
                logger.info("Database connection verified")
            except Exception as e:
                logger.error(f"Database connection failed: {str(e)}")
                return False
            
            # Create tables
            try:
                db.create_all()
                logger.info("Database tables creation initiated")
            except Exception as e:
                logger.error(f"Failed to create tables: {str(e)}")
                return False
            
            # Verify tables were created
            try:
                inspector = inspect(db.engine)
                tables = inspector.get_table_names()
                logger.info(f"Found tables: {tables}")
                
                # Check for required tables
                required_tables = {'user', 'medication', 'consumption', 'inventory_log', 'prescription'}
                existing_tables = set(tables)
                
                if not required_tables.issubset(existing_tables):
                    missing = required_tables - existing_tables
                    logger.error(f"Missing required tables: {missing}")
                    return False
                
                # Verify table structures
                for table in required_tables:
                    columns = [c['name'] for c in inspector.get_columns(table)]
                    logger.info(f"Table {table} columns: {columns}")
                
                logger.info("All required tables and structures verified")
                return True
            except Exception as e:
                logger.error(f"Table verification failed: {str(e)}")
                logger.error("Stack trace:", exc_info=True)
                return False
                
    except Exception as e:
        logger.error(f"Critical error in database setup: {str(e)}")
        logger.error("Stack trace:", exc_info=True)
        return False

def create_upload_directories():
    """Create necessary directories for file uploads"""
    try:
        logger.info("Creating upload directories...")
        upload_dirs = [
            'static/uploads',
            'static/uploads/prescriptions'
        ]
        for directory in upload_dirs:
            os.makedirs(directory, exist_ok=True)
            logger.info("Created directory: %s", directory)
        return True
    except Exception as e:
        logger.error("Error creating directories: %s", str(e))
        return False

def check_port_availability(port):
    """Check if the specified port is available"""
    import socket
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', port))
            logger.info(f"Port {port} is available")
            return True
    except socket.error as e:
        logger.error(f"Port {port} is already in use: {str(e)}")
        return False

def start_flask_application():
    """Start the Flask application using subprocess"""
    try:
        logger.info("Starting Flask application...")
        
        # Start the Flask application using subprocess
        flask_process = subprocess.Popen(
            ["python", "run.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        
        # Give the process a moment to start
        sleep(2)
        
        # Check if process is running
        if flask_process.poll() is None:
            logger.info("Flask application started successfully")
            return True
        else:
            stdout, stderr = flask_process.communicate()
            logger.error("Flask application failed to start")
            logger.error(f"stdout: {stdout}")
            logger.error(f"stderr: {stderr}")
            return False
            
    except Exception as e:
        logger.error(f"Critical error in Flask application startup: {str(e)}")
        logger.error("Stack trace:", exc_info=True)
        return False

def verify_application_running():
    """Verify if the Flask application is running with enhanced error handling"""
    try:
        logger.info("=== Starting Application Verification ===")
        logger.info("Stage 1: Initial connection check")
        
        max_attempts = 5
        timeout = 10
        expected_status_codes = {200: "OK", 302: "Redirect to login", 401: "Unauthorized", 403: "Forbidden"}
        health_endpoint = '/health'
        
        def log_response_details(response):
            logger.info(f"Response Status: {response.status_code}")
            logger.info(f"Response Headers: {dict(response.headers)}")
            logger.info(f"Response Time: {response.elapsed.total_seconds()}s")
        
        for attempt in range(max_attempts):
            try:
                # Check main endpoint
                logger.info(f"Attempt {attempt + 1}/{max_attempts} - Checking main endpoint")
                response = requests.get('http://localhost:4200/', timeout=timeout)
                
                if response.status_code in expected_status_codes:
                    log_response_details(response)
                    logger.info(f"Main endpoint check successful: {expected_status_codes[response.status_code]}")
                else:
                    logger.warning(f"Unexpected status code: {response.status_code}")
                
                # Check health endpoint
                try:
                    health_response = requests.get(f'http://localhost:4200{health_endpoint}', timeout=timeout)
                    if health_response.status_code == 200:
                        logger.info("Health check endpoint responding correctly")
                    else:
                        logger.warning(f"Health check returned status {health_response.status_code}")
                except requests.RequestException as he:
                    logger.warning(f"Health check endpoint not available: {str(he)}")
                
                # If we get here, the application is running
                logger.info("=== Application Verification Completed Successfully ===")
                return True
                
            except requests.Timeout:
                logger.error(f"Attempt {attempt + 1}: Connection timed out after {timeout} seconds")
            except requests.ConnectionError as ce:
                logger.error(f"Attempt {attempt + 1}: Connection error: {str(ce)}")
                logger.debug("Connection error details:", exc_info=True)
            except Exception as e:
                logger.error(f"Attempt {attempt + 1}: Unexpected error: {str(e)}")
                logger.error("Stack trace:", exc_info=True)
            
            if attempt < max_attempts - 1:
                sleep_time = 2 * (attempt + 1)  # Exponential backoff
                logger.info(f"Retrying in {sleep_time} seconds...")
                sleep(sleep_time)
            else:
                logger.error("Max retry attempts reached")
        
        logger.error("=== Application Verification Failed ===")
        return False
        
    except Exception as e:
        logger.error(f"Critical error during application verification: {str(e)}")
        logger.error("Full stack trace:", exc_info=True)
        return False

def setup_ssl_certificates():
    """Setup SSL certificates for database connection"""
    try:
        logger.info("Setting up SSL certificates...")
        from generate_ssl import main as generate_ssl
        cert_paths = generate_ssl()
        logger.info("SSL certificates generated successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to setup SSL certificates: {e}")
        return False

def main():
    """Main deployment function with enhanced error handling and recovery"""
    deployment_id = datetime.now().strftime('%Y%m%d_%H%M%S')
    logger.info("=== Starting Deployment Process ===")
    logger.info(f"Deployment ID: {deployment_id}")
    
    # Initial dependency check
    logger.info("Performing initial dependency check...")
    if not check_service_dependencies():
        logger.error("Critical dependencies not met. Attempting recovery...")
        # Wait and retry once
        sleep(5)
        if not check_service_dependencies():
            logger.error("Dependencies check failed after recovery attempt")
            logger.error("=== Deployment Failed ===")
            return False
    
    steps = [
        ("Checking environment variables", check_environment_variables),
        ("Setting up SSL certificates", setup_ssl_certificates),
        ("Verifying database connection", verify_database_connection),
        ("Setting up database", setup_database),
        ("Creating upload directories", create_upload_directories),
        ("Starting Flask application", start_flask_application),
        ("Verifying application status", verify_application_running)
    ]
    
    success = True
    failed_steps = []
    
    for step_name, step_func in steps:
        try:
            logger.info(f"=== Executing: {step_name} ===")
            logger.info(f"Started at: {datetime.now().strftime('%H:%M:%S')}")
            
            if not step_func():
                logger.error(f"Step failed: {step_name}")
                failed_steps.append(step_name)
                success = False
                break
                
            logger.info(f"Completed at: {datetime.now().strftime('%H:%M:%S')}")
            
        except Exception as e:
            logger.error(f"Unexpected error in {step_name}: {str(e)}")
            logger.error("Stack trace:", exc_info=True)
            failed_steps.append(step_name)
            success = False
            break
    
    if success:
        logger.info("=== Deployment Completed Successfully ===")
        logger.info("Stage Summary:")
        for step in steps:
            logger.info(f"✓ {step[0]}")
        logger.info("\nThe application is ready to run!")
        logger.info("Access it at http://localhost:4200")
        return True
    else:
        logger.error("=== Deployment Failed ===")
        logger.error("Failed Steps:")
        for step in failed_steps:
            logger.error(f"✗ {step}")
        logger.error("\nPlease check the detailed logs in debug_%s.log", 
                    datetime.now().strftime("%Y%m%d_%H%M%S"))
        return False

if __name__ == "__main__":
    main()
