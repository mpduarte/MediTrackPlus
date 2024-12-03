#!/bin/bash

echo "=== MedTracker Raspberry Pi Installation Script ==="

# Import common functions from main install script
source install.sh

# Function to enable required interfaces
enable_interfaces() {
    echo "Enabling required interfaces..."
    
    # Enable I2C
    if ! grep -q "^dtparam=i2c_arm=on" /boot/config.txt; then
        echo "dtparam=i2c_arm=on" | sudo tee -a /boot/config.txt
        echo "I2C interface enabled"
    fi
    
    # Enable SPI
    if ! grep -q "^dtparam=spi=on" /boot/config.txt; then
        echo "dtparam=spi=on" | sudo tee -a /boot/config.txt
        echo "SPI interface enabled"
    fi
    
    # Enable 1-Wire (for temperature sensors)
    if ! grep -q "^dtoverlay=w1-gpio" /boot/config.txt; then
        echo "dtoverlay=w1-gpio" | sudo tee -a /boot/config.txt
        echo "1-Wire interface enabled"
    fi
}

# Function to optimize for Raspberry Pi
optimize_system() {
    echo "Optimizing system for Raspberry Pi..."
    
    # Adjust swap size based on available RAM
    total_ram=$(free -m | awk '/^Mem:/{print $2}')
    if [ "$total_ram" -lt 1024 ]; then
        sudo dphys-swapfile swapoff
        sudo sed -i "s/CONF_SWAPSIZE=.*/CONF_SWAPSIZE=1024/" /etc/dphys-swapfile
        sudo dphys-swapfile setup
        sudo dphys-swapfile swapon
        echo "Swap size optimized for low memory system"
    fi
    
    # Optimize PostgreSQL for Raspberry Pi
    if [ -f /etc/postgresql/*/main/postgresql.conf ]; then
        sudo sed -i "s/#shared_buffers = .*/shared_buffers = 128MB/" /etc/postgresql/*/main/postgresql.conf
        sudo sed -i "s/#work_mem = .*/work_mem = 4MB/" /etc/postgresql/*/main/postgresql.conf
        sudo sed -i "s/#maintenance_work_mem = .*/maintenance_work_mem = 32MB/" /etc/postgresql/*/main/postgresql.conf
        sudo sed -i "s/#effective_cache_size = .*/effective_cache_size = 256MB/" /etc/postgresql/*/main/postgresql.conf
        echo "PostgreSQL optimized for Raspberry Pi"
    fi
}

# Function to setup power management
setup_power_management() {
    echo "Setting up power management..."
    
    # Create power monitoring script
    cat > /usr/local/bin/monitor_power.sh << 'EOF'
#!/bin/bash
while true; do
    # Get voltage
    voltage=$(vcgencmd measure_volts core | cut -d= -f2)
    # Get throttling status
    throttle=$(vcgencmd get_throttled)
    # Log status
    echo "[$(date)] Voltage: $voltage, Throttle: $throttle" >> /var/log/medtracker/power.log
    sleep 300
done
EOF
    chmod +x /usr/local/bin/monitor_power.sh
    
    # Create systemd service for power monitoring
    cat > /etc/systemd/system/medtracker-power-monitor.service << EOF
[Unit]
Description=MedTracker Power Monitor
After=network.target

[Service]
Type=simple
ExecStart=/usr/local/bin/monitor_power.sh
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable medtracker-power-monitor.service
    echo "Power management setup completed"
}

# Main installation process
echo "Starting Raspberry Pi specific installation..."

# Check if running on Raspberry Pi
if ! detect_raspberry_pi; then
    echo "Error: This script must be run on a Raspberry Pi"
    exit 1
fi

# Install Raspberry Pi specific packages
echo "Installing Raspberry Pi specific packages..."
apt-get update
apt-get install -y \
    python3-rpi.gpio \
    python3-smbus \
    i2c-tools \
    python3-w1thermsensor \
    wiringpi

# Enable required interfaces
enable_interfaces

# Check interfaces
check_gpio
check_i2c
check_spi

# Setup temperature monitoring
setup_temperature_monitoring

# Setup power management
setup_power_management

# Optimize system
optimize_system

# Setup permissions
setup_permissions

echo ""
echo "=== Raspberry Pi Installation Complete ==="
echo ""
echo "Additional Setup Summary:"
echo "------------------------"
echo "1. Hardware interfaces enabled and configured"
echo "2. System optimized for Raspberry Pi"
echo "3. Temperature monitoring enabled"
echo "4. Power management configured"
echo "5. Permissions set for hardware access"
echo ""
echo "To complete setup:"
echo "1. Reboot your Raspberry Pi"
echo "2. Run the main installation script: ./install.sh"
echo ""
