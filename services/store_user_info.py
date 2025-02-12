"""Store user information from prompts in the database."""

import asyncio
import logging
from db_service import DatabaseService
import uuid
import re

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def parse_user_info(prompt_text: str) -> dict:
    """Parse user information from the prompt text."""
    info = {}
    
    # Extract OS version
    os_match = re.search(r"user's OS version is ([^.]+)", prompt_text)
    if os_match:
        info['os_version'] = os_match.group(1)
        
    # Extract workspace path
    workspace_match = re.search(r"absolute path of the user's workspace is ([^.]+)", prompt_text)
    if workspace_match:
        info['workspace_path'] = workspace_match.group(1)
        
    # Extract shell path
    shell_match = re.search(r"user's shell is ([^.]+)", prompt_text)
    if shell_match:
        info['shell_path'] = shell_match.group(1)
        
    # Extract name
    name_match = re.search(r"my name is ([^.]+)", prompt_text, re.IGNORECASE)
    if name_match:
        info['name'] = name_match.group(1).strip()
        
    # Extract expertise level
    expertise_match = re.search(r"expertise level is ([^.]+)", prompt_text, re.IGNORECASE)
    if expertise_match:
        info['expertise_level'] = expertise_match.group(1).strip()
        
    # Extract goals
    goals_match = re.search(r"goals? (?:is|are) ([^.]+)", prompt_text, re.IGNORECASE)
    if goals_match:
        info['goals'] = goals_match.group(1).strip()
        
    return info

async def store_user_info_from_prompt(prompt_text: str):
    """Store user information from the prompt in the database."""
    logger = logging.getLogger(__name__)
    db = DatabaseService()
    await db.initialize()
    
    try:
        # Parse user info from prompt
        info = parse_user_info(prompt_text)
        
        # Generate a session ID
        session_id = str(uuid.uuid4())
        
        # Store in database
        result = await db.store_user_info(
            session_id=session_id,
            name=info.get('name'),
            expertise_level=info.get('expertise_level'),
            goals=info.get('goals'),
            os_version=info.get('os_version'),
            workspace_path=info.get('workspace_path'),
            shell_path=info.get('shell_path')
        )
        
        logger.info(f"✓ Stored user info (Session ID: {session_id})")
        logger.info(f"Name: {info.get('name', 'Not set')}")
        logger.info(f"Expertise: {info.get('expertise_level', 'Not set')}")
        logger.info(f"Goals: {info.get('goals', 'Not set')}")
        logger.info(f"OS Version: {info.get('os_version')}")
        logger.info(f"Workspace: {info.get('workspace_path')}")
        logger.info(f"Shell: {info.get('shell_path')}")
        
    except Exception as e:
        logger.error(f"Failed to store user info: {str(e)}")
        raise
    finally:
        if hasattr(db, 'pool'):
            await db.pool.close()

if __name__ == "__main__":
    # Example prompt text
    prompt = """
    The user's OS version is win32 10.0.22631. 
    The absolute path of the user's workspace is /c%3A/Users/Owner/Documents/GitHub/cursor_test/LTB2/Email_Assist/Email_assist_current. 
    The user's shell is C:\WINDOWS\System32\WindowsPowerShell\v1.0\powershell.exe.
    """
    
    asyncio.run(store_user_info_from_prompt(prompt)) 