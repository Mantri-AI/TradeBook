#!/bin/bash

# Mantri Trade Book - Setup and Run Script

echo "🚀 Setting up Mantri Trade Book..."

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed. Please install Python 3 first."
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip

# Install requirements
echo "📚 Installing dependencies..."
pip install -r requirements.txt

# Initialize database
echo "🗄️  Initializing database..."
python init_db.py

# Set environment variables if .env file exists
if [ -f ".env" ]; then
    echo "🔐 Loading environment variables..."
    export $(cat .env | xargs)
fi

echo "✅ Setup completed successfully!"
echo ""
echo "🎯 To start the application:"
echo "   source venv/bin/activate"
echo "   python app.py"
echo ""
echo "📱 The application will be available at: http://localhost:5000"
echo ""
echo "🔒 Security Notice:"
echo "   - Remember to set proper encryption keys in production"
echo "   - Use environment variables for sensitive configuration"
echo "   - Enable HTTPS in production environments"