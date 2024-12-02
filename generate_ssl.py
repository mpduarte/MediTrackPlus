import os
import subprocess
import stat
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_ssl_directories():
    """Create necessary directories for SSL certificates"""
    try:
        # Create .postgresql directory in user's home
        cert_dir = Path.home() / '.postgresql'
        cert_dir.mkdir(exist_ok=True)
        
        # Set proper permissions (700)
        cert_dir.chmod(stat.S_IRWXU)
        
        logger.info(f"Created directory: {cert_dir}")
        return str(cert_dir)
    except Exception as e:
        logger.error(f"Failed to create SSL directories: {e}")
        raise

def generate_self_signed_cert(cert_dir):
    """Generate self-signed certificates using OpenSSL"""
    try:
        cert_path = Path(cert_dir) / 'postgresql.crt'
        key_path = Path(cert_dir) / 'postgresql.key'
        root_cert_path = Path(cert_dir) / 'root.crt'
        
        # Generate private key
        subprocess.run([
            'openssl', 'genrsa',
            '-out', str(key_path),
            '2048'
        ], check=True)
        
        # Generate self-signed certificate
        subprocess.run([
            'openssl', 'req', '-new', '-x509',
            '-key', str(key_path),
            '-out', str(cert_path),
            '-days', '365',
            '-subj', '/CN=localhost'
        ], check=True)
        
        # Copy certificate to root.crt for client verification
        subprocess.run(['cp', str(cert_path), str(root_cert_path)], check=True)
        
        # Set proper permissions
        key_path.chmod(stat.S_IRUSR | stat.S_IWUSR)  # 600
        cert_path.chmod(stat.S_IRUSR | stat.S_IWUSR)  # 600
        root_cert_path.chmod(stat.S_IRUSR | stat.S_IWUSR)  # 600
        
        logger.info("SSL certificates generated successfully")
        return {
            'cert_path': str(cert_path),
            'key_path': str(key_path),
            'root_cert_path': str(root_cert_path)
        }
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to generate SSL certificates: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error generating certificates: {e}")
        raise

def main():
    """Main function to generate SSL certificates"""
    try:
        logger.info("Starting SSL certificate generation")
        
        # Create directories
        cert_dir = create_ssl_directories()
        logger.info(f"Created SSL directory at: {cert_dir}")
        
        # Generate certificates
        cert_paths = generate_self_signed_cert(cert_dir)
        
        # Set environment variables
        os.environ['SSL_CERT_PATH'] = cert_paths['cert_path']
        os.environ['SSL_KEY_PATH'] = cert_paths['key_path']
        os.environ['SSL_ROOT_CERT_PATH'] = cert_paths['root_cert_path']
        
        logger.info("SSL certificate generation completed successfully")
        logger.info(f"Certificate paths:\n"
                   f"  Certificate: {cert_paths['cert_path']}\n"
                   f"  Private Key: {cert_paths['key_path']}\n"
                   f"  Root Certificate: {cert_paths['root_cert_path']}")
        
        return cert_paths
    except Exception as e:
        logger.error(f"Failed to setup SSL certificates: {e}")
        raise

if __name__ == "__main__":
    main()
