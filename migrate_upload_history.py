#!/usr/bin/env python3
"""
Migration script to add UploadHistory table to the database
"""

import os
import sys
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

# Add the current directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models.database import db, UploadHistory
from config import Config

def create_app():
    """Create Flask app for migration"""
    app = Flask(__name__)
    
    # Use existing database URL or default to SQLite
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL') or 'sqlite:///mantri_trade_book.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    db.init_app(app)
    return app

def migrate_database():
    """Add UploadHistory table to existing database"""
    app = create_app()
    
    with app.app_context():
        try:
            # Check if the table already exists
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            existing_tables = inspector.get_table_names()
            
            if 'upload_history' in existing_tables:
                print("UploadHistory table already exists.")
                return
            
            print("Creating UploadHistory table...")
            
            # Create the new table
            db.create_all()
            
            print("✅ UploadHistory table created successfully!")
            print("\nTable structure:")
            print("- id: Primary key")
            print("- account_id: Foreign key to accounts table")
            print("- filename: Unique filename for stored file")
            print("- original_filename: Original uploaded filename")
            print("- file_size: File size in bytes")
            print("- file_type: Type of file (csv, xlsx, etc.)")
            print("- upload_timestamp: When file was uploaded")
            print("- upload_status: Status (pending, processing, completed, failed)")
            print("- total_rows: Total rows in file")
            print("- successful_imports: Number of successful imports")
            print("- failed_imports: Number of failed imports")
            print("- error_message: Error details if failed")
            print("- processing_started_at: When processing started")
            print("- processing_completed_at: When processing completed")
            print("- import_source: Source type (robinhood, fidelity, etc.)")
            print("- notes: Additional notes")
            print("- created_at: Record creation timestamp")
            
        except Exception as e:
            print(f"❌ Error creating UploadHistory table: {str(e)}")
            raise

if __name__ == '__main__':
    migrate_database()