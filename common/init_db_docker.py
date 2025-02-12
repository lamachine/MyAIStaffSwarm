import os
import sys
from pathlib import Path
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add the parent directory to the Python path
sys.path.append(str(Path(__file__).parent.parent))

from common.models import Base, User
from common.database import engine, SessionLocal

def init_db():
    try:
        logger.info("Checking database tables...")
        # Only create tables that don't exist
        Base.metadata.create_all(bind=engine)
        
        logger.info("Checking admin user...")
        db = SessionLocal()
        try:
            # Check if admin user exists
            admin_email = "lamachine.geo@gmail.com"
            existing_admin = db.query(User).filter(User.email == admin_email).first()
            
            if not existing_admin:
                logger.info("Creating admin user...")
                admin_user = User(
                    email=admin_email,
                    disabled=False,
                    created_at=datetime.utcnow()
                )
                # Set password
                admin_user.set_password("change_this_password")
                
                # Add and commit
                db.add(admin_user)
                db.commit()
                
                logger.info(f"Admin user created with email: {admin_email}")
                logger.info("Password set to: change_this_password")
                logger.info("Please change this password after first login!")
                
                # Verify the user was created
                created_user = db.query(User).filter(User.email == admin_email).first()
                if created_user and created_user.hashed_password:
                    logger.info("User creation verified successfully!")
                else:
                    raise Exception("User creation verification failed!")
            else:
                logger.info(f"Admin user already exists with email: {admin_email}")
                
        except Exception as e:
            logger.error(f"Database initialization error: {str(e)}")
            db.rollback()
            raise
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Fatal error during database initialization: {str(e)}")
        raise

if __name__ == "__main__":
    init_db() 