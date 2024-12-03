#!/bin/bash

echo "=== MedTracker Installation Script ==="
echo "Checking system requirements..."

# Function to log messages
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

# Function to check command availability
check_command() {
    if ! command -v $1 &> /dev/null; then
        log "Error: $1 is not installed"
        return 1
    fi
    return 0
}

# Function to detect Raspberry Pi
detect_raspberry_pi() {
    if [ -f /proc/cpuinfo ] && grep -q "Raspberry Pi" /proc/cpuinfo; then
        log "Detected Raspberry Pi hardware"
        return 0
    elif [ -f /proc/device-tree/model ] && grep -q "Raspberry Pi" /proc/device-tree/model; then
        log "Detected Raspberry Pi hardware"
        return 0
    else
        return 1
    fi
}

# Function to check GPIO availability
check_gpio() {
    if [ -d "/sys/class/gpio" ]; then
        log "GPIO interface available"
        return 0
    else
        log "Warning: GPIO interface not found"
        return 1
    fi
}

# Function to check I2C availability
check_i2c() {
    if [ -e "/dev/i2c-1" ]; then
        log "I2C interface available"
        return 0
    else
        log "Warning: I2C interface not found"
        return 1
    fi
}

# Function to check SPI availability
check_spi() {
    if [ -e "/dev/spidev0.0" ]; then
        log "SPI interface available"
        return 0
    else
        log "Warning: SPI interface not found"
        return 1
    fi
}

# Function to check system resources
check_system_resources() {
    # Check RAM
    total_ram=$(free -m | awk '/^Mem:/{print $2}')
    if [ "$total_ram" -lt 512 ]; then
        log "Warning: Less than 512MB RAM available (${total_ram}MB)"
        return 1
    fi
    log "Memory check passed: ${total_ram}MB RAM available"

    # Check storage
    free_space=$(df -m / | awk 'NR==2 {print $4}')
    if [ "$free_space" -lt 1024 ]; then
        log "Warning: Less than 1GB free space available (${free_space}MB)"
        return 1
    fi
    log "Storage check passed: ${free_space}MB free space available"

    return 0
}

# Function to setup temperature monitoring
setup_temperature_monitoring() {
    if [ -f /sys/class/thermal/thermal_zone0/temp ]; then
        # Create temperature monitoring script
        cat > /usr/local/bin/monitor_temperature.sh << 'EOF'
#!/bin/bash
while true; do
    temp=$(cat /sys/class/thermal/thermal_zone0/temp)
    temp=$(echo "scale=2; $temp/1000" | bc)
    echo "[$(date)] CPU Temperature: ${temp}°C" >> /var/log/medtracker/temperature.log
    sleep 300
done
EOF
        chmod +x /usr/local/bin/monitor_temperature.sh
        log "Temperature monitoring script created"
        return 0
    else
        log "Warning: Temperature monitoring not available"
        return 1
    fi
}

# Function to setup systemd service
setup_systemd_service() {
    cat > /etc/systemd/system/medtracker.service << EOF
[Unit]
Description=MedTracker Application
After=network.target postgresql.service

[Service]
User=medtracker
Group=medtracker
WorkingDirectory=$(pwd)
Environment=FLASK_APP=run.py
Environment=FLASK_ENV=production
ExecStart=/usr/bin/python3 run.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

    # Create temperature monitoring service if on Raspberry Pi
    if detect_raspberry_pi; then
        cat > /etc/systemd/system/medtracker-temp-monitor.service << EOF
[Unit]
Description=MedTracker Temperature Monitor
After=network.target

[Service]
Type=simple
ExecStart=/usr/local/bin/monitor_temperature.sh
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
    fi

    systemctl daemon-reload
    systemctl enable medtracker.service
    if detect_raspberry_pi; then
        systemctl enable medtracker-temp-monitor.service
    fi
    log "Systemd services configured"
}

# Function to setup backup configuration
setup_backup_configuration() {
    # Create backup directory
    mkdir -p /var/backups/medtracker
    
    # Create backup script
    cat > /usr/local/bin/medtracker-backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/var/backups/medtracker"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME="medtracker"

# Backup database
pg_dump $DB_NAME > "$BACKUP_DIR/db_backup_$DATE.sql"

# Backup uploads
tar -czf "$BACKUP_DIR/uploads_backup_$DATE.tar.gz" static/uploads/

# Rotate backups (keep last 5)
cd $BACKUP_DIR
ls -t db_backup_* | tail -n +6 | xargs -r rm
ls -t uploads_backup_* | tail -n +6 | xargs -r rm
EOF

    chmod +x /usr/local/bin/medtracker-backup.sh
    
    # Setup backup cron job
    echo "0 2 * * * /usr/local/bin/medtracker-backup.sh" | crontab -
    
    log "Backup configuration completed"
}

# Function to setup log rotation
setup_log_rotation() {
    cat > /etc/logrotate.d/medtracker << EOF
/var/log/medtracker/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 640 medtracker medtracker
    size 10M
}
EOF
    log "Log rotation configured"
}

# Function to setup permissions
setup_permissions() {
    # Create medtracker user and group if they don't exist
    if ! id -u medtracker >/dev/null 2>&1; then
        useradd -r -s /bin/false medtracker
    fi

    # Set directory permissions
    chown -R medtracker:medtracker .
    chmod -R 750 .
    
    if detect_raspberry_pi; then
        # Setup GPIO permissions
        usermod -a -G gpio medtracker
        # Setup I2C permissions
        usermod -a -G i2c medtracker
        # Setup SPI permissions
        usermod -a -G spi medtracker
    fi
    
    log "Permissions configured"
}

# Main installation process
log "Starting installation..."

# Create log directory
mkdir -p /var/log/medtracker
chmod 750 /var/log/medtracker

# Check if running on Raspberry Pi
if detect_raspberry_pi; then
    log "=== Running on Raspberry Pi ==="
    
    # Check Raspberry Pi specific dependencies
    log "Checking Raspberry Pi dependencies..."
    check_gpio
    check_i2c
    check_spi
    
    # Install Raspberry Pi specific packages
    log "Installing Raspberry Pi specific packages..."
    apt-get update
    apt-get install -y python3-rpi.gpio python3-smbus i2c-tools

    # Setup temperature monitoring
    setup_temperature_monitoring
fi

# Check system resources
check_system_resources || {
    log "Error: System requirements not met"
    exit 1
}

# Check Python version
check_command python3 || exit 1

python_version=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
if (( $(echo "$python_version 3.8" | awk '{print ($1 < $2)}') )); then
    log "Error: Python 3.8 or higher is required (found $python_version)"
    exit 1
fi
log "Python version check passed: $python_version"

# Check PostgreSQL
check_command psql || exit 1
log "PostgreSQL installation check passed"

# Install dependencies
log "Installing Python dependencies..."
if ! python3 -m pip install --upgrade pip; then
    log "Error: Failed to upgrade pip"
    exit 1
fi

if ! pip install -r requirements.txt; then
    log "Error: Failed to install dependencies"
    exit 1
fi
log "Dependencies installed successfully"

# Create necessary directories
log "Creating required directories..."
directories=(
    "static/uploads"
    "static/uploads/prescriptions"
    "logs"
)

for dir in "${directories[@]}"; do
    if ! mkdir -p "$dir"; then
        log "Error: Failed to create directory: $dir"
        exit 1
    fi
done
log "Directories created successfully"

# Setup environment variables
if [ ! -f .env ]; then
    log "Setting up environment variables..."
    {
        echo "FLASK_APP=run.py"
        echo "FLASK_ENV=production"
        echo "DATABASE_URL=${DATABASE_URL:-postgresql://localhost:5432/medtracker}"
        echo "FLASK_SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_hex(24))')"
    } > .env
    log "Created .env file with default settings"
fi

# Initialize database
log "Initializing database..."
if ! python3 - <<EOF
from app import create_app, db
app = create_app()
with app.app_context():
    db.create_all()
EOF
then
    log "Error: Failed to initialize database"
    exit 1
fi
log "Database initialized successfully"

# Setup systemd service
setup_systemd_service

# Setup backup configuration
setup_backup_configuration

# Setup log rotation
setup_log_rotation

# Setup permissions
setup_permissions

echo ""
log "=== Installation Complete ==="
echo ""
echo "Configuration Summary:"
echo "---------------------"
echo "1. Application files and directories setup: ✓"
echo "2. Dependencies installed: ✓"
echo "3. Database initialized: ✓"
echo "4. Environment configured: ✓"
if detect_raspberry_pi; then
    echo "5. Raspberry Pi specific setup: ✓"
    echo "   - GPIO/I2C/SPI configured"
    echo "   - Temperature monitoring enabled"
    echo "   - Hardware permissions set"
fi
echo "5. Services configured: ✓"
echo "6. Backup system configured: ✓"
echo "7. Log rotation configured: ✓"
echo ""
echo "To start the application:"
echo "1. Verify your database credentials in .env file"
echo "2. Start the service: systemctl start medtracker"
echo ""
echo "The application will be available at http://0.0.0.0:4200"
echo "For more information, please refer to README.md"
echo ""
log "Installation script completed successfully"
