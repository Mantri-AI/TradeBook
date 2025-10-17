"""
Database initialization and migration script
"""
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate, init, migrate, upgrade
import os
import sys

"""
Database initialization and migration script
"""
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate, init, migrate, upgrade
import os
import sys

def create_app():
    app = Flask(__name__)
    
    # Configuration
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///mantri_trade_book.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize database with app
    from models.database import db
    db.init_app(app)
    migrate_obj = Migrate(app, db)
    
    # Import models to register them
    from models.database import Account, Position, Trade, StockData, OptionData, TradingSession
    
    return app, db, migrate_obj

def init_database():
    """Initialize the database with tables"""
    app, db, migrate_obj = create_app()
    
    with app.app_context():
        # Create all tables
        db.create_all()
        print("Database tables created successfully!")
        
        # Create sample data if needed
        create_sample_data(db)

def create_sample_data(db):
    """Create some sample data for testing"""
    from models.database import Account
    
    try:
        # Check if we already have data
        existing_account = db.session.execute(db.select(Account)).first()
        if existing_account:
            print("Sample data already exists, skipping...")
            return
        
        # Create a sample account (without real credentials)
        sample_account = Account(
            name="Demo Account",
            username="demo@example.com",
            is_active=False,  # Inactive by default
            buying_power=10000.00,
            total_portfolio_value=15000.00
        )
        
        db.session.add(sample_account)
        db.session.commit()
        print("Sample data created successfully!")
    except Exception as e:
        print(f"Error creating sample data: {e}")
        print("This is normal for a fresh installation - you can add accounts through the web interface.")

if __name__ == '__main__':
    init_database()