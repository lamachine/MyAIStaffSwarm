from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get database configuration from environment variables with defaults
# Use 'postgres' as host when running in Docker, 'localhost' otherwise
DB_HOST = os.getenv('POSTGRES_HOST', 'postgres')  # Service name in docker-compose
DB_PORT = os.getenv('POSTGRES_PORT', '5433')  # External port in docker-compose
DB_NAME = os.getenv('POSTGRES_DB', 'agentswarm')
DB_USER = os.getenv('POSTGRES_USER', 'agentswarm')
DB_PASS = os.getenv('POSTGRES_PASSWORD', 'spac3bunny')

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:5432/{DB_NAME}"  # Use internal port 5432

logger.info(f"Connecting to database at {DB_HOST}:{DB_PORT}/{DB_NAME}")
engine = create_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        logger.info("Creating new database session")
        yield db
    finally:
        logger.info("Closing database session")
        db.close() 