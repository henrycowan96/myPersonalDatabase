import asyncio
import sys
from pathlib import Path


async def fetch_calendar_data(user_id: str, creds):
    """Fetch calendar data using the fetch_calendar.py script"""
    try:
        print(f"[CALENDAR FETCH] Starting calendar data fetch for user {user_id}")
        
        # Import and use the fetch_calendar script
        sys.path.append(str(Path(__file__).parent.parent.parent / "scripts"))
        from fetch_calendar import fetch_google_calendar_events
        
        # Fetch calendar events using the script with provided credentials
        events_data = await asyncio.get_event_loop().run_in_executor(
            None, 
            lambda: fetch_google_calendar_events(credentials=creds)
        )
        
        print(f"[CALENDAR FETCH] Total events fetched: {len(events_data)}")
        return events_data
    except Exception as e:
        print(f"[CALENDAR FETCH] Fatal error in fetch_calendar_data: {e}")
        import traceback
        traceback.print_exc()
        raise Exception(f"Error fetching calendar data: {str(e)}")


async def fetch_gmail_data(user_id: str, creds):
    """Fetch Gmail data using the fetch_emails.py script"""
    try:
        print(f"[GMAIL FETCH] Starting Gmail data fetch for user {user_id}")
        
        # Import and use the fetch_emails script
        sys.path.append(str(Path(__file__).parent.parent.parent / "scripts"))
        from fetch_emails import fetch_gmail_emails
        
        # Fetch emails using the script with provided credentials
        emails_data = await asyncio.get_event_loop().run_in_executor(
            None, 
            lambda: fetch_gmail_emails(max_results=100, credentials=creds)
        )
        
        print(f"[GMAIL FETCH] Total emails fetched: {len(emails_data)}")
        return emails_data
    except Exception as e:
        print(f"[GMAIL FETCH] Fatal error in fetch_gmail_data: {e}")
        import traceback
        traceback.print_exc()
        raise Exception(f"Error fetching Gmail data: {str(e)}")


async def fetch_google_drive_data(user_id: str, creds):
    """Fetch Google Drive files using the fetch_drive_files.py script"""
    try:
        print(f"[DRIVE FETCH] Starting Google Drive fetch for user {user_id}")
        
        # Import and use the fetch_drive_files script
        sys.path.append(str(Path(__file__).parent.parent.parent / "scripts"))
        from fetch_drive_files import fetch_drive_files
        
        # Fetch drive files using the script with provided credentials
        drive_data = await asyncio.get_event_loop().run_in_executor(
            None, 
            lambda: fetch_drive_files(credentials=creds)
        )
        
        print(f"[DRIVE FETCH] Total files fetched: {len(drive_data)}")
        return drive_data
    except Exception as e:
        print(f"[DRIVE FETCH] Fatal error in fetch_google_drive_data: {e}")
        import traceback
        traceback.print_exc()
        raise Exception(f"Error fetching Google Drive data: {str(e)}")
