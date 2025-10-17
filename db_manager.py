#!/usr/bin/env python3
"""
Simple database management script for TradeBook
Provides commands for database initialization, backup, and utilities
"""
import os
import sys
import subprocess
from datetime import datetime

def run_command(command, description):
    """Run a command and print status"""
    print(f"🔧 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e}")
        if e.stderr:
            print(f"Error: {e.stderr}")
        return False

def init_database():
    """Initialize a fresh database"""
    print("🗄️  Initializing fresh database...")
    
    # Check if database exists
    if os.path.exists('mantri_trade_book.db'):
        print("⚠️  Warning: Database already exists!")
        response = input("Do you want to recreate it? This will delete all data! (y/N): ")
        if response.lower() != 'y':
            print("❌ Database initialization cancelled")
            return False
    
    # Run init_db.py
    if run_command("python init_db.py --force", "Database initialization"):
        print("\n🎉 Database initialization completed!")
        print("💡 You can now start the application with: python app.py")
        return True
    return False

def backup_database():
    """Create a backup of the database"""
    if not os.path.exists('mantri_trade_book.db'):
        print("❌ No database found to backup")
        return False
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_name = f'backup_mantri_trade_book_{timestamp}.db'
    
    if run_command(f"cp mantri_trade_book.db {backup_name}", "Database backup"):
        print(f"📦 Backup created: {backup_name}")
        return True
    return False

def verify_database():
    """Verify database integrity"""
    if not os.path.exists('mantri_trade_book.db'):
        print("❌ No database found")
        return False
    
    return run_command("python migrate_db.py verify", "Database verification")

def show_help():
    """Show help information"""
    print("🎯 TradeBook Database Manager")
    print("=" * 30)
    print("Usage: python db_manager.py <command>")
    print("")
    print("Commands:")
    print("  init     - Initialize fresh database (will prompt if exists)")
    print("  backup   - Create database backup")
    print("  verify   - Verify database integrity and show stats")
    print("  help     - Show this help message")
    print("")
    print("Examples:")
    print("  python db_manager.py init")
    print("  python db_manager.py backup")
    print("  python db_manager.py verify")

def main():
    """Main function"""
    if len(sys.argv) < 2:
        show_help()
        return
    
    command = sys.argv[1].lower()
    
    if command == 'init':
        init_database()
    elif command == 'backup':
        backup_database()
    elif command == 'verify':
        verify_database()
    elif command == 'help':
        show_help()
    else:
        print(f"❌ Unknown command: {command}")
        show_help()

if __name__ == '__main__':
    main()