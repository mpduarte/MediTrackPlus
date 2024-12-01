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

echo ""
log "=== Installation Complete ==="
echo ""
echo "Configuration Summary:"
echo "---------------------"
echo "1. Application files and directories setup: ✓"
echo "2. Dependencies installed: ✓"
echo "3. Database initialized: ✓"
echo "4. Environment configured: ✓"
echo ""
echo "To start the application:"
echo "1. Verify your database credentials in .env file"
echo "2. Run: python run.py"
echo ""
echo "The application will be available at http://0.0.0.0:3000"
echo "For more information, please refer to README.md"
echo ""
log "Installation script completed successfully"
