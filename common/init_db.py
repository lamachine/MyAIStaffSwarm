from models import Base, User
from database import engine, SessionLocal
import os

def init_db():
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    # Create admin user
    db = SessionLocal()
    try:
        # Check if admin user exists
        admin_email = "lamachine.geo@gmail.com"
        existing_admin = db.query(User).filter(User.email == admin_email).first()
        
        if not existing_admin:
            admin_user = User(
                email=admin_email,
                is_active=True
            )
            # Use the environment variable for admin password
            admin_user.set_password(os.getenv("ADMIN_PASSWORD", "change_this_password"))
            db.add(admin_user)
            db.commit()
            print(f"Admin user created with email: {admin_email}")
        else:
            print(f"Admin user already exists with email: {admin_email}")
            
    finally:
        db.close()

if __name__ == "__main__":
    init_db() 