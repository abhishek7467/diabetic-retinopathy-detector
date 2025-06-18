#!/usr/bin/env python3
"""
Direct database creation script for the diabetic retinopathy detector
"""

from app import create_app
from app.models import db, User, ImageRecord
from werkzeug.security import generate_password_hash

def init_database():
    """Initialize the database with tables and sample data"""
    app = create_app()
    
    with app.app_context():
        # Drop all tables and recreate them
        db.drop_all()
        db.create_all()
        
        # Create admin user
        admin_user = User(
            name='Administrator',
            email='admin@retinopatia.com',
            is_admin=True
        )
        admin_user.set_password('admin123')
        
        # Create sample regular user
        sample_user = User(
            name='Dr. Jane Smith',
            email='jane.smith@hospital.com',
            is_admin=False
        )
        sample_user.set_password('password123')
        
        db.session.add(admin_user)
        db.session.add(sample_user)
        db.session.commit()
        
        print("✓ Database initialized successfully!")
        print("✓ Admin user created: admin@retinopatia.com / admin123")
        print("✓ Sample user created: jane.smith@hospital.com / password123")
        
        return True

if __name__ == '__main__':
    print("Initializing database for Diabetic Retinopathy Detector...")
    try:
        init_database()
        print("\n🎉 Database setup completed successfully!")
    except Exception as e:
        print(f"\n❌ Database setup failed: {e}")
