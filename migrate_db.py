"""
Database utilities for TradeBook
This script provides database backup and restore functionality
"""
import os
import shutil
import sqlite3
from datetime import datetime
from flask import Flask

def create_app():
    """Create Flask app with database configuration"""
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL') or 'sqlite:///mantri_trade_book.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    from models.database import db
    db.init_app(app)
    
    return app, db

def backup_database():
    """Create a backup of the current database"""
    db_file = 'mantri_trade_book.db'
    
    if not os.path.exists(db_file):
        print("❌ No database file found to backup")
        return False
    
    # Create backup filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = f'mantri_trade_book_backup_{timestamp}.db'
    
    try:
        shutil.copy2(db_file, backup_file)
        print(f"✅ Database backed up to: {backup_file}")
        return backup_file
    except Exception as e:
        print(f"❌ Backup failed: {e}")
        return False

def restore_database(backup_file):
    """Restore database from backup"""
    if not os.path.exists(backup_file):
        print(f"❌ Backup file {backup_file} not found")
        return False
    
    db_file = 'mantri_trade_book.db'
    
    try:
        # Create backup of current database if it exists
        if os.path.exists(db_file):
            current_backup = backup_database()
            if current_backup:
                print(f"📦 Current database backed up as: {current_backup}")
        
        # Restore from backup
        shutil.copy2(backup_file, db_file)
        print(f"✅ Database restored from: {backup_file}")
        return True
    except Exception as e:
        print(f"❌ Restore failed: {e}")
        return False

def verify_database():
    """Verify database integrity and show basic info"""
    db_file = 'mantri_trade_book.db'
    
    if not os.path.exists(db_file):
        print("❌ No database file found")
        return False
    
    try:
        app, db = create_app()
        
        with app.app_context():
            from models.database import Account, Position, Trade
            
            # Check database connectivity and basic stats
            accounts_count = Account.query.count()
            positions_count = Position.query.count()
            trades_count = Trade.query.count()
            
            print("📊 Database Statistics:")
            print(f"   Accounts: {accounts_count}")
            print(f"   Positions: {positions_count}")
            print(f"   Trades: {trades_count}")
            
            # Show active accounts
            active_accounts = Account.query.filter_by(is_active=True).all()
            if active_accounts:
                print("\n🔧 Active Accounts:")
                for account in active_accounts:
                    print(f"   - {account.name} ({account.provider})")
            
            print("✅ Database verification completed")
            return True
            
    except Exception as e:
        print(f"❌ Database verification failed: {e}")
        return False

def reset_database():
    """Reset database to fresh state"""
    print("⚠️  WARNING: This will delete ALL data in the database!")
    response = input("Are you sure you want to continue? Type 'RESET' to confirm: ")
    
    if response != 'RESET':
        print("❌ Database reset cancelled")
        return False
    
    # Create backup first
    backup_file = backup_database()
    if backup_file:
        print(f"📦 Backup created: {backup_file}")
    
    # Remove existing database
    db_file = 'mantri_trade_book.db'
    if os.path.exists(db_file):
        os.remove(db_file)
        print("🗑️  Removed existing database")
    
    # Reinitialize
    try:
        from init_db import init_fresh_database
        success = init_fresh_database()
        if success:
            print("✅ Database reset completed!")
        return success
    except Exception as e:
        print(f"❌ Database reset failed: {e}")
        return False

def main():
    """Main function with command-line interface"""
    import sys
    
    if len(sys.argv) < 2:
        print("🔧 TradeBook Database Utilities")
        print("=" * 30)
        print("Usage: python migrate_db.py <command>")
        print("")
        print("Commands:")
        print("  backup          - Create database backup")
        print("  restore <file>  - Restore from backup file")
        print("  verify          - Verify database integrity")
        print("  reset           - Reset database (WARNING: deletes all data)")
        print("")
        print("Examples:")
        print("  python migrate_db.py backup")
        print("  python migrate_db.py restore mantri_trade_book_backup_20241015_120000.db")
        print("  python migrate_db.py verify")
        return
    
    command = sys.argv[1].lower()
    
    if command == 'backup':
        backup_database()
    elif command == 'restore':
        if len(sys.argv) < 3:
            print("❌ Please specify backup file to restore from")
            return
        restore_database(sys.argv[2])
    elif command == 'verify':
        verify_database()
    elif command == 'reset':
        reset_database()
    else:
        print(f"❌ Unknown command: {command}")

if __name__ == '__main__':
    main()