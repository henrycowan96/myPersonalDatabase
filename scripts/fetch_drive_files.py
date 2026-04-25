import os
import sys
from pathlib import Path
import pickle
from dotenv import load_dotenv
import io
import json

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from metadata_utils import generate_metadata, save_with_metadata

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

load_dotenv()

# Configuration
RAW_DOCS_DIR = Path(__file__).parent.parent / "data" / "raw_docs"
DRIVE_FILES_DIR = RAW_DOCS_DIR / "drive_files"
CREDENTIALS_DIR = Path(__file__).parent.parent / "credentials"
TOKEN_FILE = CREDENTIALS_DIR / "token_drive.pickle"

# Create directories if they don't exist
RAW_DOCS_DIR.mkdir(parents=True, exist_ok=True)
DRIVE_FILES_DIR.mkdir(parents=True, exist_ok=True)
CREDENTIALS_DIR.mkdir(parents=True, exist_ok=True)

# OAuth2 scopes - Drive readonly
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

# MIME type mappings for export
EXPORT_MIME_TYPES = {
    'application/vnd.google-apps.document': 'text/plain',
    'application/vnd.google-apps.presentation': 'text/plain',
    'application/vnd.google-apps.spreadsheet': 'text/csv',
    'application/vnd.google-apps.drawing': 'text/plain',
    'application/vnd.google-apps.script': 'text/plain',
}

# File types that can be downloaded directly (no export needed)
DOWNLOADABLE_TYPES = [
    'application/pdf',
    'text/plain',
    'text/csv',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.ms-powerpoint',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation',
]

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

def list_drive_files(drive_service):
    """List all files in Drive (excluding Google Docs which are handled separately)"""
    # Query for files that are not Google Docs (those are handled by fetch_google_docs.py)
    query = "mimeType != 'application/vnd.google-apps.document'"
    
    results = drive_service.files().list(
        q=query,
        fields="files(id, name, mimeType, modifiedTime, owners)",
        pageSize=100
    ).execute()
    
    files = results.get('files', [])
    print(f"Found {len(files)} files in Drive")
    return files

def export_drive_file(drive_service, file_id, file_name, mime_type, modified_time=None, owners=None):
    """Export or download a file from Drive with metadata"""
    
    # Check if this is a Google Workspace file that needs export
    if mime_type in EXPORT_MIME_TYPES:
        export_mime = EXPORT_MIME_TYPES[mime_type]
        request = drive_service.files().export_media(
            fileId=file_id,
            mimeType=export_mime
        )
        
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
        
        content = fh.getvalue()
        
        # Determine file extension based on export type
        if export_mime == 'text/plain':
            extension = '.txt'
        elif export_mime == 'text/csv':
            extension = '.csv'
        else:
            extension = '.txt'
        
    # Check if this is a directly downloadable file
    elif mime_type in DOWNLOADABLE_TYPES:
        request = drive_service.files().get_media(fileId=file_id)
        
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
        
        content = fh.getvalue()
        
        # Determine extension from original filename or mime type
        if '.' in file_name:
            extension = '.' + file_name.rsplit('.', 1)[-1]
        else:
            extension = '.bin'
    
    else:
        print(f"Skipping {file_name} (unsupported MIME type: {mime_type})")
        return None
    
    # Save to drive_files directory
    safe_name = "".join(c for c in file_name if c.isalnum() or c in (' ', '-', '_', '.')).rstrip()
    if not safe_name:
        safe_name = "unnamed_file"
    
    # Remove existing extension if present and add the correct one
    if safe_name.endswith(extension):
        output_path = DRIVE_FILES_DIR / safe_name
    else:
        # Remove any existing extension
        base_name = safe_name.rsplit('.', 1)[0] if '.' in safe_name else safe_name
        output_path = DRIVE_FILES_DIR / f"{base_name}{extension}"
    
    # Generate metadata
    author = owners[0]['displayName'] if owners and len(owners) > 0 else None
    metadata = generate_metadata(
        source="google_drive",
        type="file",
        author=author,
        created_date=None,  # Drive API doesn't always provide creation date
        modified_date=modified_time,
        original_filename=file_name,
        mime_type=mime_type
    )
    
    # Write content with metadata header for text files
    if isinstance(content, bytes):
        # For binary files, save metadata separately as JSON
        metadata_path = output_path.with_suffix('.metadata.json')
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)
        with open(output_path, 'wb') as f:
            f.write(content)
    else:
        # For text files, embed metadata in the file
        save_with_metadata(output_path, content, metadata)
    
    print(f"Downloaded: {file_name} -> {output_path.name}")
    return output_path

def fetch_drive_files(credentials_dir=None, credentials=None):
    """Fetch Google Drive files and return them as structured data
    
    Args:
        credentials_dir: Custom credentials directory path (deprecated, use credentials instead)
        credentials: Google OAuth Credentials object (preferred)
    
    Returns:
        List of dictionaries containing file data
    """
    global CREDENTIALS_DIR, TOKEN_FILE, DRIVE_FILES_DIR
    
    # Use provided credentials if available
    if credentials:
        print("Authenticating with Google using provided credentials...")
        creds = credentials
    else:
        # Override directories if custom path provided
        if credentials_dir:
            CREDENTIALS_DIR = Path(credentials_dir)
            TOKEN_FILE = CREDENTIALS_DIR / "token_drive.pickle"
        
        print("Authenticating with Google...")
        creds = get_credentials()
    
    print("Building Drive service...")
    drive_service = build('drive', 'v3', credentials=creds)
    
    print("Fetching Drive files...")
    files = list_drive_files(drive_service)
    
    if not files:
        print("No files found in your Drive.")
        return []
    
    all_files = []
    
    for f in files:
        try:
            # For text-based files, we can read the content
            mime_type = f.get('mimeType', '')
            file_id = f['id']
            file_name = f['name']
            
            # Try to export/download content for supported types
            if mime_type in EXPORT_MIME_TYPES or mime_type in DOWNLOADABLE_TYPES:
                if mime_type in EXPORT_MIME_TYPES:
                    export_mime = EXPORT_MIME_TYPES[mime_type]
                    request = drive_service.files().export_media(
                        fileId=file_id,
                        mimeType=export_mime
                    )
                else:
                    request = drive_service.files().get_media(fileId=file_id)
                
                fh = io.BytesIO()
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while done is False:
                    status, done = downloader.next_chunk()
                
                content = fh.getvalue()
                
                # Decode if it's text
                if isinstance(content, bytes):
                    try:
                        content = content.decode('utf-8')
                    except:
                        content = str(content)
                
                all_files.append({
                    'file_id': file_id,
                    'name': file_name,
                    'mime_type': mime_type,
                    'modified_time': f.get('modifiedTime'),
                    'owners': f.get('owners'),
                    'content': content
                })
                print(f"Fetched: {file_name}")
            else:
                print(f"Skipping {file_name} (unsupported MIME type: {mime_type})")
                
        except Exception as e:
            print(f"Error fetching {f['name']}: {e}")
    
    print(f"Total files fetched: {len(all_files)}")
    return all_files

def main():
    print("Authenticating with Google...")
    creds = get_credentials()
    
    print("Building Drive service...")
    drive_service = build('drive', 'v3', credentials=creds)
    
    print("Fetching Drive files...")
    files = list_drive_files(drive_service)
    
    if not files:
        print("No files found in your Drive.")
        return
    
    print(f"\nFound {len(files)} files:")
    for f in files:
        mime = f.get('mimeType', 'unknown')
        print(f"  - {f['name']} ({mime})")
    
    confirm = input("\nDownload all files? (y/n): ")
    if confirm.lower() != 'y':
        print("Aborted.")
        return
    
    print("\nDownloading files...")
    success_count = 0
    skip_count = 0
    error_count = 0
    
    for f in files:
        try:
            result = export_drive_file(
                drive_service, 
                f['id'], 
                f['name'], 
                f['mimeType'],
                f.get('modifiedTime'),
                f.get('owners')
            )
            if result:
                success_count += 1
            else:
                skip_count += 1
        except Exception as e:
            print(f"Error downloading {f['name']}: {e}")
            error_count += 1
    
    print(f"\nComplete! Downloaded {success_count} files to {DRIVE_FILES_DIR}")
    if skip_count > 0:
        print(f"Skipped {skip_count} files (unsupported format)")
    if error_count > 0:
        print(f"Failed to download {error_count} files")
    print("You can now run 'python scripts/ingest.py' to process these files.")

if __name__ == "__main__":
    main()
