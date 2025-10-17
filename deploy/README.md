# Mantri Trade Book - Deployment Guide

This directory contains deployment scripts and configurations for the Mantri Trade Book Flask application. The deployment supports multiple platforms and deployment methods.

## Table of Contents

- [Quick Start](#quick-start)
- [Installation Methods](#installation-methods)
- [Docker Deployment](#docker-deployment)
- [Native Installation](#native-installation)
- [Configuration](#configuration)
- [Production Deployment](#production-deployment)
- [Troubleshooting](#troubleshooting)
- [Maintenance](#maintenance)

## Quick Start

### Docker (Recommended)
```bash
cd deploy
chmod +x docker-deploy.sh
./docker-deploy.sh start
```

### Native Installation
```bash
cd deploy
chmod +x install.sh
./install.sh
```

### Windows
```cmd
cd deploy
install.bat
```

## Installation Methods

### 1. Docker Deployment (Recommended for Production)

Docker deployment provides:
- Consistent environment across platforms
- Easy scaling and management
- Isolated dependencies
- Built-in database and caching

**Prerequisites:**
- Docker 20.0+
- Docker Compose v2.0+

**Quick Start:**
```bash
cd deploy
./docker-deploy.sh start
```

**Available Commands:**
```bash
./docker-deploy.sh start     # Start all services
./docker-deploy.sh stop      # Stop all services
./docker-deploy.sh restart   # Restart services
./docker-deploy.sh status    # Show service status
./docker-deploy.sh logs      # View logs
./docker-deploy.sh backup    # Create backup
./docker-deploy.sh restore   # Restore from backup
./docker-deploy.sh update    # Update application
./docker-deploy.sh cleanup   # Remove all data
```

### 2. Native Installation

Native installation provides:
- Direct system integration
- Lower resource usage
- Easier debugging
- System service integration (Linux)

**Supported Platforms:**
- Linux (Ubuntu, CentOS, RHEL, Debian)
- macOS (10.14+)
- Windows (10+, with Git Bash/WSL)

**Prerequisites:**
- Python 3.8+
- pip
- git (optional)

**Installation:**

**Linux/macOS:**
```bash
cd deploy
chmod +x install.sh
./install.sh
```

**Windows:**
```cmd
cd deploy
install.bat
```

## Docker Deployment

### Components

The Docker deployment includes:

1. **Flask Application** (TradeBook)
   - Main application container
   - Runs on port 5000
   - Includes health checks

2. **PostgreSQL Database** (db)
   - Production-ready database
   - Persistent data storage
   - Automatic backups

3. **Redis Cache** (redis)
   - Session storage
   - Caching layer
   - Background task queue

4. **Nginx Reverse Proxy** (nginx)
   - Load balancing
   - SSL termination
   - Static file serving
   - Rate limiting

### Configuration Files

- `docker-compose.yml` - Main orchestration file
- `Dockerfile` - Application container definition
- `nginx.conf` - Web server configuration
- `.env.example` - Environment variables template

### Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
# Security (REQUIRED - Generate strong keys)
SECRET_KEY=your-super-secret-key-here
ENCRYPTION_KEY=your-encryption-key-32-chars

# Database
POSTGRES_PASSWORD=your-strong-database-password

# Application
FLASK_ENV=production
DEBUG=False
```

### SSL/HTTPS Setup

1. Obtain SSL certificates (Let's Encrypt recommended)
2. Place certificates in `deploy/ssl/` directory
3. Update `nginx.conf` to enable HTTPS server block
4. Restart nginx: `./docker-deploy.sh restart`

## Native Installation

### Installation Process

The installer performs the following steps:

1. **System Check**
   - Detects operating system
   - Verifies Python version (3.8+)
   - Checks for required tools

2. **Environment Setup**
   - Creates installation directory
   - Sets up Python virtual environment
   - Installs dependencies

3. **Application Setup**
   - Copies application files
   - Creates configuration files
   - Initializes database

4. **Integration**
   - Creates startup scripts
   - Optionally installs system service (Linux)
   - Creates desktop shortcuts

### Directory Structure

After installation:
```
~/TradeBook/
├── app.py                 # Main application
├── config.py             # Configuration
├── requirements.txt      # Dependencies
├── models/               # Database models
├── services/            # Business logic
├── templates/           # HTML templates
├── static/              # CSS, JS, images
├── instance/            # Database and user data
├── logs/                # Application logs
├── venv/                # Python virtual environment
├── start.sh            # Unix startup script
├── start.bat           # Windows startup script
└── .env                # Environment configuration
```

### Starting the Application

**Linux/macOS:**
```bash
cd ~/TradeBook
./start.sh
```

**Windows:**
```cmd
cd %USERPROFILE%\TradeBook
start.bat
```

**As System Service (Linux):**
```bash
sudo systemctl start TradeBook
sudo systemctl enable TradeBook  # Auto-start on boot
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | Flask secret key | Generated |
| `ENCRYPTION_KEY` | Data encryption key | Generated |
| `DATABASE_URL` | Database connection string | SQLite local file |
| `FLASK_ENV` | Environment mode | production |
| `DEBUG` | Debug mode | False |

### Database Configuration

**SQLite (Default):**
```bash
DATABASE_URL=sqlite:///instance/mantri_trade_book.db
```

**PostgreSQL:**
```bash
DATABASE_URL=postgresql://user:password@host:port/database
```

**MySQL:**
```bash
DATABASE_URL=mysql://user:password@host:port/database
```

### Security Configuration

1. **Generate Strong Keys:**
```bash
# Secret key
python3 -c "import secrets; print(secrets.token_hex(32))"

# Encryption key
python3 -c "import secrets; print(secrets.token_hex(16))"
```

2. **Update .env file:**
```bash
SECRET_KEY=generated-secret-key
ENCRYPTION_KEY=generated-encryption-key
```

## Production Deployment

### Docker Production Setup

1. **Environment Preparation:**
```bash
# Copy and configure environment
cp .env.example .env
# Edit .env with production values
```

2. **SSL Certificate Setup:**
```bash
# Create SSL directory
mkdir -p ssl

# Copy your certificates
cp /path/to/cert.pem ssl/
cp /path/to/key.pem ssl/

# Update nginx.conf to enable HTTPS
```

3. **Deploy:**
```bash
./docker-deploy.sh start
```

4. **Verify Deployment:**
```bash
./docker-deploy.sh status
curl -f http://localhost/health
```

### Native Production Setup

1. **System Service (Linux):**
```bash
# Install as service during setup
./install.sh
# Answer 'y' when prompted for service installation

# Or manually install service
sudo cp TradeBook.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable TradeBook
sudo systemctl start TradeBook
```

2. **Reverse Proxy Setup:**
```nginx
# /etc/nginx/sites-available/TradeBook
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://127.0.0.1:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Performance Optimization

1. **Application Tuning:**
```bash
# Use production WSGI server
pip install gunicorn
gunicorn --workers 4 --bind 0.0.0.0:5001 app:app
```

2. **Database Optimization:**
```bash
# Use PostgreSQL for production
pip install psycopg2-binary
# Update DATABASE_URL in .env
```

3. **Caching:**
```bash
# Use Redis for session storage
pip install redis flask-session
# Configure in app settings
```

## Troubleshooting

### Common Issues

1. **Port Already in Use:**
```bash
# Check what's using the port
lsof -i :5000
# Kill the process or change port in configuration
```

2. **Permission Denied (Linux/macOS):**
```bash
# Make scripts executable
chmod +x install.sh docker-deploy.sh
```

3. **Python Not Found:**
```bash
# Install Python 3.8+
# Ubuntu/Debian:
sudo apt-get install python3 python3-pip python3-venv

# macOS:
brew install python3

# Windows: Download from python.org
```

4. **Docker Not Starting:**
```bash
# Check Docker daemon
systemctl status docker  # Linux
# Start Docker Desktop on Windows/macOS
```

### Logs and Debugging

**Docker Logs:**
```bash
./docker-deploy.sh logs
docker-compose logs TradeBook
```

**Native Installation Logs:**
```bash
# Application logs
tail -f ~/TradeBook/logs/app.log

# System service logs (Linux)
journalctl -u TradeBook -f
```

**Database Issues:**
```bash
# Check database connection
python3 -c "from app import app; app.app_context().push(); from models.database import db; print('DB OK' if db.engine.execute('SELECT 1').scalar() else 'DB ERROR')"
```

### Health Checks

1. **Application Health:**
```bash
curl http://localhost:5000/health
```

2. **Database Health:**
```bash
# SQLite
ls -la instance/mantri_trade_book.db

# PostgreSQL (Docker)
docker exec TradeBook-db pg_isready
```

3. **Service Status:**
```bash
# Docker
./docker-deploy.sh status

# Native (Linux)
systemctl status TradeBook
```

## Maintenance

### Backup and Restore

**Docker Backup:**
```bash
./docker-deploy.sh backup
# Creates timestamped backup directory
```

**Docker Restore:**
```bash
./docker-deploy.sh restore backup_20231214_143022
```

**Native Backup:**
```bash
# Backup database and configuration
tar -czf backup_$(date +%Y%m%d).tar.gz \
    ~/TradeBook/instance/ \
    ~/TradeBook/.env
```

### Updates

**Docker Update:**
```bash
./docker-deploy.sh update
```

**Native Update:**
```bash
# Backup first
cd ~/TradeBook
# Download new version and replace files
# Restart application
```

### Monitoring

1. **Resource Usage:**
```bash
# Docker
docker stats

# Native
htop
ps aux | grep python
```

2. **Application Metrics:**
- Monitor logs for errors
- Check response times
- Monitor database size
- Track user activity

### Security Maintenance

1. **Regular Updates:**
```bash
# Update dependencies
pip install --upgrade -r requirements.txt

# Update Docker images
docker-compose pull
```

2. **Key Rotation:**
```bash
# Generate new keys periodically
# Update .env file
# Restart application
```

3. **Access Logs:**
```bash
# Monitor for suspicious activity
tail -f logs/access.log | grep -E "(401|403|404|500)"
```

## Support

For issues and questions:

1. Check this documentation
2. Review application logs
3. Check the main application README
4. File issues in the project repository

## License

This deployment package is part of the Mantri Trade Book application. See the main LICENSE file for details.