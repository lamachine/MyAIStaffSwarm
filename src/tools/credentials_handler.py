import os
import pickle
from functools import lru_cache
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Define the scopes required by your application.
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/gmail.labels',
    'https://www.googleapis.com/auth/calendar',        # Full access
    'https://www.googleapis.com/auth/calendar.events'  # Read/write events
]

@lru_cache(maxsize=1)
def get_credentials() -> Credentials:
    """
    Retrieves valid Google API credentials.
    Checks for a token file (configured via environment variables) and refreshes or creates
    credentials using OAuth flow if needed.
    """
    token_file = os.getenv("GOOGLE_TOKEN_FILE", "token.pickle")
    credentials_file = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")
    creds = None

    # Load credentials from token file if it exists.
    if os.path.exists(token_file):
        with open(token_file, "rb") as token:
            creds = pickle.load(token)

    # If credentials are not available or not valid, perform OAuth flow.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open(token_file, "wb") as token:
            pickle.dump(creds, token)
    return creds 