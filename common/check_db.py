import os
import sys
from pathlib import Path

# Add the parent directory to the Python path
sys.path.append(str(Path(__file__).parent.parent))

from common.models import User
from common.database import SessionLocal, DATABASE_URL

def check_db():
    print("Checking database setup...")
    print(f"Database URL: {DATABASE_URL}")
    
    db = SessionLocal()
    try:
        # Check if admin user exists
        admin_email = "lamachine.geo@gmail.com"
        admin_user = db.query(User).filter(User.email == admin_email).first()
        
        if admin_user:
            print(f"Found admin user: {admin_user.email}")
            print(f"Account active: {admin_user.is_active}")
            print(f"Last login: {admin_user.last_login}")
            print(f"Has password hash: {'Yes' if admin_user.password_hash else 'No'}")
            print(f"Password hash: {admin_user.password_hash[:20]}...")
        else:
            print("Admin user not found!")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check_db() 