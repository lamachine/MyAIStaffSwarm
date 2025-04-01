import os
from google.oauth2 import service_account
from googleapiclient.discovery import build

class GoogleAPIClient:
    def __init__(self, service_account_file: str, scopes: list[str]):
        self.service_account_file = service_account_file
        self.scopes = scopes
        self.creds = service_account.Credentials.from_service_account_file(
            service_account_file, scopes=scopes
        )
        self.service = None

    def build_service(self, api_name: str, api_version: str):
        self.service = build(api_name, api_version, credentials=self.creds)
        return self.service

    def list_drive_files(self, page_size: int = 10) -> list[dict]:
        if not self.service:
            self.build_service("drive", "v3")
        results = self.service.files().list(
            pageSize=page_size, fields="files(id, name)"
        ).execute()
        return results.get("files", [])

# Demo if running standalone
if __name__ == "__main__":
    SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "path/to/service.json")
    SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
    client = GoogleAPIClient(SERVICE_ACCOUNT_FILE, SCOPES)
    drive_files = client.list_drive_files(page_size=5)
    print("Google Drive Files:", drive_files) 