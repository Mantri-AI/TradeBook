"""
Database initialization script for TradeBook
Creates a fresh database with all tables and optional sample data.
"""
import os
import sys
from flask import Flask

def create_app():
    """Create Flask app with database configuration"""
    app = Flask(__name__)
    
    # Configuration
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL') or 'sqlite:///mantri_trade_book.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize database with app
    from models.database import db
    db.init_app(app)
    
    return app, db

def init_fresh_database():
    """Initialize a fresh database with all tables"""
    app, db = create_app()
    
    with app.app_context():
        # Import all models to register them with SQLAlchemy
        from models.database import Account, Position, Trade, StockData, OptionData, TradingSession
        
        print("🗄️  Initializing fresh database...")
        
        # Drop all existing tables (if any)
        db.drop_all()
        print("✅ Dropped existing tables (if any)")
        
        # Create all tables from scratch
        db.create_all()
        print("✅ Created all database tables")
        
        # Create sample data if requested
        create_sample_data(db)
        
        print("🎉 Database initialization completed successfully!")
        return True

def create_sample_data(db):
    """Create sample data for testing (optional)"""
    from models.database import Account
    
    try:
        # Check if we already have data
        existing_account = Account.query.first()
        if existing_account:
            print("📊 Existing data found, skipping sample data creation...")
            return
        
        # Create a sample demo account
        demo_account = Account(
            name="Demo Trading Account",
            provider="robinhood",
            username="demo@tradebook.com",
            authentication_type="manual",
            is_active=False,  # Inactive by default for safety
            buying_power=10000.00,
            total_portfolio_value=15000.00,
            account_number="DEMO123456"
        )
        
        db.session.add(demo_account)
        db.session.commit()
        
        print("✅ Created sample demo account")
        print("📝 You can activate it later or create new accounts through the web interface")
        
    except Exception as e:
        print(f"⚠️  Warning: Could not create sample data: {e}")
        print("💡 This is normal - you can add accounts through the web interface")
        db.session.rollback()

def main():
    """Main function"""
    print("🎯 TradeBook Database Initialization")
    print("=" * 40)
    
    # Check if database file exists and warn user
    db_file = 'mantri_trade_book.db'
    if os.path.exists(db_file):
        print(f"⚠️  Warning: Database file '{db_file}' already exists!")
        if len(sys.argv) > 1 and sys.argv[1] == '--force':
            print("🔥 Force mode enabled - will recreate database")
        else:
            response = input("Do you want to recreate the database? This will delete all existing data! (y/N): ")
            if response.lower() != 'y':
                print("❌ Database initialization cancelled")
                return False
    
    try:
        success = init_fresh_database()
        if success:
            print("\n🚀 Database is ready!")
            print("💡 You can now start the application with: python app.py")
            print("🌐 Or use the quick start script: python run.py")
        return success
    except Exception as e:
        print(f"\n❌ Database initialization failed: {e}")
        return False

if __name__ == '__main__':
    main()