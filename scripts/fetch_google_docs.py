import os
import sys
from pathlib import Path
import pickle
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from metadata_utils import generate_metadata, save_with_metadata

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io

load_dotenv()

# Configuration
RAW_DOCS_DIR = Path(__file__).parent.parent / "data" / "raw_docs"
GOOGLE_DOCS_DIR = RAW_DOCS_DIR / "google_docs"
CREDENTIALS_DIR = Path(__file__).parent.parent / "credentials"
TOKEN_FILE = CREDENTIALS_DIR / "token.pickle"

# Create directories if they don't exist
RAW_DOCS_DIR.mkdir(parents=True, exist_ok=True)
GOOGLE_DOCS_DIR.mkdir(parents=True, exist_ok=True)
CREDENTIALS_DIR.mkdir(parents=True, exist_ok=True)

# OAuth2 scopes
SCOPES = ['https://www.googleapis.com/auth/drive.readonly', 'https://www.googleapis.com/auth/documents.readonly']

def get_credentials():
    """Get or refresh OAuth2 credentials"""
    creds = None
    
    # Load existing token if available
    if TOKEN_FILE.exists():
        with open(TOKEN_FILE, 'rb') as token:
            creds = pickle.load(token)
    
    # If there are no (valid) credentials, let the user log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            client_secrets_file = CREDENTIALS_DIR / "client_secret.json"
            if not client_secrets_file.exists():
                raise FileNotFoundError(
                    f"OAuth credentials not found at {client_secrets_file}. "
                    "Please download client_secret.json from Google Cloud Console and place it in the credentials directory."
                )
            
            flow = InstalledAppFlow.from_client_secrets_file(
                str(client_secrets_file), SCOPES
            )
            creds = flow.run_local_server(port=0)
        
        # Save the credentials for the next run
        with open(TOKEN_FILE, 'wb') as token:
            pickle.dump(creds, token)
    
    return creds

def list_google_docs(drive_service):
    """List all Google Docs in the user's Drive"""
    results = drive_service.files().list(
        q="mimeType='application/vnd.google-apps.document'",
        fields="files(id, name, modifiedTime, owners)",
        pageSize=100
    ).execute()
    
    files = results.get('files', [])
    print(f"Found {len(files)} Google Docs")
    return files

def export_google_doc(drive_service, doc_id, doc_name, modified_time=None, owners=None):
    """Export a Google Doc to plain text with metadata"""
    request = drive_service.files().export_media(
        fileId=doc_id,
        mimeType='text/plain'
    )
    
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while done is False:
        status, done = downloader.next_chunk()
    
    content = fh.getvalue().decode('utf-8')
    
    # Save to google_docs directory
    safe_name = "".join(c for c in doc_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
    output_path = GOOGLE_DOCS_DIR / f"{safe_name}.txt"
    
    # Generate metadata
    author = owners[0]['displayName'] if owners and len(owners) > 0 else None
    metadata = generate_metadata(
        source="google_docs",
        type="document",
        author=author,
        created_date=None,  # Drive API doesn't always provide creation date
        modified_date=modified_time,
        title=doc_name
    )
    
    # Save with metadata header
    save_with_metadata(output_path, content, metadata)
    
    print(f"Downloaded: {doc_name} -> {output_path}")
    return output_path

def main():
    print("Authenticating with Google...")
    creds = get_credentials()
    
    print("Building Drive service...")
    drive_service = build('drive', 'v3', credentials=creds)
    
    print("Fetching Google Docs...")
    docs = list_google_docs(drive_service)
    
    if not docs:
        print("No Google Docs found in your account.")
        return
    
    print(f"\nFound {len(docs)} Google Docs:")
    for doc in docs:
        print(f"  - {doc['name']} (ID: {doc['id']})")
    
    confirm = input("\nDownload all documents? (y/n): ")
    if confirm.lower() != 'y':
        print("Aborted.")
        return
    
    print("\nDownloading documents...")
    for doc in docs:
        try:
            export_google_doc(
                drive_service, 
                doc['id'], 
                doc['name'],
                doc.get('modifiedTime'),
                doc.get('owners')
            )
        except Exception as e:
            print(f"Error downloading {doc['name']}: {e}")
    
    print(f"\nComplete! Documents saved to {GOOGLE_DOCS_DIR}")
    print("You can now run 'python scripts/ingest.py' to process these documents.")

if __name__ == "__main__":
    main()
