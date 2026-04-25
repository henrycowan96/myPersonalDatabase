import os
import sys
from pathlib import Path
import pickle
from dotenv import load_dotenv
import base64
import email
from email.policy import default

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from metadata_utils import generate_metadata, save_with_metadata

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

load_dotenv()

# Configuration
RAW_DOCS_DIR = Path(__file__).parent.parent / "data" / "raw_docs"
EMAILS_DIR = RAW_DOCS_DIR / "emails"
CREDENTIALS_DIR = Path(__file__).parent.parent / "credentials"
TOKEN_FILE = CREDENTIALS_DIR / "token_gmail.pickle"

# Create directories if they don't exist
RAW_DOCS_DIR.mkdir(parents=True, exist_ok=True)
EMAILS_DIR.mkdir(parents=True, exist_ok=True)
CREDENTIALS_DIR.mkdir(parents=True, exist_ok=True)

# OAuth2 scopes - Gmail readonly
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

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

def list_emails(gmail_service, max_results=100):
    """List emails from Gmail"""
    results = gmail_service.users().messages().list(
        userId='me',
        maxResults=max_results
    ).execute()
    
    messages = results.get('messages', [])
    print(f"Found {len(messages)} emails")
    return messages

def get_email_content(gmail_service, msg_id):
    """Get the full content of an email"""
    message = gmail_service.users().messages().get(
        userId='me',
        id=msg_id,
        format='raw'
    ).execute()
    
    # Decode the raw email
    msg_raw = base64.urlsafe_b64decode(message['raw'])
    msg = email.message_from_bytes(msg_raw, policy=default)
    
    # Extract subject, sender, date, and body
    subject = msg.get('subject', 'No Subject')
    sender = msg.get('from', 'Unknown Sender')
    date = msg.get('date', 'Unknown Date')
    to = msg.get('to', '')
    
    # Extract body text
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type == 'text/plain':
                body = part.get_content()
                break
    else:
        body = msg.get_content()
    
    # Format the email as text (without metadata header)
    email_text = f"Subject: {subject}\n"
    email_text += f"From: {sender}\n"
    if to:
        email_text += f"To: {to}\n"
    email_text += f"Date: {date}\n"
    email_text += f"\n{body}"
    
    return email_text, subject, sender, date

def save_email(email_text, subject, msg_id, sender, date):
    """Save email to file with metadata"""
    # Create a safe filename from subject
    safe_subject = "".join(c for c in subject if c.isalnum() or c in (' ', '-', '_')).rstrip()
    if not safe_subject:
        safe_subject = "no_subject"
    
    # Use message ID to ensure uniqueness
    filename = f"{safe_subject}_{msg_id[:8]}.txt"
    output_path = EMAILS_DIR / filename
    
    # Generate metadata
    metadata = generate_metadata(
        source="gmail",
        type="email",
        author=sender,
        created_date=date,
        modified_date=None,  # Emails don't have modification dates
        subject=subject,
        message_id=msg_id
    )
    
    # Save with metadata header
    save_with_metadata(output_path, email_text, metadata)
    
    return output_path

def fetch_gmail_emails(max_results=100, credentials_dir=None, credentials=None):
    """Fetch Gmail emails and return them as structured data
    
    Args:
        max_results: Maximum number of emails to fetch
        credentials_dir: Custom credentials directory path (deprecated, use credentials instead)
        credentials: Google OAuth Credentials object (preferred)
    
    Returns:
        List of dictionaries containing email data
    """
    global CREDENTIALS_DIR, TOKEN_FILE, EMAILS_DIR
    
    # Use provided credentials if available
    if credentials:
        print("Authenticating with Google using provided credentials...")
        creds = credentials
    else:
        # Override directories if custom path provided
        if credentials_dir:
            CREDENTIALS_DIR = Path(credentials_dir)
            TOKEN_FILE = CREDENTIALS_DIR / "token_gmail.pickle"
        
        print("Authenticating with Google...")
        creds = get_credentials()
    
    print("Building Gmail service...")
    gmail_service = build('gmail', 'v1', credentials=creds)
    
    print(f"Fetching up to {max_results} emails...")
    messages = list_emails(gmail_service, max_results)
    
    if not messages:
        print("No emails found in your account.")
        return []
    
    print(f"Found {len(messages)} emails")
    
    all_emails = []
    
    for msg in messages:
        try:
            msg_id = msg['id']
            email_text, subject, sender, date = get_email_content(gmail_service, msg_id)
            all_emails.append({
                'message_id': msg_id,
                'subject': subject,
                'sender': sender,
                'date': date,
                'body': email_text
            })
            print(f"Fetched: {subject[:50]}...")
        except Exception as e:
            print(f"Error fetching email {msg['id']}: {e}")
    
    print(f"Total emails fetched: {len(all_emails)}")
    return all_emails

def main():
    print("Authenticating with Google...")
    creds = get_credentials()
    
    print("Building Gmail service...")
    gmail_service = build('gmail', 'v1', credentials=creds)
    
    # Ask user how many emails to fetch
    max_results = input("How many emails to fetch? (default: 100): ").strip()
    max_results = int(max_results) if max_results else 100
    
    print(f"Fetching up to {max_results} emails...")
    messages = list_emails(gmail_service, max_results)
    
    if not messages:
        print("No emails found in your account.")
        return
    
    print(f"\nFound {len(messages)} emails")
    
    confirm = input(f"\nDownload all {len(messages)} emails? (y/n): ")
    if confirm.lower() != 'y':
        print("Aborted.")
        return
    
    print("\nDownloading emails...")
    success_count = 0
    error_count = 0
    
    for msg in messages:
        try:
            msg_id = msg['id']
            email_text, subject, sender, date = get_email_content(gmail_service, msg_id)
            output_path = save_email(email_text, subject, msg_id, sender, date)
            print(f"Downloaded: {subject[:50]}... -> {output_path.name}")
            success_count += 1
        except Exception as e:
            print(f"Error downloading email {msg['id']}: {e}")
            error_count += 1
    
    print(f"\nComplete! Downloaded {success_count} emails to {EMAILS_DIR}")
    if error_count > 0:
        print(f"Failed to download {error_count} emails")
    print("You can now run 'python scripts/ingest.py' to process these emails.")

if __name__ == "__main__":
    main()
