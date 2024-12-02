import os
import subprocess
import stat
from pathlib import Path
import logging
import shutil

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_ssl_directories():
    """Create necessary directories for SSL certificates"""
    try:
        # Create SSL directories
        ssl_dirs = ['/etc/ssl/certs', '/etc/ssl/private']
        for dir_path in ssl_dirs:
            os.makedirs(dir_path, exist_ok=True)
            os.chmod(dir_path, stat.S_IRWXU)  # 700 permissions
            logger.info(f"Created directory: {dir_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to create SSL directories: {e}")
        return False

def generate_ssl_certificates():
    """Generate SSL certificates for PostgreSQL"""
    try:
        cert_path = '/etc/ssl/certs/postgresql.crt'
        key_path = '/etc/ssl/private/postgresql.key'
        
        # Generate private key
        key_cmd = [
            'openssl', 'genrsa',
            '-out', key_path,
            '2048'
        ]
        subprocess.run(key_cmd, check=True)
        os.chmod(key_path, stat.S_IRUSR | stat.S_IWUSR)  # 600 permissions
        
        # Generate certificate
        cert_cmd = [
            'openssl', 'req', '-new', '-x509',
            '-key', key_path,
            '-out', cert_path,
            '-days', '365',
            '-subj', '/CN=localhost'
        ]
        subprocess.run(cert_cmd, check=True)
        os.chmod(cert_path, stat.S_IRUSR | stat.S_IWUSR)  # 600 permissions
        
        # Copy system CA certificates
        shutil.copy('/etc/ssl/certs/ca-certificates.crt', '/etc/ssl/certs/root.crt')
        
        logger.info("SSL certificates generated successfully")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to generate SSL certificates: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error generating certificates: {e}")
        return False

def main():
    """Main function to setup SSL"""
    success = True
    
    # Create SSL directories
    if not create_ssl_directories():
        logger.error("Failed to create SSL directories")
        success = False
        return success
        
    # Generate SSL certificates
    if not generate_ssl_certificates():
        logger.error("Failed to generate SSL certificates")
        success = False
        return success
        
    if success:
        logger.info("SSL setup completed successfully")
    
    return success

if __name__ == "__main__":
    main()