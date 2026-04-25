import os
import sys
from pathlib import Path
import pickle
from dotenv import load_dotenv
from datetime import datetime, timedelta

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
CALENDAR_DIR = RAW_DOCS_DIR / "calendar"
CREDENTIALS_DIR = Path(__file__).parent.parent / "credentials"
TOKEN_FILE = CREDENTIALS_DIR / "token_calendar.pickle"

# Create directories if they don't exist
RAW_DOCS_DIR.mkdir(parents=True, exist_ok=True)
CALENDAR_DIR.mkdir(parents=True, exist_ok=True)
CREDENTIALS_DIR.mkdir(parents=True, exist_ok=True)

# OAuth2 scopes - Calendar readonly
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

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

def list_calendars(calendar_service):
    """List all calendars"""
    calendar_list = calendar_service.calendarList().list().execute()
    calendars = calendar_list.get('items', [])
    print(f"Found {len(calendars)} calendars")
    return calendars

def get_events(calendar_service, calendar_id, time_min, time_max):
    """Get events from a calendar within a date range"""
    events_result = calendar_service.events().list(
        calendarId=calendar_id,
        timeMin=time_min,
        timeMax=time_max,
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    
    events = events_result.get('items', [])
    return events

def format_event(event):
    """Format an event as text"""
    summary = event.get('summary', 'No Title')
    
    # Get start and end times
    start = event.get('start', {})
    end = event.get('end', {})
    
    start_time = start.get('dateTime', start.get('date', 'Unknown'))
    end_time = end.get('dateTime', end.get('date', 'Unknown'))
    
    # Get description
    description = event.get('description', '')
    
    # Get location
    location = event.get('location', '')
    
    # Format the event
    event_text = f"Title: {summary}\n"
    event_text += f"Start: {start_time}\n"
    event_text += f"End: {end_time}\n"
    
    if location:
        event_text += f"Location: {location}\n"
    
    if description:
        event_text += f"\nDescription:\n{description}\n"
    
    return event_text

def save_events(events, calendar_name):
    """Save events to a text file with metadata"""
    if not events:
        return None
    
    # Create a safe filename from calendar name
    safe_name = "".join(c for c in calendar_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
    if not safe_name:
        safe_name = "calendar"
    
    filename = f"{safe_name}_events.txt"
    output_path = CALENDAR_DIR / filename
    
    # Generate metadata
    metadata = generate_metadata(
        source="google_calendar",
        type="calendar_events",
        author=None,  # Calendar events don't have a single author
        created_date=None,  # Events have individual dates
        modified_date=None,
        calendar_name=calendar_name,
        event_count=len(events)
    )
    
    # Format the events content
    content = f"Calendar: {calendar_name}\n"
    content += f"Total Events: {len(events)}\n"
    content += "=" * 50 + "\n\n"
    
    for event in events:
        event_text = format_event(event)
        content += event_text
        content += "\n" + "-" * 50 + "\n\n"
    
    # Save with metadata header
    save_with_metadata(output_path, content, metadata)
    
    return output_path

def fetch_google_calendar_events(start_date=None, end_date=None, credentials_dir=None, credentials=None):
    """Fetch Google Calendar events and return them as structured data
    
    Args:
        start_date: Start date string (YYYY-MM-DD) or None for 30 days ago
        end_date: End date string (YYYY-MM-DD) or None for today
        credentials_dir: Custom credentials directory path (deprecated, use credentials instead)
        credentials: Google OAuth Credentials object (preferred)
    
    Returns:
        List of dictionaries containing calendar events
    """
    global CREDENTIALS_DIR, TOKEN_FILE, CALENDAR_DIR
    
    # Use provided credentials if available
    if credentials:
        print("Authenticating with Google using provided credentials...")
        creds = credentials
    else:
        # Override directories if custom path provided
        if credentials_dir:
            CREDENTIALS_DIR = Path(credentials_dir)
            TOKEN_FILE = CREDENTIALS_DIR / "token_calendar.pickle"
        
        print("Authenticating with Google...")
        creds = get_credentials()
    
    print("Building Calendar service...")
    calendar_service = build('calendar', 'v3', credentials=creds)
    
    # List calendars
    print("Fetching calendars...")
    calendars = list_calendars(calendar_service)
    
    if not calendars:
        print("No calendars found in your account.")
        return []
    
    # Set default date range
    if not start_date:
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    if not end_date:
        end_date = datetime.now().strftime('%Y-%m-%d')
    
    # Format times for API
    time_min = f"{start_date}T00:00:00Z"
    time_max = f"{end_date}T23:59:59Z"
    
    print(f"Fetching events from {start_date} to {end_date}...")
    
    all_events = []
    
    for cal in calendars:
        try:
            calendar_id = cal['id']
            calendar_name = cal.get('summary', 'Unnamed')
            
            events = get_events(calendar_service, calendar_id, time_min, time_max)
            
            for event in events:
                all_events.append({
                    'calendar': calendar_name,
                    'calendar_id': calendar_id,
                    'summary': event.get('summary', 'No Title'),
                    'start': event.get('start', {}),
                    'end': event.get('end', {}),
                    'description': event.get('description', ''),
                    'location': event.get('location', '')
                })
            
            print(f"Fetched {len(events)} events from '{calendar_name}'")
                
        except Exception as e:
            print(f"Error fetching events from {cal.get('summary', 'calendar')}: {e}")
    
    print(f"Total events fetched: {len(all_events)}")
    return all_events

def main():
    print("Authenticating with Google...")
    creds = get_credentials()
    
    print("Building Calendar service...")
    calendar_service = build('calendar', 'v3', credentials=creds)
    
    # List calendars
    print("Fetching calendars...")
    calendars = list_calendars(calendar_service)
    
    if not calendars:
        print("No calendars found in your account.")
        return
    
    print(f"\nFound {len(calendars)} calendars:")
    for i, cal in enumerate(calendars):
        print(f"  {i + 1}. {cal.get('summary', 'Unnamed')} (ID: {cal.get('id')})")
    
    # Ask for date range
    print("\nSpecify date range for events:")
    print("Format: YYYY-MM-DD (e.g., 2026-01-01)")
    
    start_date = input("Start date (default: 30 days ago): ").strip()
    if not start_date:
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    
    end_date = input("End date (default: today): ").strip()
    if not end_date:
        end_date = datetime.now().strftime('%Y-%m-%d')
    
    # Format times for API
    time_min = f"{start_date}T00:00:00Z"
    time_max = f"{end_date}T23:59:59Z"
    
    print(f"\nFetching events from {start_date} to {end_date}...")
    
    confirm = input(f"\nFetch events from all {len(calendars)} calendars? (y/n): ")
    if confirm.lower() != 'y':
        print("Aborted.")
        return
    
    print("\nFetching events...")
    success_count = 0
    total_events = 0
    
    for cal in calendars:
        try:
            calendar_id = cal['id']
            calendar_name = cal.get('summary', 'Unnamed')
            
            events = get_events(calendar_service, calendar_id, time_min, time_max)
            
            if events:
                output_path = save_events(events, calendar_name)
                print(f"Downloaded {len(events)} events from '{calendar_name}' -> {output_path.name}")
                success_count += 1
                total_events += len(events)
            else:
                print(f"No events found in '{calendar_name}'")
                
        except Exception as e:
            print(f"Error fetching events from {cal.get('summary', 'calendar')}: {e}")
    
    print(f"\nComplete! Fetched {total_events} events from {success_count} calendars")
    print(f"Events saved to {CALENDAR_DIR}")
    print("You can now run 'python scripts/ingest.py' to process these events.")

if __name__ == "__main__":
    main()
