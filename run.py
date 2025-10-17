#!/usr/bin/env python3
"""
Quick start script for Mantri Trade Book
"""
import os
import sys
import subprocess

def check_requirements():
    """Check if all requirements are met"""
    print("🔍 Checking requirements...")
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        return False
    
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} detected")
    
    # Check if virtual environment exists
    if not os.path.exists('venv'):
        print("❌ Virtual environment not found. Please run setup.sh first")
        return False
    
    print("✅ Virtual environment found")
    
    # Check if database exists
    if not os.path.exists('mantri_trade_book.db'):
        print("🗄️  Database not found. Initializing...")
        try:
            # Activate venv and run init_db.py
            if os.name == 'nt':  # Windows
                subprocess.run(['venv\\Scripts\\python.exe', 'init_db.py'], check=True)
            else:  # Unix/Linux/MacOS
                subprocess.run(['./venv/bin/python', 'init_db.py'], check=True)
            print("✅ Database initialized")
        except subprocess.CalledProcessError:
            print("❌ Failed to initialize database")
            return False
    else:
        print("✅ Database found")
    
    return True

def start_application():
    """Start the Flask application"""
    print("\n🚀 Starting Mantri Trade Book...")
    print("📱 Application will be available at: http://localhost:5000")
    print("⏹️  Press Ctrl+C to stop the application\n")
    
    try:
        if os.name == 'nt':  # Windows
            subprocess.run(['venv\\Scripts\\python.exe', 'app.py'])
        else:  # Unix/Linux/MacOS
            subprocess.run(['./venv/bin/python', 'app.py'])
    except KeyboardInterrupt:
        print("\n\n⏹️  Application stopped by user")
    except Exception as e:
        print(f"\n❌ Error starting application: {e}")

def main():
    """Main function"""
    print("🎯 Mantri Trade Book - Quick Start")
    print("=" * 40)
    
    if not check_requirements():
        print("\n💡 Please run './setup.sh' first to set up the application")
        return
    
    print("\n✅ All requirements met!")
    start_application()

if __name__ == '__main__':
    main()