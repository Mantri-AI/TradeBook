#!/bin/bash

# Mantri Trade Book - Cross-platform installation script
# This script works on Linux, macOS, and Windows (with WSL/Git Bash)

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
APP_NAME="TradeBook"
INSTALL_DIR="$HOME/$APP_NAME"
VENV_NAME="venv"
PYTHON_MIN_VERSION="3.8"

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check Python version
check_python_version() {
    if command_exists python3; then
        PYTHON_CMD="python3"
    elif command_exists python; then
        PYTHON_CMD="python"
    else
        return 1
    fi

    PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | awk '{print $2}')
    REQUIRED_VERSION=$PYTHON_MIN_VERSION
    
    if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" = "$REQUIRED_VERSION" ]; then
        return 0
    else
        return 1
    fi
}

# Function to detect OS
detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        OS="linux"
        DISTRO=$(lsb_release -si 2>/dev/null || echo "Unknown")
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
        DISTRO="macOS"
    elif [[ "$OSTYPE" == "cygwin" ]] || [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
        OS="windows"
        DISTRO="Windows"
    else
        OS="unknown"
        DISTRO="Unknown"
    fi
}

# Function to install system dependencies
install_system_deps() {
    print_status "Installing system dependencies for $DISTRO..."
    
    case $OS in
        "linux")
            if command_exists apt-get; then
                sudo apt-get update
                sudo apt-get install -y python3 python3-pip python3-venv git curl build-essential
            elif command_exists yum; then
                sudo yum update -y
                sudo yum install -y python3 python3-pip git curl gcc gcc-c++ make
            elif command_exists dnf; then
                sudo dnf update -y
                sudo dnf install -y python3 python3-pip git curl gcc gcc-c++ make
            else
                print_error "Unsupported Linux distribution. Please install Python 3.8+, pip, git, and build tools manually."
                exit 1
            fi
            ;;
        "macos")
            if command_exists brew; then
                brew update
                brew install python3 git
            else
                print_warning "Homebrew not found. Please install Python 3.8+ and git manually."
                print_warning "Visit: https://brew.sh/ to install Homebrew"
            fi
            ;;
        "windows")
            print_warning "Please ensure you have Python 3.8+, pip, and git installed."
            print_warning "Download from: https://www.python.org/downloads/ and https://git-scm.com/"
            ;;
        *)
            print_error "Unsupported operating system: $OSTYPE"
            exit 1
            ;;
    esac
}

# Function to check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check Python
    if ! check_python_version; then
        print_error "Python $PYTHON_MIN_VERSION or higher is required"
        print_status "Current Python version: $($PYTHON_CMD --version 2>&1 || echo 'Not found')"
        install_system_deps
        
        # Check again after installation
        if ! check_python_version; then
            print_error "Failed to install required Python version"
            exit 1
        fi
    fi
    
    print_success "Python $($PYTHON_CMD --version 2>&1 | awk '{print $2}') found"
    
    # Check pip
    if ! command_exists pip3 && ! command_exists pip; then
        print_error "pip is required but not found"
        exit 1
    fi
    
    # Check git
    if ! command_exists git; then
        print_error "git is required but not found"
        install_system_deps
        
        if ! command_exists git; then
            print_error "Failed to install git"
            exit 1
        fi
    fi
    
    print_success "All prerequisites satisfied"
}

# Function to create installation directory
create_install_dir() {
    print_status "Creating installation directory: $INSTALL_DIR"
    
    if [ -d "$INSTALL_DIR" ]; then
        print_warning "Directory already exists. Backing up to ${INSTALL_DIR}.backup"
        mv "$INSTALL_DIR" "${INSTALL_DIR}.backup.$(date +%Y%m%d_%H%M%S)"
    fi
    
    mkdir -p "$INSTALL_DIR"
    cd "$INSTALL_DIR"
}

# Function to copy application files
copy_application() {
    print_status "Copying application files..."
    
    # Get the directory where this script is located
    SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
    APP_SOURCE_DIR="$(dirname "$SCRIPT_DIR")"
    
    # Copy all files except deploy directory and cache files
    rsync -av --exclude='deploy/' \
              --exclude='__pycache__/' \
              --exclude='*.pyc' \
              --exclude='.git/' \
              --exclude='instance/' \
              --exclude='logs/' \
              "$APP_SOURCE_DIR/" "$INSTALL_DIR/"
    
    # Create necessary directories
    mkdir -p "$INSTALL_DIR/instance"
    mkdir -p "$INSTALL_DIR/logs"
    
    print_success "Application files copied"
}

# Function to create virtual environment
create_virtual_env() {
    print_status "Creating Python virtual environment..."
    
    cd "$INSTALL_DIR"
    $PYTHON_CMD -m venv "$VENV_NAME"
    
    # Activate virtual environment
    if [[ "$OS" == "windows" ]]; then
        source "$VENV_NAME/Scripts/activate"
    else
        source "$VENV_NAME/bin/activate"
    fi
    
    # Upgrade pip
    pip install --upgrade pip
    
    print_success "Virtual environment created"
}

# Function to install Python dependencies
install_dependencies() {
    print_status "Installing Python dependencies..."
    
    cd "$INSTALL_DIR"
    
    # Activate virtual environment
    if [[ "$OS" == "windows" ]]; then
        source "$VENV_NAME/Scripts/activate"
    else
        source "$VENV_NAME/bin/activate"
    fi
    
    # Install dependencies
    pip install -r requirements.txt
    
    print_success "Dependencies installed"
}

# Function to setup database
setup_database() {
    print_status "Setting up database..."
    
    cd "$INSTALL_DIR"
    
    # Activate virtual environment
    if [[ "$OS" == "windows" ]]; then
        source "$VENV_NAME/Scripts/activate"
    else
        source "$VENV_NAME/bin/activate"
    fi
    
    # Create environment file if it doesn't exist
    if [ ! -f ".env" ]; then
        cat > .env << EOF
SECRET_KEY=$(openssl rand -hex 32 2>/dev/null || python3 -c "import secrets; print(secrets.token_hex(32))")
ENCRYPTION_KEY=$(openssl rand -hex 16 2>/dev/null || python3 -c "import secrets; print(secrets.token_hex(16))")
FLASK_ENV=production
DATABASE_URL=sqlite:///instance/mantri_trade_book.db
EOF
        print_success "Environment file created"
    fi
    
    # Initialize database
    python3 -c "
from app import app
with app.app_context():
    from models.database import db
    db.create_all()
    print('Database initialized successfully')
"
    
    print_success "Database setup complete"
}

# Function to create startup scripts
create_startup_scripts() {
    print_status "Creating startup scripts..."
    
    cd "$INSTALL_DIR"
    
    # Create start script for Unix-like systems
    cat > start.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
export FLASK_ENV=production
python3 app.py
EOF
    
    # Create start script for Windows
    cat > start.bat << 'EOF'
@echo off
cd /d "%~dp0"
call venv\Scripts\activate.bat
set FLASK_ENV=production
python app.py
pause
EOF
    
    # Create service script for systemd (Linux)
    cat > TradeBook.service << EOF
[Unit]
Description=Mantri Trade Book Flask Application
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$INSTALL_DIR
Environment=PATH=$INSTALL_DIR/$VENV_NAME/bin
Environment=FLASK_ENV=production
ExecStart=$INSTALL_DIR/$VENV_NAME/bin/python3 $INSTALL_DIR/app.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF
    
    # Make scripts executable
    chmod +x start.sh
    chmod +x start.bat
    
    print_success "Startup scripts created"
}

# Function to install as system service (Linux only)
install_service() {
    if [[ "$OS" == "linux" ]] && command_exists systemctl; then
        print_status "Installing as system service..."
        
        sudo cp "$INSTALL_DIR/TradeBook.service" /etc/systemd/system/
        sudo systemctl daemon-reload
        sudo systemctl enable TradeBook.service
        
        print_success "Service installed. Use 'sudo systemctl start TradeBook' to start"
    else
        print_warning "System service installation is only available on Linux with systemd"
    fi
}

# Function to create desktop shortcut
create_desktop_shortcut() {
    case $OS in
        "linux")
            if [ -d "$HOME/Desktop" ]; then
                cat > "$HOME/Desktop/Mantri Trade Book.desktop" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Mantri Trade Book
Comment=Trading Portfolio Management Application
Exec=$INSTALL_DIR/start.sh
Icon=$INSTALL_DIR/static/favicon.ico
Terminal=true
Categories=Office;Finance;
EOF
                chmod +x "$HOME/Desktop/Mantri Trade Book.desktop"
                print_success "Desktop shortcut created"
            fi
            ;;
        "macos")
            # Create an app bundle for macOS
            mkdir -p "$HOME/Applications/Mantri Trade Book.app/Contents/MacOS"
            cat > "$HOME/Applications/Mantri Trade Book.app/Contents/Info.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>Mantri Trade Book</string>
    <key>CFBundleIdentifier</key>
    <string>com.mantri.tradebook</string>
    <key>CFBundleName</key>
    <string>Mantri Trade Book</string>
    <key>CFBundleVersion</key>
    <string>1.0</string>
</dict>
</plist>
EOF
            cat > "$HOME/Applications/Mantri Trade Book.app/Contents/MacOS/Mantri Trade Book" << EOF
#!/bin/bash
cd "$INSTALL_DIR"
./start.sh
EOF
            chmod +x "$HOME/Applications/Mantri Trade Book.app/Contents/MacOS/Mantri Trade Book"
            print_success "Application bundle created in Applications folder"
            ;;
        "windows")
            # Create a simple batch file shortcut
            cat > "$HOME/Desktop/Mantri Trade Book.bat" << EOF
@echo off
cd /d "$INSTALL_DIR"
start.bat
EOF
            print_success "Desktop shortcut created"
            ;;
    esac
}

# Function to print installation summary
print_summary() {
    print_success "Installation completed successfully!"
    echo
    echo "==================== INSTALLATION SUMMARY ===================="
    echo "Application installed to: $INSTALL_DIR"
    echo "Operating System: $DISTRO"
    echo "Python Version: $($PYTHON_CMD --version 2>&1 | awk '{print $2}')"
    echo
    echo "==================== HOW TO START ===================="
    case $OS in
        "linux"|"macos")
            echo "1. Run: cd $INSTALL_DIR && ./start.sh"
            if [[ "$OS" == "linux" ]] && command_exists systemctl; then
                echo "2. Or as service: sudo systemctl start TradeBook"
            fi
            ;;
        "windows")
            echo "1. Double-click: $INSTALL_DIR/start.bat"
            echo "2. Or run from command line: cd $INSTALL_DIR && start.bat"
            ;;
    esac
    echo
    echo "The application will be available at: http://localhost:5001"
    echo
    echo "==================== CONFIGURATION ===================="
    echo "Configuration file: $INSTALL_DIR/.env"
    echo "Database location: $INSTALL_DIR/instance/mantri_trade_book.db"
    echo "Logs directory: $INSTALL_DIR/logs/"
    echo
    echo "==================== UNINSTALL ===================="
    echo "To uninstall, simply delete the directory: $INSTALL_DIR"
    if [[ "$OS" == "linux" ]] && command_exists systemctl; then
        echo "And remove the service: sudo systemctl disable TradeBook && sudo rm /etc/systemd/system/TradeBook.service"
    fi
    echo "============================================================"
}

# Main installation function
main() {
    echo "==================== MANTRI TRADE BOOK INSTALLER ===================="
    echo "This installer will set up Mantri Trade Book on your system."
    echo "Supported platforms: Linux, macOS, Windows (WSL/Git Bash)"
    echo "======================================================================"
    echo
    
    detect_os
    print_status "Detected OS: $DISTRO"
    
    check_prerequisites
    create_install_dir
    copy_application
    create_virtual_env
    install_dependencies
    setup_database
    create_startup_scripts
    
    # Optional components
    read -p "Install as system service? (Linux only) [y/N]: " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        install_service
    fi
    
    read -p "Create desktop shortcut? [y/N]: " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        create_desktop_shortcut
    fi
    
    print_summary
}

# Run main function
main "$@"