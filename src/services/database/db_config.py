import os
from dotenv import load_dotenv
from supabase import create_client, Client
import logging

load_dotenv()

LOGGER = logging.getLogger(__name__)

class DatabaseConfig:
    """Handles database configuration and client initialization."""
    
    def __init__(self):
        self.url = os.getenv("SUPABASE_URL")
        self.key = os.getenv("SUPABASE_KEY")
        
        if not self.url or not self.key:
            raise ValueError("Missing Supabase credentials in .env file")
        
        self.client: Client = self._create_client()

    def _create_client(self) -> Client:
        """Create and return a Supabase client."""
        try:
            LOGGER.debug("Creating Supabase client")
            client = create_client(self.url, self.key)
            LOGGER.info("Supabase client created successfully")
            return client
        except Exception as e:
            LOGGER.error(f"Failed to create Supabase client: {e}", exc_info=True)
            raise RuntimeError("Failed to initialize database client") from e

    def get_client(self) -> Client:
        """Return the initialized Supabase client."""
        return self.client