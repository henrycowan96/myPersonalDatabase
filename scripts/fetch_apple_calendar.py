import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
import json

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from metadata_utils import generate_metadata, save_with_metadata

try:
    import caldav
except ImportError:
    print("Error: caldav library not installed.")
    print("Install it with: pip install caldav")
    sys.exit(1)

"""
Apple Calendar Integration Notes:
================================
This script uses CalDAV protocol to access iCloud calendars directly from Apple's servers.

Requirements:
- Apple ID email
- App-Specific Password (generate at appleid.apple.com)
- caldav library (pip install caldav)

Apple does not provide a public REST API for iCloud Calendar. CalDAV is the standard protocol
for accessing calendar data from Apple's servers. This approach works cross-platform and doesn't
require the Calendar app to be running or the machine to have calendars synced locally.
"""

# Configuration
RAW_DOCS_DIR = Path(__file__).parent.parent / "data" / "raw_docs"
APPLE_CALENDAR_DIR = RAW_DOCS_DIR / "apple_calendar"

# Create directories if they don't exist
RAW_DOCS_DIR.mkdir(parents=True, exist_ok=True)
APPLE_CALENDAR_DIR.mkdir(parents=True, exist_ok=True)

def connect_to_icloud(email, app_password):
    """Connect to iCloud CalDAV server"""
    try:
        print(f"  Attempting to connect to iCloud with email: {email}")
        client = caldav.DAVClient(
            url='https://caldav.icloud.com/',
            username=email,
            password=app_password
        )
        principal = client.principal()
        print(f"  Successfully connected to iCloud")
        return principal
    except Exception as e:
        print(f"Error connecting to iCloud: {e}")
        import traceback
        traceback.print_exc()
        return None

def list_calendars(principal):
    """List all calendars from iCloud"""
    try:
        print(f"  Fetching calendars from principal...")
        calendars = principal.calendars()
        print(f"  Found {len(calendars)} calendars")
        calendar_names = [cal.name for cal in calendars]
        print(f"  Calendar names: {calendar_names}")
        return calendar_names, calendars
    except Exception as e:
        print(f"Error listing calendars: {e}")
        import traceback
        traceback.print_exc()
        return [], []

def get_events(calendar, start_date, end_date):
    """Get events from a specific calendar within a date range using CalDAV"""
    try:
        print(f"  Searching for events from {start_date} to {end_date}")
        
        # Fetch events within date range
        events = calendar.date_search(
            start=start_date,
            end=end_date,
            expand=True
        )
        
        print(f"  Raw events returned: {len(events)}")
        
        event_list = []
        for event in events:
            try:
                print(f"  Processing event: {event}")
                # Parse event data
                vevent = event.icalendar_instance.walk('VEVENT')[0]
                
                summary = str(vevent.get('SUMMARY', 'No Title'))
                location = str(vevent.get('LOCATION', ''))
                notes = str(vevent.get('DESCRIPTION', ''))
                
                # Parse dates
                dtstart = vevent.get('DTSTART')
                dtend = vevent.get('DTEND')
                
                if dtstart:
                    start_date_str = dtstart.dt.strftime('%Y-%m-%d %H:%M:%S') if hasattr(dtstart.dt, 'strftime') else str(dtstart.dt)
                else:
                    start_date_str = 'Unknown'
                
                if dtend:
                    end_date_str = dtend.dt.strftime('%Y-%m-%d %H:%M:%S') if hasattr(dtend.dt, 'strftime') else str(dtend.dt)
                else:
                    end_date_str = 'Unknown'
                
                event_list.append({
                    'summary': summary,
                    'location': location,
                    'notes': notes,
                    'start_date': start_date_str,
                    'end_date': end_date_str
                })
                print(f"  Successfully parsed event: {summary}")
            except Exception as e:
                print(f"  Error parsing event: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        print(f"  Total events parsed: {len(event_list)}")
        return event_list
    except Exception as e:
        print(f"  Error getting events: {e}")
        import traceback
        traceback.print_exc()
        return []

def format_event(event):
    """Format an event as text"""
    summary = event.get('summary', 'No Title')
    start_date = event.get('start_date', 'Unknown')
    end_date = event.get('end_date', 'Unknown')
    location = event.get('location', '')
    notes = event.get('notes', '')
    
    event_text = f"Title: {summary}\n"
    event_text += f"Start: {start_date}\n"
    event_text += f"End: {end_date}\n"
    
    if location:
        event_text += f"Location: {location}\n"
    
    if notes:
        event_text += f"\nNotes:\n{notes}\n"
    
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
    output_path = APPLE_CALENDAR_DIR / filename
    
    # Generate metadata
    metadata = generate_metadata(
        source="apple_calendar",
        type="calendar_events",
        author=None,
        created_date=None,
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

def main():
    print("Fetching Apple Calendar data via CalDAV...")
    print("\nNote: You need an App-Specific Password for iCloud.")
    print("Generate one at: https://appleid.apple.com")
    
    # Get credentials
    email = input("\nEnter your Apple ID email: ").strip()
    if not email:
        print("Email is required.")
        return
    
    app_password = input("Enter your App-Specific Password: ").strip()
    if not app_password:
        print("App-Specific Password is required.")
        return
    
    # Connect to iCloud
    print("\nConnecting to iCloud...")
    principal = connect_to_icloud(email, app_password)
    
    if not principal:
        print("Failed to connect to iCloud. Please check your credentials.")
        return
    
    print("Connected successfully!")
    
    # List calendars
    print("\nListing calendars...")
    calendar_names, calendars = list_calendars(principal)
    
    if not calendars:
        print("No calendars found.")
        return
    
    print(f"\nFound {len(calendars)} calendars:")
    for i, cal in enumerate(calendar_names):
        print(f"  {i + 1}. {cal}")
    
    # Ask for date range
    print("\nSpecify date range for events:")
    print("Format: YYYY-MM-DD (e.g., 2026-01-01)")
    
    start_date_input = input("Start date (default: 30 days ago): ").strip()
    if not start_date_input:
        start_date = datetime.now() - timedelta(days=30)
    else:
        start_date = datetime.strptime(start_date_input, '%Y-%m-%d')
    
    end_date_input = input("End date (default: today): ").strip()
    if not end_date_input:
        end_date = datetime.now()
    else:
        end_date = datetime.strptime(end_date_input, '%Y-%m-%d')
    
    print(f"\nFetching events from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}...")
    
    confirm = input(f"\nFetch events from all {len(calendars)} calendars? (y/n): ")
    if confirm.lower() != 'y':
        print("Aborted.")
        return
    
    print("\nFetching events...")
    success_count = 0
    total_events = 0
    
    for calendar_name, calendar in zip(calendar_names, calendars):
        try:
            events = get_events(calendar, start_date, end_date)
            
            if events:
                output_path = save_events(events, calendar_name)
                print(f"Downloaded {len(events)} events from '{calendar_name}' -> {output_path.name}")
                success_count += 1
                total_events += len(events)
            else:
                print(f"No events found in '{calendar_name}'")
                
        except Exception as e:
            print(f"Error fetching events from {calendar_name}: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\nComplete! Fetched {total_events} events from {success_count} calendars")
    print(f"Events saved to {APPLE_CALENDAR_DIR}")
    print("You can now run 'python scripts/ingest.py' to process these events.")

if __name__ == "__main__":
    main()
