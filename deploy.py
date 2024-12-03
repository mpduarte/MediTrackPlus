import os
import sys
import logging
import subprocess
from datetime import datetime
import signal
import atexit
from app import create_app, db
import psycopg2
import requests
from time import sleep
import psutil

def simulate_raspberry_pi_environment():
    """Create a simulated Raspberry Pi environment for testing"""
    try:
        # Create temporary test directories
        test_dirs = [
            '/tmp/sys/class/gpio',
            '/tmp/sys/class/thermal/thermal_zone0',
            '/tmp/dev/i2c-1',
            '/tmp/proc'
        ]
        for dir_path in test_dirs:
            os.makedirs(dir_path, exist_ok=True)
        
        # Simulate CPU info
        with open('/tmp/proc/cpuinfo', 'w') as f:
            f.write('Hardware\t: BCM2835\nRevision\t: 002\nModel\t: Raspberry Pi 4 Model B Rev 1.2\n')
        
        # Simulate temperature sensor
        with open('/tmp/sys/class/thermal/thermal_zone0/temp', 'w') as f:
            f.write('45000')
        
        # Set environment variable for testing
        os.environ['RASPBERRY_PI_TEST'] = 'true'
        
        return True
    except Exception as e:
        logger.error(f"Failed to create test environment: {e}")
        return False

# Configure logging
deployment_id = datetime.now().strftime('%Y%m%d_%H%M%S')
log_filename = f'deployment_{deployment_id}.log'

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(name)s] - %(message)s',
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def setup_log_rotation():
    """Setup log rotation for Raspberry Pi deployments"""
    try:
        import logging.handlers
        
        # Configure log rotation
        max_bytes = 5 * 1024 * 1024  # 5MB
        backup_count = 3
        
        # Setup rotating file handler for main log
        main_handler = logging.handlers.RotatingFileHandler(
            log_filename,
            maxBytes=max_bytes,
            backupCount=backup_count
        )
        main_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - [%(name)s] - %(message)s'
        ))
        
        # Setup rotating handler for debug log
        debug_handler = logging.handlers.RotatingFileHandler(
            f'debug_{log_filename}',
            maxBytes=max_bytes,
            backupCount=backup_count
        )
        debug_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - [%(name)s] - %(message)s\n'
            'File "%(pathname)s", line %(lineno)d, in %(funcName)s\n'
        ))
        
        return main_handler, debug_handler
    except Exception as e:
        logger.error(f"Failed to setup log rotation: {e}")
        return None, None

def cleanup_old_logs():
    """Clean up old log files to free up disk space"""
    try:
        log_dir = "logs"
        if not os.path.exists(log_dir):
            return
        
        # Keep only last 5 log files
        log_files = sorted(
            [f for f in os.listdir(log_dir) if f.endswith('.log')],
            key=lambda x: os.path.getmtime(os.path.join(log_dir, x))
        )[:-5]
        
        for log_file in log_files:
            try:
                os.remove(os.path.join(log_dir, log_file))
                logger.info(f"Cleaned up old log file: {log_file}")
            except Exception as e:
                logger.warning(f"Could not remove log file {log_file}: {e}")
    except Exception as e:
        logger.warning(f"Error during log cleanup: {e}")

def get_system_info():
    """Get system information including Raspberry Pi specific details"""
    system_info = {
        'is_raspberry_pi': False,
        'temperature': None,
        'gpio_temp_sensor': None,
        'memory': {
            'total': None,
            'available': None
        },
        'cpu_cores': os.cpu_count(),
        'usb_devices': [],
        'network_interfaces': [],
        'gpio_status': {},
        'power_supply': None,
        'hardware_model': None
    }
    
    # Check if running on Raspberry Pi
    try:
        with open('/proc/cpuinfo', 'r') as f:
            cpuinfo = f.read()
            if 'Raspberry Pi' in cpuinfo:
                system_info['is_raspberry_pi'] = True
                # Extract hardware model
                for line in cpuinfo.split('\n'):
                    if 'Hardware' in line:
                        system_info['hardware_model'] = line.split(':')[1].strip()
                
        if system_info['is_raspberry_pi']:
            # Get CPU temperature
            try:
                with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                    system_info['temperature'] = float(f.read()) / 1000.0
            except Exception as e:
                logger.warning(f"Could not read CPU temperature: {e}")
            
            # Check for GPIO temperature sensor (DS18B20)
            try:
                w1_devices = '/sys/bus/w1/devices/'
                if os.path.exists(w1_devices):
                    for device in os.listdir(w1_devices):
                        if device.startswith('28-'):
                            with open(f'{w1_devices}{device}/temperature', 'r') as f:
                                system_info['gpio_temp_sensor'] = float(f.read()) / 1000.0
            except Exception as e:
                logger.warning(f"Could not read GPIO temperature sensor: {e}")
            
            # Get USB devices
            try:
                import subprocess
                usb_devices = subprocess.check_output(['lsusb']).decode('utf-8').split('\n')
                system_info['usb_devices'] = [dev for dev in usb_devices if dev]
            except Exception as e:
                logger.warning(f"Could not get USB devices: {e}")
            
            # Get network interfaces
            try:
                net_if = psutil.net_if_stats()
                for interface, stats in net_if.items():
                    system_info['network_interfaces'].append({
                        'name': interface,
                        'speed': stats.speed,
                        'mtu': stats.mtu,
                        'is_up': stats.isup,
                        'duplex': stats.duplex if hasattr(stats, 'duplex') else None
                    })
            except Exception as e:
                logger.warning(f"Could not get network interfaces: {e}")
            
            # Get GPIO status
            try:
                gpio_path = '/sys/class/gpio'
                if os.path.exists(gpio_path):
                    for gpio in os.listdir(gpio_path):
                        if gpio.startswith('gpio'):
                            gpio_num = gpio.replace('gpio', '')
                            direction_file = f'{gpio_path}/{gpio}/direction'
                            value_file = f'{gpio_path}/{gpio}/value'
                            if os.path.exists(direction_file) and os.path.exists(value_file):
                                with open(direction_file, 'r') as f:
                                    direction = f.read().strip()
                                with open(value_file, 'r') as f:
                                    value = f.read().strip()
                                system_info['gpio_status'][gpio_num] = {
                                    'direction': direction,
                                    'value': value
                                }
            except Exception as e:
                logger.warning(f"Could not get GPIO status: {e}")
            
            # Get power supply information
            try:
                power_path = '/sys/class/power_supply/rpi_power'
                if os.path.exists(power_path):
                    system_info['power_supply'] = {}
                    voltage_path = f'{power_path}/voltage_now'
                    current_path = f'{power_path}/current_now'
                    if os.path.exists(voltage_path):
                        with open(voltage_path, 'r') as f:
                            system_info['power_supply']['voltage'] = float(f.read().strip()) / 1000000
                    if os.path.exists(current_path):
                        with open(current_path, 'r') as f:
                            system_info['power_supply']['current'] = float(f.read().strip()) / 1000000
            except Exception as e:
                logger.warning(f"Could not get power supply information: {e}")
        
        # Get memory information
        try:
            with open('/proc/meminfo', 'r') as f:
                mem_info = f.read()
                mem_lines = dict(line.split(':') for line in mem_info.split('\n') if line)
                system_info['memory']['total'] = int(mem_lines['MemTotal'].strip().split()[0]) // 1024
                system_info['memory']['available'] = int(mem_lines['MemAvailable'].strip().split()[0]) // 1024
        except Exception as e:
            logger.warning(f"Could not read memory information: {e}")
    except Exception as e:
        logger.warning(f"Could not determine if system is Raspberry Pi: {e}")
    
    return system_info

def monitor_system_performance():
    """Enhanced monitoring system performance metrics with Raspberry Pi optimizations and adaptive resource limits"""
    
    def get_adaptive_limits():
        """Calculate adaptive resource limits based on system capabilities"""
        limits = {
            'max_workers': 4,
            'max_connections': 100,
            'memory_limit': '256M',
            'cpu_limit': None
        }
        
        # Adjust limits for Raspberry Pi
        if os.path.exists('/proc/cpuinfo'):
            with open('/proc/cpuinfo', 'r') as f:
                if 'Raspberry Pi' in f.read():
                    memory = psutil.virtual_memory()
                    total_mem_mb = memory.total / (1024 * 1024)
                    
                    # Adjust based on available memory
                    if total_mem_mb < 512:  # Low memory Pi
                        limits.update({
                            'max_workers': 1,
                            'max_connections': 20,
                            'memory_limit': '128M'
                        })
                    elif total_mem_mb < 1024:  # Standard Pi
                        limits.update({
                            'max_workers': 2,
                            'max_connections': 50,
                            'memory_limit': '256M'
                        })
                    
                    # Set CPU limit based on temperature
                    try:
                        with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                            temp = float(f.read().strip()) / 1000.0
                            if temp > 70:
                                limits['cpu_limit'] = '50%'
                            elif temp > 60:
                                limits['cpu_limit'] = '75%'
                    except Exception:
                        pass
        
        return limits
    try:
        perf_data = {
            'cpu_usage': None,
            'memory_pressure': None,
            'disk_usage': None,
            'io_wait': None,
            'swap_usage': None,
            'network_io': None,
            'process_count': None,
            'cpu_freq': None,
            'disk_io_counters': None,
            'network_interfaces': None,
            'io_throttle': None,
            'power_stats': None,
            'temperature': None,
            'voltage': None,
            'throttled_state': None,
            'gpu_memory': None,
            'arm_memory': None
        }
        
        # Raspberry Pi specific metrics
        if os.path.exists('/sys/class/thermal/thermal_zone0/temp'):
            with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                perf_data['temperature'] = float(f.read().strip()) / 1000.0
                
        # Check for throttling and voltage issues
        if os.path.exists('/sys/devices/platform/soc/soc:firmware/get_throttled'):
            with open('/sys/devices/platform/soc/soc:firmware/get_throttled', 'r') as f:
                throttle_hex = f.read().strip()
                perf_data['throttled_state'] = int(throttle_hex, 16)
                
        # Try to get GPU memory split
        try:
            import subprocess
            gpu_mem = subprocess.check_output(['vcgencmd', 'get_mem', 'gpu']).decode()
            if gpu_mem:
                perf_data['gpu_memory'] = int(gpu_mem.replace('gpu=', '').replace('M', ''))
        except:
            pass
        
        # Get CPU usage and frequency scaling
        try:
            perf_data['cpu_usage'] = psutil.cpu_percent(interval=1)
            cpu_freq = psutil.cpu_freq()
            if cpu_freq:
                perf_data['cpu_freq'] = {
                    'current': cpu_freq.current,
                    'min': cpu_freq.min,
                    'max': cpu_freq.max
                }
        except Exception as e:
            logger.warning(f"Could not get CPU metrics: {e}")
        
        # Get memory pressure
        try:
            memory = psutil.virtual_memory()
            perf_data['memory_pressure'] = memory.percent
        except Exception as e:
            logger.warning(f"Could not get memory pressure: {e}")
        
        # Get disk usage and I/O metrics
        try:
            disk = psutil.disk_usage('/')
            perf_data['disk_usage'] = disk.percent
            disk_io = psutil.disk_io_counters()
            perf_data['disk_io_counters'] = {
                'read_bytes': disk_io.read_bytes,
                'write_bytes': disk_io.write_bytes,
                'read_time': disk_io.read_time,
                'write_time': disk_io.write_time
            }
        except Exception as e:
            logger.warning(f"Could not get disk metrics: {e}")
        
        # Get IO wait and throttling metrics
        try:
            cpu_times = psutil.cpu_times_percent(interval=1)
            perf_data['io_wait'] = cpu_times.iowait if hasattr(cpu_times, 'iowait') else None
            perf_data['io_throttle'] = {
                'throttle_time': None,
                'throttle_count': None
            }
            # Check for I/O throttling on Linux systems
            if os.path.exists('/sys/block/sda/stat'):
                with open('/sys/block/sda/stat', 'r') as f:
                    stats = f.read().split()
                    if len(stats) >= 11:
                        perf_data['io_throttle']['throttle_time'] = int(stats[10])
                        perf_data['io_throttle']['throttle_count'] = int(stats[9])
        except Exception as e:
            logger.warning(f"Could not get I/O metrics: {e}")
        
        # Get network interface metrics
        try:
            net_io = psutil.net_io_counters(pernic=True)
            perf_data['network_interfaces'] = {}
            for interface, counters in net_io.items():
                perf_data['network_interfaces'][interface] = {
                    'bytes_sent': counters.bytes_sent,
                    'bytes_recv': counters.bytes_recv,
                    'packets_sent': counters.packets_sent,
                    'packets_recv': counters.packets_recv,
                    'errin': counters.errin,
                    'errout': counters.errout,
                    'dropin': counters.dropin,
                    'dropout': counters.dropout
                }
        except Exception as e:
            logger.warning(f"Could not get network metrics: {e}")
        
        # Get power supply information (Raspberry Pi specific)
        try:
            if os.path.exists('/sys/class/power_supply/'):
                power_supplies = os.listdir('/sys/class/power_supply/')
                perf_data['power_stats'] = {}
                for supply in power_supplies:
                    supply_path = f'/sys/class/power_supply/{supply}'
                    if os.path.exists(f'{supply_path}/voltage_now'):
                        with open(f'{supply_path}/voltage_now', 'r') as f:
                            perf_data['power_stats'][supply] = {
                                'voltage': float(f.read().strip()) / 1000000  # Convert to volts
                            }
        except Exception as e:
            logger.warning(f"Could not get power supply metrics: {e}")
        
        return perf_data
    except Exception as e:
        logger.warning(f"Error monitoring system performance: {str(e)}")
        return None

def setup_health_monitoring():
    """Setup health monitoring system for Raspberry Pi"""
    import threading
    import time
    
    def monitor_health():
        while True:
            try:
                perf_data = monitor_system_performance()
                sys_info = get_system_info()
                
                if sys_info['is_raspberry_pi']:
                    logger.info("=== Raspberry Pi Health Check ===")
                    if sys_info['temperature']:
                        logger.info(f"CPU Temperature: {sys_info['temperature']}°C")
                    logger.info(f"Memory Available: {sys_info['memory']['available']}MB")
                    if perf_data:
                        logger.info(f"CPU Usage: {perf_data['cpu_usage']}%")
                        logger.info(f"Memory Pressure: {perf_data['memory_pressure']}%")
                        logger.info(f"Swap Usage: {perf_data.get('swap_usage', 'N/A')}%")
                        logger.info(f"Process Count: {perf_data.get('process_count', 'N/A')}")
                        
                        # Trigger optimizations if needed
                        if sys_info['temperature'] and sys_info['temperature'] > 75:
                            logger.warning("High temperature detected - reducing workload")
                            os.environ['FLASK_MAX_WORKERS'] = '1'
                        if perf_data['memory_pressure'] > 90:
                            logger.warning("High memory pressure - cleaning up processes")
                            clean_up_old_processes()
            except Exception as e:
                logger.error(f"Health monitoring error: {e}")
            time.sleep(300)  # Check every 5 minutes
    
    def clean_up_old_processes():
        try:
            for proc in psutil.process_iter(['pid', 'name', 'create_time']):
                try:
                    if proc.info['name'] == 'python' and \
                       (datetime.now().timestamp() - proc.info['create_time']) > 3600:
                        logger.info(f"Cleaning up old process: {proc.info['pid']}")
                        proc.terminate()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception as e:
            logger.error(f"Process cleanup error: {e}")
    
    # Start monitoring in a background thread
    if get_system_info()['is_raspberry_pi']:
        monitor_thread = threading.Thread(target=monitor_health, daemon=True)
        monitor_thread.start()
        logger.info("Health monitoring system started for Raspberry Pi")

# Global signal handler
signal_handler = None

def setup_graceful_shutdown():
    """Setup graceful shutdown handlers for Raspberry Pi"""
    def create_signal_handler():
        def handler(signum, frame):
            logger.info(f"Received signal {signum}")
            logger.info("Initiating graceful shutdown...")
            
            try:
                # Stop the Flask application
                logger.info("Stopping Flask application...")
                if hasattr(handler, 'flask_process'):
                    handler.flask_process.terminate()
                    handler.flask_process.wait(timeout=5)
                
                # Close database connections
                logger.info("Closing database connections...")
                try:
                    db.session.remove()
                    db.engine.dispose()
                except Exception as e:
                    logger.warning(f"Error closing database connections: {e}")
                
                # Final cleanup
                logger.info("Performing final cleanup...")
                sys.exit(0)
                
            except Exception as e:
                logger.error(f"Error during graceful shutdown: {e}")
                sys.exit(1)
        return handler
    
    global signal_handler
    signal_handler = create_signal_handler()
    
    # Register signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    # Register cleanup on normal exit
    atexit.register(lambda: logger.info("Application shutdown completed"))

def check_service_dependencies():
    """Check status of all service dependencies with Raspberry Pi compatibility"""
    logger.info("=== Checking Service Dependencies ===")
    dependencies_status = {
        "Database": False,
        "File System": False,
        "Port Availability": False,
        "Environment": False,
        "System Architecture": False,
        "System Resources": False
    }
    
    # Check if running on Raspberry Pi
    try:
        with open('/proc/cpuinfo', 'r') as f:
            cpu_info = f.read()
        is_raspberry_pi = 'BCM' in cpu_info or 'Raspberry' in cpu_info
        dependencies_status["System Architecture"] = True
        
        # Additional Raspberry Pi specific checks
        if is_raspberry_pi:
            logger.info("Running on Raspberry Pi: Performing additional checks")
            
            # Check CPU temperature
            try:
                with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                    temp = float(f.read()) / 1000.0
                logger.info(f"CPU Temperature: {temp}°C")
                if temp > 80:
                    logger.warning(f"High CPU temperature detected: {temp}°C")
            except Exception as e:
                logger.warning(f"Could not read CPU temperature: {str(e)}")
            
            # Check available memory
            with open('/proc/meminfo', 'r') as f:
                mem_info = f.read()
            total_mem = int([line for line in mem_info.split('\n') if 'MemTotal' in line][0].split()[1]) // 1024
            free_mem = int([line for line in mem_info.split('\n') if 'MemAvailable' in line][0].split()[1]) // 1024
            logger.info(f"Memory - Total: {total_mem}MB, Available: {free_mem}MB")
            
            if free_mem < 512:  # Less than 512MB available
                logger.warning(f"Low memory available: {free_mem}MB")
                logger.info("Enabling low memory optimizations")
            
            dependencies_status["System Resources"] = True
        else:
            logger.info("Running on standard system: OK")
            dependencies_status["System Resources"] = True
            
    except Exception as e:
        logger.warning(f"Could not determine system architecture: {str(e)}")
        dependencies_status["System Architecture"] = True  # Don't block deployment
        dependencies_status["System Resources"] = True
    
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
    """Verify PostgreSQL database connection with enhanced Raspberry Pi compatibility"""
    try:
        logger.info("Verifying database connection...")
        # Get SSL certificate path from environment or use system default
        ssl_cert = os.getenv('SSL_CERT_FILE', '/etc/ssl/certs/ca-certificates.crt')
        
        # Enhanced Raspberry Pi detection with multiple methods
        is_raspberry_pi = False
        try:
            # Method 1: Check CPU info
            with open('/proc/cpuinfo', 'r') as f:
                cpu_info = f.read()
                if 'BCM' in cpu_info or 'Raspberry' in cpu_info:
                    is_raspberry_pi = True
            
            # Method 2: Check device tree model
            if not is_raspberry_pi and os.path.exists('/proc/device-tree/model'):
                with open('/proc/device-tree/model', 'r') as f:
                    if 'Raspberry Pi' in f.read():
                        is_raspberry_pi = True
        except Exception as e:
            logger.warning(f"Pi detection warning: {e}")
            pass
        
        # Optimized connection parameters for Raspberry Pi
        conn_params = {
            'sslmode': 'verify-full' if os.path.exists(ssl_cert) else 'require',
            'sslcert': None,
            'sslkey': None,
            'sslrootcert': ssl_cert,
            'application_name': 'MedTracker',
            'options': (
                '-c statement_timeout=15000 '  # Extended timeout for Pi
                '-c work_mem=4MB '  # Reduced work memory for Pi
                '-c maintenance_work_mem=32MB'  # Reduced maintenance memory
            ) if is_raspberry_pi else (
                '-c statement_timeout=5000'
            ),
            'keepalives': 1,
            'keepalives_idle': 60 if is_raspberry_pi else 30,
            'keepalives_interval': 20 if is_raspberry_pi else 10,
            'keepalives_count': 3 if is_raspberry_pi else 5,
            'connect_timeout': 20 if is_raspberry_pi else 10
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

def check_port_availability(port, max_attempts=5):
    """Enhanced port availability check with Raspberry Pi considerations"""
    import socket
    import psutil
    
    def get_process_using_port(port):
        for conn in psutil.net_connections(kind='inet'):
            if conn.laddr.port == port:
                try:
                    return psutil.Process(conn.pid)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    return None
        return None

    def check_single_port(port):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                # Set socket options for quick release
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                if hasattr(socket, 'SO_REUSEPORT'):  # Some systems might not have this option
                    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
                s.bind(('', port))
                return True
        except socket.error:
            return False

    for attempt in range(max_attempts):
        current_port = port + attempt
        
        # Check if port is available
        if check_single_port(current_port):
            if attempt > 0:
                logger.info(f"Original port {port} was in use, using alternative port {current_port}")
                os.environ['PORT'] = str(current_port)
            else:
                logger.info(f"Port {current_port} is available")
            return True
        else:
            # Get process using the port
            process = get_process_using_port(current_port)
            if process:
                logger.warning(f"Port {current_port} is in use by process {process.name()} (PID: {process.pid})")
            else:
                logger.warning(f"Port {current_port} is in use by unknown process")

            # On Raspberry Pi, check system resource usage
            try:
                with open('/proc/cpuinfo', 'r') as f:
                    if 'Raspberry Pi' in f.read():
                        memory = psutil.virtual_memory()
                        if memory.percent > 90:
                            logger.warning("High memory usage detected on Raspberry Pi")
                        cpu_percent = psutil.cpu_percent(interval=1)
                        if cpu_percent > 80:
                            logger.warning("High CPU usage detected on Raspberry Pi")
            except Exception as e:
                logger.debug(f"Raspberry Pi specific checks failed: {e}")

            if attempt == max_attempts - 1:
                logger.error(f"All ports from {port} to {port + max_attempts - 1} are in use")
                return False
            continue
    return False

def setup_raspberry_pi_interfaces():
    """Setup Raspberry Pi specific interfaces like GPIO and I2C with fallback mechanisms"""
    try:
        is_raspberry_pi = False
        # Multiple detection methods for better compatibility
        detection_methods = [
            ('/proc/cpuinfo', 'Raspberry Pi'),
            ('/proc/device-tree/model', 'Raspberry Pi'),
            ('/sys/firmware/devicetree/base/model', 'Raspberry Pi')
        ]
        
        for file_path, search_text in detection_methods:
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r') as f:
                        if search_text in f.read():
                            is_raspberry_pi = True
                            break
                except Exception:
                    continue
        
        if not is_raspberry_pi:
            logger.info("Not running on Raspberry Pi - skipping hardware interface setup")
            return False
        
        # Check and setup GPIO
        if os.path.exists('/sys/class/gpio'):
            logger.info("GPIO interface available")
            # Ensure proper permissions
            try:
                subprocess.run(['chown', '-R', 'root:gpio', '/sys/class/gpio'])
                subprocess.run(['chmod', '-R', 'g+rw', '/sys/class/gpio'])
                logger.info("GPIO permissions configured")
            except Exception as e:
                logger.warning(f"Failed to set GPIO permissions: {e}")
        
        # Check and setup I2C
        if os.path.exists('/dev/i2c-1'):
            logger.info("I2C interface available")
            try:
                subprocess.run(['chown', 'root:i2c', '/dev/i2c-1'])
                subprocess.run(['chmod', 'g+rw', '/dev/i2c-1'])
                logger.info("I2C permissions configured")
            except Exception as e:
                logger.warning(f"Failed to set I2C permissions: {e}")
        
        # Setup device tree overlays if needed
        config_path = '/boot/config.txt'
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = f.read()
            if 'dtparam=i2c_arm=on' not in config:
                logger.info("Enabling I2C in device tree")
                with open(config_path, 'a') as f:
                    f.write('\ndtparam=i2c_arm=on\n')
        
        return True
    except Exception as e:
        logger.error(f"Error setting up Raspberry Pi interfaces: {e}")
        return False

def optimize_network_settings():
    """Optimize network settings for Raspberry Pi"""
    try:
        if not os.path.exists('/proc/cpuinfo'):
            return False
            
        with open('/proc/cpuinfo', 'r') as f:
            if 'Raspberry Pi' not in f.read():
                return False

        # Optimize network buffer sizes for Raspberry Pi
        with open('/proc/sys/net/core/rmem_max', 'w') as f:
            f.write('2097152')  # 2MB receive buffer
        with open('/proc/sys/net/core/wmem_max', 'w') as f:
            f.write('2097152')  # 2MB send buffer

        # Enable TCP fast open
        with open('/proc/sys/net/ipv4/tcp_fastopen', 'w') as f:
            f.write('3')

        logger.info("Network settings optimized for Raspberry Pi")
        return True
    except Exception as e:
        logger.warning(f"Failed to optimize network settings: {e}")
        return False

def optimize_power_settings():
    """Optimize power settings for Raspberry Pi"""
    try:
        if not os.path.exists('/proc/cpuinfo'):
            return False
            
        with open('/proc/cpuinfo', 'r') as f:
            if 'Raspberry Pi' not in f.read():
                return False

        # Set CPU governor to ondemand for better power efficiency
        if os.path.exists('/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor'):
            with open('/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor', 'w') as f:
                f.write('ondemand')

        # Optimize USB power management
        for usb_dev in os.listdir('/sys/bus/usb/devices'):
            power_control = f'/sys/bus/usb/devices/{usb_dev}/power/control'
            if os.path.exists(power_control):
                with open(power_control, 'w') as f:
                    f.write('auto')

        logger.info("Power settings optimized for Raspberry Pi")
        return True
    except Exception as e:
        logger.warning(f"Failed to optimize power settings: {e}")
        return False

def start_flask_application():
    """Start the Flask application with Raspberry Pi optimizations"""
    # Setup Raspberry Pi interfaces and optimizations
    setup_raspberry_pi_interfaces()
    optimize_network_settings()
    optimize_power_settings()
    try:
        logger.info("Starting Flask application with optimizations...")
        
        # Check if running on Raspberry Pi
        is_raspberry_pi = False
        try:
            with open('/proc/cpuinfo', 'r') as f:
                if 'Raspberry Pi' in f.read():
                    is_raspberry_pi = True
        except Exception:
            pass

        # Set environment variables based on system type
        env = os.environ.copy()
        if is_raspberry_pi:
            # Raspberry Pi optimizations
            memory = psutil.virtual_memory()
            available_mb = memory.available / (1024 * 1024)
            
            # Adjust worker count based on available memory
            if available_mb < 512:
                env['FLASK_MAX_WORKERS'] = '1'
                env['SQLALCHEMY_POOL_SIZE'] = '3'
            else:
                env['FLASK_MAX_WORKERS'] = '2'
                env['SQLALCHEMY_POOL_SIZE'] = '5'
            
            # Set other Pi-specific optimizations
            env['FLASK_THREADED'] = 'true'
            env['FLASK_TIMEOUT'] = '30'
        else:
            # Standard system settings
            env['FLASK_MAX_WORKERS'] = '4'
            env['SQLALCHEMY_POOL_SIZE'] = '10'
            env['FLASK_THREADED'] = 'true'
            env['FLASK_TIMEOUT'] = '15'
        
        # Start the Flask application using subprocess with optimized settings
        flask_process = subprocess.Popen(
            ["python", "run.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            env=env
        )
        
        # Give the process a moment to start
        sleep(5 if is_raspberry_pi else 2)
        
        # Check if process is running
        if flask_process.poll() is None:
            logger.info("Flask application started successfully")
            if is_raspberry_pi:
                logger.info("Running with Raspberry Pi optimizations:")
                logger.info(f"- Max Workers: {env['FLASK_MAX_WORKERS']}")
                logger.info(f"- Pool Size: {env['SQLALCHEMY_POOL_SIZE']}")
                logger.info(f"- Timeout: {env['FLASK_TIMEOUT']}s")
            signal_handler.flask_process = flask_process  # Assign to signal handler for graceful shutdown
            return True
        else:
            stdout, stderr = flask_process.communicate()
            logger.error("Flask application failed to start")
            logger.error(f"stdout: {stdout}")
            logger.error(f"stderr: {stderr}")
            
            # Additional error handling for Raspberry Pi
            if is_raspberry_pi:
                cpu_temp = None
                try:
                    with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                        cpu_temp = float(f.read().strip()) / 1000.0
                    if cpu_temp and cpu_temp > 80:
                        logger.error(f"High CPU temperature detected: {cpu_temp}°C")
                except Exception:
                    pass
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
    """Setup SSL certificates for database connection with Raspberry Pi compatibility"""
    try:
        logger.info("Setting up SSL certificates...")
        
        # Check for existing certificates in Raspberry Pi default locations
        rpi_cert_locations = [
            '/etc/ssl/certs/ca-certificates.crt',
            '/etc/ssl/certs/ca-bundle.crt'
        ]
        
        for cert_path in rpi_cert_locations:
            if os.path.exists(cert_path):
                logger.info(f"Using system SSL certificates from: {cert_path}")
                os.environ['SSL_CERT_FILE'] = cert_path
                return True
                
        # If no system certs found, generate our own
        from generate_ssl import main as generate_ssl
        cert_paths = generate_ssl()
        logger.info("SSL certificates generated successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to setup SSL certificates: {e}")
        logger.error("Stack trace:", exc_info=True)
        return False

def main():
    """Main deployment function with enhanced error handling and recovery"""
    logger.info("=== Starting Deployment Process ===")
    logger.info(f"Deployment ID: {deployment_id}")
    
    try:
        # Get system information
        system_info = get_system_info()
        
        # Setup Raspberry Pi specific optimizations
        if system_info['is_raspberry_pi']:
            logger.info("=== Setting up Raspberry Pi Optimizations ===")
            
            # Setup log rotation for resource management
            main_handler, debug_handler = setup_log_rotation()
            if main_handler and debug_handler:
                logger.info("Log rotation configured for Raspberry Pi")
                logger.addHandler(main_handler)
                logger.addHandler(debug_handler)
            
            # Setup health monitoring system
            setup_health_monitoring()
            
            # Setup graceful shutdown handlers
            setup_graceful_shutdown()
            
            # Adjust resource limits for Raspberry Pi
            logger.info("Configuring resource optimizations for Raspberry Pi")
            if system_info['memory']['available'] < 512:  # Less than 512MB available
                os.environ['FLASK_MAX_WORKERS'] = '1'
                os.environ['SQLALCHEMY_POOL_SIZE'] = '5'
                os.environ['SQLALCHEMY_MAX_OVERFLOW'] = '2'
                logger.info("Applied low-memory optimizations")
            
            # Monitor and adjust for high temperature
            if system_info.get('temperature') and system_info['temperature'] > 75:
                logger.warning(f"High CPU temperature detected: {system_info['temperature']}°C")
                os.environ['FLASK_MAX_WORKERS'] = '1'
                logger.info("Reduced workers due to high temperature")
            
            # Check disk space and cleanup if needed
            disk_usage = psutil.disk_usage('/')
            if disk_usage.percent > 90:
                logger.warning("High disk usage detected - initiating cleanup")
                cleanup_old_logs()
        else:
            logger.info("Running on standard system - skipping Raspberry Pi optimizations")
            
    except Exception as e:
        logger.error(f"Error during deployment setup: {str(e)}")
        logger.error("Stack trace:", exc_info=True)
        return False
        logger.info(f"CPU Temperature: {system_info['temperature']}°C")
        logger.info(f"Memory - Total: {system_info['memory']['total']}MB, Available: {system_info['memory']['available']}MB")
        logger.info(f"CPU Cores: {system_info['cpu_cores']}")
        
        # Setup log rotation for Raspberry Pi
        main_handler, debug_handler = setup_log_rotation()
        if main_handler and debug_handler:
            logger.info("Log rotation configured for Raspberry Pi deployment")
            logger.addHandler(main_handler)
            logger.addHandler(debug_handler)
        
        # Apply Raspberry Pi optimizations with performance monitoring
        perf_data = monitor_system_performance()
        if perf_data:
            logger.info("=== System Performance Metrics ===")
            logger.info(f"CPU Usage: {perf_data['cpu_usage']:.1f}%")
            logger.info(f"Memory Pressure: {perf_data['memory_pressure']:.1f}%")
            logger.info(f"Disk Usage: {perf_data['disk_usage']:.1f}%")
            logger.info(f"IO Wait: {perf_data['io_wait']:.1f}%")
            
            # Setup automatic recovery thresholds
            recovery_thresholds = {
                'cpu_temp': 85,  # Celsius
                'memory_pressure': 95,  # Percentage
                'cpu_usage': 95,  # Percentage
                'io_wait': 40  # Percentage
            }
            
            # Check for critical conditions requiring immediate action
            critical_conditions = []
            
            if system_info['temperature'] and system_info['temperature'] > recovery_thresholds['cpu_temp']:
                critical_conditions.append('CPU temperature critical')
                logger.error(f"Critical CPU temperature: {system_info['temperature']}°C")
                os.environ['FLASK_WORKERS_PER_CORE'] = '1'
                os.environ['SQLALCHEMY_POOL_SIZE'] = '2'
            
            if perf_data['memory_pressure'] > recovery_thresholds['memory_pressure']:
                critical_conditions.append('Memory pressure critical')
                logger.error(f"Critical memory pressure: {perf_data['memory_pressure']}%")
                os.environ['FLASK_MAX_WORKERS'] = '1'
                os.environ['SQLALCHEMY_POOL_SIZE'] = '2'
                os.environ['SQLALCHEMY_MAX_OVERFLOW'] = '1'
            
            if perf_data['cpu_usage'] > recovery_thresholds['cpu_usage']:
                critical_conditions.append('CPU usage critical')
                logger.error(f"Critical CPU usage: {perf_data['cpu_usage']}%")
                os.environ['FLASK_WORKERS_PER_CORE'] = '1'
                os.environ['SQLALCHEMY_POOL_RECYCLE'] = '3600'
            
            if perf_data['io_wait'] > recovery_thresholds['io_wait']:
                critical_conditions.append('IO wait critical')
                logger.error(f"Critical IO wait: {perf_data['io_wait']}%")
                os.environ['SQLALCHEMY_POOL_TIMEOUT'] = '120'
                os.environ['SQLALCHEMY_MAX_OVERFLOW'] = '1'

            # Enhanced Raspberry Pi specific optimizations
            try:
                if system_info['is_raspberry_pi']:
                    # Monitor swap usage
                    swap = psutil.swap_memory()
                    perf_data['swap_usage'] = swap.percent
                    if swap.percent > 80:
                        critical_conditions.append('Swap usage critical')
                        logger.error(f"Critical swap usage: {swap.percent}%")
                        os.environ['SQLALCHEMY_POOL_SIZE'] = '2'
                        os.environ['FLASK_MAX_WORKERS'] = '1'

                    # Monitor network I/O
                    net_io = psutil.net_io_counters()
                    perf_data['network_io'] = {
                        'bytes_sent': net_io.bytes_sent,
                        'bytes_recv': net_io.bytes_recv
                    }

                    # Monitor process count
                    process_count = len(psutil.pids())
                    perf_data['process_count'] = process_count
                    if process_count > 200:
                        critical_conditions.append('High process count')
                        logger.warning(f"High process count: {process_count}")
                        # Clean up old processes if needed
                        for proc in psutil.process_iter(['pid', 'name', 'create_time']):
                            try:
                                if proc.info['name'] == 'python' and \
                                   (datetime.now().timestamp() - proc.info['create_time']) > 3600:
                                    logger.info(f"Terminating old Python process: {proc.info['pid']}")
                                    proc.terminate()
                            except (psutil.NoSuchProcess, psutil.AccessDenied):
                                continue
            except Exception as e:
                logger.warning(f"Error during Raspberry Pi specific monitoring: {e}")
            
            if critical_conditions:
                logger.warning("=== Critical Resource Usage Detected ===")
                for condition in critical_conditions:
                    logger.warning(f"- {condition}")
                logger.info("Applied emergency resource optimization settings")
        
            # Apply optimizations based on performance metrics
            if system_info['memory']['available'] < 512 or perf_data['memory_pressure'] > 80:
                logger.info("Low memory mode enabled - Applying memory optimizations")
                os.environ['FLASK_MAX_WORKERS'] = '1'
                os.environ['SQLALCHEMY_POOL_SIZE'] = '3'
                os.environ['SQLALCHEMY_POOL_TIMEOUT'] = '60'
                
            if system_info['temperature'] and system_info['temperature'] > 70:
                logger.warning(f"High CPU temperature detected: {system_info['temperature']}°C")
                logger.info("Enabling temperature management mode")
                os.environ['FLASK_WORKERS_PER_CORE'] = '1'
                
            if perf_data['cpu_usage'] > 80:
                logger.warning("High CPU usage detected - Enabling CPU optimization mode")
                os.environ['FLASK_WORKERS_PER_CORE'] = '1'
                os.environ['SQLALCHEMY_POOL_RECYCLE'] = '1800'
                
            if perf_data['io_wait'] > 20:
                logger.warning("High IO wait detected - Adjusting database parameters")
                os.environ['SQLALCHEMY_POOL_TIMEOUT'] = '90'
                os.environ['SQLALCHEMY_MAX_OVERFLOW'] = '2'
    
    # Initial dependency check with enhanced recovery
    logger.info("Performing initial dependency check...")
    dependency_check_attempts = 3
    for attempt in range(dependency_check_attempts):
        if check_service_dependencies():
            break
        
        if attempt < dependency_check_attempts - 1:
            logger.warning(f"Dependency check attempt {attempt + 1} failed, attempting recovery...")
            # Implement progressive backoff
            sleep_time = (attempt + 1) * 5
            logger.info(f"Waiting {sleep_time} seconds before retry...")
            sleep(sleep_time)
            
            # Clear any existing port bindings
            try:
                import psutil
                for proc in psutil.process_iter(['pid', 'name', 'connections']):
                    try:
                        for conn in proc.connections():
                            if conn.status == 'LISTEN' and conn.laddr.port == int(os.environ.get('PORT', 4200)):
                                logger.info(f"Found process using port {conn.laddr.port}: {proc.name()}")
                                if proc.name() == 'python' or proc.name() == 'python3':
                                    logger.info(f"Terminating conflicting Python process: {proc.pid}")
                                    proc.terminate()
                                    proc.wait(timeout=5)
                    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired):
                        continue
            except Exception as e:
                logger.warning(f"Error while attempting to clear port: {e}")
        else:
            logger.error("Dependencies check failed after all recovery attempts")
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
    setup_graceful_shutdown()
    main()