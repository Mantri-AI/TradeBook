#!/usr/bin/env python3
"""
Migration script to add ImportHistory table
"""

from app import app
from models.database import db, ImportHistory

def migrate():
    """Add ImportHistory table"""
    with app.app_context():
        try:
            # Create the ImportHistory table
            db.create_all()
            print("✅ ImportHistory table created successfully")
            
            # Check if table was created
            inspector = db.inspect(db.engine)
            if 'import_history' in inspector.get_table_names():
                print("✅ Confirmed: import_history table exists")
            else:
                print("❌ Error: import_history table not found")
                
        except Exception as e:
            print(f"❌ Error creating ImportHistory table: {str(e)}")

if __name__ == '__main__':
    migrate()