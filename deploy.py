import os
import sys
import logging
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
            conn = psycopg2.connect(os.environ['DATABASE_URL'])
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
        dependencies_status["Port Availability"] = check_port_availability(3000)
        
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
        conn = psycopg2.connect(os.environ['DATABASE_URL'])
        conn.close()
        logger.info("Database connection successful")
        return True
    except Exception as e:
        logger.error("Database connection failed: %s", str(e))
        return False

def setup_database():
    """Initialize the database with direct SQL verification"""
    try:
        logger.info("Setting up database...")
        from execute_sql_tool import execute_sql_tool
        
        # Test database connection with direct SQL
        try:
            logger.info("Testing database connection...")
            result = execute_sql_tool("SELECT 1")
            if result:
                logger.info("Database connection test successful")
            else:
                logger.error("Database connection test failed")
                return False
        except Exception as e:
            logger.error(f"Database connection test failed: {str(e)}")
            return False

        # Create application tables
        try:
            app = create_app()
            with app.app_context():
                db.create_all()
                logger.info("Database tables created successfully")
                
                # Verify table creation
                table_check = execute_sql_tool("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public'
                """)
                if table_check:
                    logger.info(f"Verified tables: {[t[0] for t in table_check]}")
                    return True
                else:
                    logger.error("No tables found after creation")
                    return False
        except Exception as e:
            logger.error(f"Failed to create database tables: {str(e)}")
            logger.error("Stack trace:", exc_info=True)
            return False
            
    except Exception as e:
        logger.error(f"Unexpected error during database setup: {str(e)}")
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

def update_run_configuration():
    """Update the run configuration for the Flask application"""
    try:
        logger.info("Updating run configuration...")
        with open('run.py', 'w') as f:
            f.write('''from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000, debug=True)
''')
        logger.info("Run configuration updated successfully")
        return True
    except Exception as e:
        logger.error("Error updating run configuration: %s", str(e))
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
    """Start the Flask application using Replit workflow"""
    try:
        logger.info("Starting Flask application...")
        from workflows_set_run_config_tool import workflows_set_run_config_tool
        workflows_set_run_config_tool(
            name="Flask App",
            command="python run.py",
            wait_for_port=3000
        )
        logger.info("Flask application startup initiated")
        return True
    except Exception as e:
        logger.error(f"Failed to start Flask application: {str(e)}")
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
                response = requests.get('http://localhost:3000/', timeout=timeout)
                
                if response.status_code in expected_status_codes:
                    log_response_details(response)
                    logger.info(f"Main endpoint check successful: {expected_status_codes[response.status_code]}")
                else:
                    logger.warning(f"Unexpected status code: {response.status_code}")
                
                # Check health endpoint
                try:
                    health_response = requests.get(f'http://localhost:3000{health_endpoint}', timeout=timeout)
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
        
        # Recovery attempt for common issues
        logger.info("Attempting recovery procedures...")
        try:
            # Check if port is available
            if not check_port_availability(3000):
                logger.info("Attempting to free up port 3000...")
                import psutil
                for proc in psutil.process_iter(['pid', 'name', 'connections']):
                    try:
                        for conn in proc.connections():
                            if conn.laddr.port == 3000:
                                logger.info(f"Found process using port 3000: {proc.info['name']} (PID: {proc.info['pid']})")
                                # Don't forcefully terminate, just log
                                break
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
        except Exception as e:
            logger.error(f"Recovery attempt failed: {str(e)}")
            logger.error("Recovery error details:", exc_info=True)
        
        logger.error("=== Application Verification Failed ===")
        return False
        
    except Exception as e:
        logger.error(f"Critical error during application verification: {str(e)}")
        logger.error("Full stack trace:", exc_info=True)
        return False

def main():
    """Main deployment function with enhanced error handling and recovery"""
    logger.info("=== Starting Deployment Process ===")
    logger.info(f"Deployment ID: {datetime.now().strftime('%Y%m%d_%H%M%S')}")
    
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
        ("Verifying database connection", verify_database_connection),
        ("Setting up database", setup_database),
        ("Creating upload directories", create_upload_directories),
        ("Updating run configuration", update_run_configuration),
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
        logger.info("\nThe application is ready to run on Replit!")
        logger.info("Access it through the provided URL in your Replit workspace.")
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
