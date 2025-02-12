"""Store working files in the database."""

import asyncio
import logging
from db_service import DatabaseService
import os

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def store_working_files():
    """Store the working files in the database."""
    logger = logging.getLogger(__name__)
    db = DatabaseService()
    await db.initialize()
    
    # List of files to store
    files = [
        'services/ai_agent.py',
        'services/llm_service.py',
        'services/db_service.py',
        'services/webhook_service.py'
    ]
    
    try:
        for file_path in files:
            logger.info(f"Storing {file_path}...")
            
            # Read file content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Store in database
            metadata = {
                "type": "python_source",
                "relative_path": file_path
            }
            
            result = await db.store_file(file_path, content, metadata)
            logger.info(f"✓ Stored {file_path} (ID: {result['id']})")
            
        logger.info("✨ All files stored successfully!")
        
    except Exception as e:
        logger.error(f"Failed to store files: {str(e)}")
        raise
    finally:
        if hasattr(db, 'pool'):
            await db.pool.close()

if __name__ == "__main__":
    asyncio.run(store_working_files()) 