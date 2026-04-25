import os
import sys
from pathlib import Path
import re
import json
from datetime import datetime
from dateutil import parser as date_parser
from collections import defaultdict

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from metadata_utils import generate_metadata, save_with_metadata

# Configuration
RAW_DOCS_DIR = Path(__file__).parent.parent / "data" / "raw_docs"
GOOGLE_CALENDAR_DIR = RAW_DOCS_DIR / "calendar"
APPLE_CALENDAR_DIR = RAW_DOCS_DIR / "apple_calendar"
PROCESSED_CALENDAR_DIR = RAW_DOCS_DIR / "calendar_processed"
PROCESSED_CALENDAR_DIR.mkdir(parents=True, exist_ok=True)

def parse_event_block(event_text):
    """Parse a single event block into structured data"""
    event_data = {
        'title': '',
        'start': '',
        'end': '',
        'location': '',
        'description': '',
        'attendees': []
    }
    
    lines = event_text.strip().split('\n')
    current_field = None
    
    for line in lines:
        line = line.strip()
        
        if line.startswith('Title:'):
            event_data['title'] = line[6:].strip()
            current_field = 'title'
        elif line.startswith('Start:'):
            event_data['start'] = line[6:].strip()
            current_field = 'start'
        elif line.startswith('End:'):
            event_data['end'] = line[4:].strip()
            current_field = 'end'
        elif line.startswith('Location:'):
            event_data['location'] = line[9:].strip()
            current_field = 'location'
        elif line.startswith('Description:') or line.startswith('Notes:'):
            # Handle both Google (Description) and Apple (Notes) formats
            field_name = 'Description:' if line.startswith('Description:') else 'Notes:'
            event_data['description'] = line[len(field_name):].strip()
            current_field = 'description'
        elif line.startswith('-' * 10):
            # Event separator
            break
        elif current_field == 'description' and line:
            event_data['description'] += '\n' + line
        elif current_field and not line.startswith(('Title:', 'Start:', 'End:', 'Location:', 'Description:', 'Notes:')):
            # Continuation of previous field
            if current_field == 'description':
                event_data['description'] += '\n' + line
    
    # Extract attendees from description if present
    description = event_data['description']
    if description:
        # Look for email patterns
        email_pattern = r'[\w\.-]+@[\w\.-]+\.\w+'
        emails = re.findall(email_pattern, description)
        event_data['attendees'] = emails
        
        # Look for meeting IDs
        meeting_id_pattern = r'Meeting ID:\s*([\d\s]+)'
        meeting_ids = re.findall(meeting_id_pattern, description)
        if meeting_ids:
            event_data['meeting_id'] = meeting_ids[0].strip()
        
        # Look for passcodes
        passcode_pattern = r'Passcode:\s*(\w+)'
        passcodes = re.findall(passcode_pattern, description)
        if passcodes:
            event_data['passcode'] = passcodes[0]
    
    return event_data

def parse_calendar_file(file_path):
    """Parse a calendar events file into structured events"""
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    # Check for metadata header
    calendar_name = "Unknown Calendar"
    if content.startswith('=== METADATA ==='):
        try:
            end_metadata = content.index('=== END METADATA ===')
            metadata_json = content[16:end_metadata].strip()
            metadata = json.loads(metadata_json)
            calendar_name = metadata.get('calendar_name', 'Unknown Calendar')
            content = content[end_metadata + 20:].strip()
        except:
            pass
    else:
        # Try to extract calendar name from first line
        first_line = content.split('\n')[0]
        if first_line.startswith('Calendar:'):
            calendar_name = first_line[9:].strip()
    
    # Split by event separators
    event_blocks = re.split(r'-{50,}', content)
    
    events = []
    for block in event_blocks:
        block = block.strip()
        if block and 'Title:' in block:
            event_data = parse_event_block(block)
            if event_data['title']:
                events.append(event_data)
    
    return {
        'calendar_name': calendar_name,
        'events': events
    }

def normalize_datetime(date_str):
    """Normalize various datetime formats to ISO format"""
    if not date_str:
        return None
    
    try:
        dt = date_parser.parse(date_str)
        return dt.isoformat()
    except:
        return date_str

def categorize_event(event_data):
    """Categorize event by type"""
    title = event_data['title'].lower()
    description = event_data['description'].lower()
    
    # Meeting/conference patterns
    if any(keyword in title or keyword in description for keyword in ['meeting', 'zoom', 'webex', 'call', 'interview']):
        return 'meeting'
    
    # Academic patterns
    if any(keyword in title or keyword in description for keyword in ['class', 'school', 'exam', 'midterm', 'final', 'homework', 'assignment', 'club']):
        return 'academic'
    
    # Social patterns
    if any(keyword in title or keyword in description for keyword in ['party', 'dinner', 'lunch', 'birthday', 'celebration', 'hangout']):
        return 'social'
    
    # Travel patterns
    if any(keyword in title or keyword in description for keyword in ['flight', 'trip', 'travel', 'reservation', 'hotel']):
        return 'travel'
    
    # Work patterns
    if any(keyword in title or keyword in description for keyword in ['work', 'office', 'shift', 'interview']):
        return 'work'
    
    # Sports/fitness
    if any(keyword in title or keyword in description for keyword in ['gym', 'workout', 'practice', 'game', 'match', 'bjj', 'jiu-jitsu']):
        return 'fitness'
    
    return 'other'

def process_calendar_files():
    """Process all calendar files from both Google and Apple calendars"""
    print(f"Processing calendar files...")
    
    # Collect files from both directories
    calendar_files = []
    
    if GOOGLE_CALENDAR_DIR.exists():
        google_files = list(GOOGLE_CALENDAR_DIR.glob('*_events.txt'))
        calendar_files.extend([(f, 'google_calendar') for f in google_files])
        print(f"Found {len(google_files)} Google Calendar files")
    
    if APPLE_CALENDAR_DIR.exists():
        apple_files = list(APPLE_CALENDAR_DIR.glob('*_events.txt'))
        calendar_files.extend([(f, 'apple_calendar') for f in apple_files])
        print(f"Found {len(apple_files)} Apple Calendar files")
    
    if not calendar_files:
        print("No calendar files found in either directory.")
        return
    
    print(f"Total calendar files to process: {len(calendar_files)}")
    
    total_events = 0
    processed_files = 0
    errors = 0
    
    for calendar_file, source in calendar_files:
        try:
            print(f"\nProcessing {calendar_file.name} (from {source})...")
            
            # Parse calendar file
            calendar_data = parse_calendar_file(calendar_file)
            events = calendar_data['events']
            calendar_name = calendar_data['calendar_name']
            
            print(f"  Found {len(events)} events")
            
            if not events:
                print(f"  No events found, skipping")
                continue
            
            # Create structured JSON output
            structured_events = []
            
            for event in events:
                # Normalize dates
                start_normalized = normalize_datetime(event['start'])
                end_normalized = normalize_datetime(event['end'])
                
                # Categorize event
                category = categorize_event(event)
                
                structured_event = {
                    'title': event['title'],
                    'start': event['start'],
                    'start_normalized': start_normalized,
                    'end': event['end'],
                    'end_normalized': end_normalized,
                    'location': event['location'],
                    'description': event['description'],
                    'category': category,
                    'attendees': event.get('attendees', []),
                    'meeting_id': event.get('meeting_id'),
                    'passcode': event.get('passcode')
                }
                
                structured_events.append(structured_event)
            
            # Save structured data as JSON
            safe_name = "".join(c for c in calendar_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
            if not safe_name:
                safe_name = "calendar"
            
            json_filename = f"{safe_name}_structured.json"
            json_path = PROCESSED_CALENDAR_DIR / json_filename
            
            # Generate metadata with correct source
            metadata = generate_metadata(
                source=source,
                type="structured_events",
                author=None,
                created_date=None,
                modified_date=None,
                calendar_name=calendar_name,
                event_count=len(structured_events),
                processed_at=datetime.now().isoformat(),
                original_file=calendar_file.name
            )
            
            # Save with metadata
            with open(json_path, 'w', encoding='utf-8') as f:
                f.write(json.dumps(structured_events, indent=2))
            
            print(f"  Saved {len(structured_events)} structured events to {json_filename}")
            
            # Also save a human-readable summary
            summary_filename = f"{safe_name}_summary.txt"
            summary_path = PROCESSED_CALENDAR_DIR / summary_filename
            
            summary_content = f"Calendar: {calendar_name}\n"
            summary_content += f"Total Events: {len(structured_events)}\n"
            summary_content += "=" * 50 + "\n\n"
            
            # Group by category
            by_category = defaultdict(list)
            for event in structured_events:
                by_category[event['category']].append(event)
            
            for category, events in sorted(by_category.items()):
                summary_content += f"\n{category.upper()} ({len(events)} events):\n"
                summary_content += "-" * 50 + "\n"
                for event in events:
                    summary_content += f"  - {event['title']}\n"
                    if event['start']:
                        summary_content += f"    Start: {event['start']}\n"
                    if event['location']:
                        summary_content += f"    Location: {event['location']}\n"
                    summary_content += "\n"
            
            save_with_metadata(summary_path, summary_content, metadata)
            
            total_events += len(structured_events)
            processed_files += 1
            
        except Exception as e:
            print(f"Error processing {calendar_file.name}: {e}")
            import traceback
            traceback.print_exc()
            errors += 1
    
    print(f"\nComplete!")
    print(f"Processed {processed_files} calendar files")
    print(f"Total events extracted: {total_events}")
    print(f"Errors: {errors}")
    print(f"Structured data saved to {PROCESSED_CALENDAR_DIR}")
    
    return {
        'processed_files': processed_files,
        'total_events': total_events,
        'errors': errors
    }

if __name__ == "__main__":
    process_calendar_files()
