#!/bin/bash

# Mantri Trade Book - Docker Deployment Script
# This script helps deploy the application using Docker and Docker Compose

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
COMPOSE_FILE="docker-compose.yml"
ENV_FILE=".env"

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

# Function to check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    if ! command_exists docker; then
        print_error "Docker is not installed. Please install Docker first."
        print_status "Visit: https://docs.docker.com/get-docker/"
        exit 1
    fi
    
    if ! command_exists docker-compose && ! docker compose version >/dev/null 2>&1; then
        print_error "Docker Compose is not available. Please install Docker Compose."
        print_status "Visit: https://docs.docker.com/compose/install/"
        exit 1
    fi
    
    # Check if Docker daemon is running
    if ! docker info >/dev/null 2>&1; then
        print_error "Docker daemon is not running. Please start Docker."
        exit 1
    fi
    
    print_success "Prerequisites satisfied"
}

# Function to setup environment file
setup_environment() {
    print_status "Setting up environment configuration..."
    
    if [ ! -f "$ENV_FILE" ]; then
        if [ -f ".env.example" ]; then
            cp .env.example "$ENV_FILE"
            print_status "Copied .env.example to .env"
        else
            cat > "$ENV_FILE" << EOF
# Security
SECRET_KEY=$(openssl rand -hex 32 2>/dev/null || python3 -c "import secrets; print(secrets.token_hex(32))" 2>/dev/null || echo "change-me-$(date +%s)")
ENCRYPTION_KEY=$(openssl rand -hex 16 2>/dev/null || python3 -c "import secrets; print(secrets.token_hex(16))" 2>/dev/null || echo "change-me-$(date +%s)")

# Database
POSTGRES_PASSWORD=$(openssl rand -base64 32 2>/dev/null || echo "change-me-strong-password")

# Application settings
FLASK_ENV=production
DEBUG=False
EOF
            print_status "Created new .env file"
        fi
        
        print_warning "Please review and update the .env file with your desired settings"
        print_warning "Especially update the SECRET_KEY, ENCRYPTION_KEY, and POSTGRES_PASSWORD"
    else
        print_success "Environment file already exists"
    fi
}

# Function to build and start services
start_services() {
    print_status "Building and starting services..."
    
    # Use docker-compose or docker compose based on availability
    if command_exists docker-compose; then
        COMPOSE_CMD="docker-compose"
    else
        COMPOSE_CMD="docker compose"
    fi
    
    # Build images
    print_status "Building Docker images..."
    $COMPOSE_CMD build
    
    # Start services
    print_status "Starting services..."
    $COMPOSE_CMD up -d
    
    # Wait for services to be ready
    print_status "Waiting for services to be ready..."
    sleep 10
    
    # Check if services are running
    if $COMPOSE_CMD ps | grep -q "Up"; then
        print_success "Services started successfully"
    else
        print_error "Some services failed to start"
        $COMPOSE_CMD logs
        exit 1
    fi
}

# Function to stop services
stop_services() {
    print_status "Stopping services..."
    
    if command_exists docker-compose; then
        COMPOSE_CMD="docker-compose"
    else
        COMPOSE_CMD="docker compose"
    fi
    
    $COMPOSE_CMD down
    print_success "Services stopped"
}

# Function to show logs
show_logs() {
    if command_exists docker-compose; then
        COMPOSE_CMD="docker-compose"
    else
        COMPOSE_CMD="docker compose"
    fi
    
    $COMPOSE_CMD logs -f
}

# Function to show status
show_status() {
    if command_exists docker-compose; then
        COMPOSE_CMD="docker-compose"
    else
        COMPOSE_CMD="docker compose"
    fi
    
    print_status "Service status:"
    $COMPOSE_CMD ps
    
    print_status "Application health:"
    if curl -f http://localhost:5000/health >/dev/null 2>&1; then
        print_success "Application is healthy"
    else
        print_warning "Application may not be ready yet"
    fi
}

# Function to backup data
backup_data() {
    print_status "Creating backup..."
    
    BACKUP_DIR="backup_$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$BACKUP_DIR"
    
    # Backup environment file
    cp .env "$BACKUP_DIR/" 2>/dev/null || true
    
    # Backup Docker volumes
    docker run --rm -v mantri_trade_book_postgres_data:/data -v "$(pwd)/$BACKUP_DIR":/backup alpine tar czf /backup/postgres_data.tar.gz -C /data .
    docker run --rm -v mantri_trade_book_redis_data:/data -v "$(pwd)/$BACKUP_DIR":/backup alpine tar czf /backup/redis_data.tar.gz -C /data .
    
    print_success "Backup created in $BACKUP_DIR"
}

# Function to restore data
restore_data() {
    if [ -z "$1" ]; then
        print_error "Please specify backup directory"
        exit 1
    fi
    
    BACKUP_DIR="$1"
    
    if [ ! -d "$BACKUP_DIR" ]; then
        print_error "Backup directory $BACKUP_DIR not found"
        exit 1
    fi
    
    print_status "Restoring from backup: $BACKUP_DIR"
    
    # Stop services first
    stop_services
    
    # Restore environment file
    cp "$BACKUP_DIR/.env" . 2>/dev/null || true
    
    # Restore Docker volumes
    if [ -f "$BACKUP_DIR/postgres_data.tar.gz" ]; then
        docker run --rm -v mantri_trade_book_postgres_data:/data -v "$(pwd)/$BACKUP_DIR":/backup alpine tar xzf /backup/postgres_data.tar.gz -C /data
    fi
    
    if [ -f "$BACKUP_DIR/redis_data.tar.gz" ]; then
        docker run --rm -v mantri_trade_book_redis_data:/data -v "$(pwd)/$BACKUP_DIR":/backup alpine tar xzf /backup/redis_data.tar.gz -C /data
    fi
    
    print_success "Restore completed"
}

# Function to update application
update_application() {
    print_status "Updating application..."
    
    # Pull latest images
    if command_exists docker-compose; then
        COMPOSE_CMD="docker-compose"
    else
        COMPOSE_CMD="docker compose"
    fi
    
    $COMPOSE_CMD pull
    $COMPOSE_CMD build --no-cache
    $COMPOSE_CMD up -d
    
    print_success "Application updated"
}

# Function to cleanup
cleanup() {
    print_status "Cleaning up Docker resources..."
    
    if command_exists docker-compose; then
        COMPOSE_CMD="docker-compose"
    else
        COMPOSE_CMD="docker compose"
    fi
    
    $COMPOSE_CMD down -v --remove-orphans
    docker system prune -f
    
    print_success "Cleanup completed"
}

# Function to show help
show_help() {
    echo "Mantri Trade Book - Docker Deployment Script"
    echo
    echo "Usage: $0 [COMMAND]"
    echo
    echo "Commands:"
    echo "  start     Build and start all services (default)"
    echo "  stop      Stop all services"
    echo "  restart   Restart all services"
    echo "  status    Show service status"
    echo "  logs      Show service logs"
    echo "  backup    Create a backup of data"
    echo "  restore   Restore from backup (requires backup directory)"
    echo "  update    Update application to latest version"
    echo "  cleanup   Remove all containers and volumes"
    echo "  help      Show this help message"
    echo
    echo "Examples:"
    echo "  $0 start"
    echo "  $0 backup"
    echo "  $0 restore backup_20231214_143022"
    echo
}

# Main function
main() {
    # Change to script directory
    cd "$(dirname "$0")"
    
    case "${1:-start}" in
        "start")
            check_prerequisites
            setup_environment
            start_services
            echo
            print_success "Mantri Trade Book is now running!"
            print_status "Access the application at: http://localhost:5000"
            print_status "Use '$0 logs' to view application logs"
            print_status "Use '$0 stop' to stop the application"
            ;;
        "stop")
            stop_services
            ;;
        "restart")
            stop_services
            sleep 2
            start_services
            ;;
        "status")
            show_status
            ;;
        "logs")
            show_logs
            ;;
        "backup")
            backup_data
            ;;
        "restore")
            restore_data "$2"
            ;;
        "update")
            update_application
            ;;
        "cleanup")
            read -p "This will remove all data. Are you sure? [y/N]: " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                cleanup
            else
                print_status "Cleanup cancelled"
            fi
            ;;
        "help"|"-h"|"--help")
            show_help
            ;;
        *)
            print_error "Unknown command: $1"
            echo
            show_help
            exit 1
            ;;
    esac
}

# Run main function
main "$@"