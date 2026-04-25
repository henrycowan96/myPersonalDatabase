import sys
import subprocess
from datetime import datetime, timedelta
from pathlib import Path


async def fetch_apple_notes():
    """Fetch Apple Notes using AppleScript (macOS only)"""
    try:
        import json
        
        # Use a JSON-based approach to avoid delimiter issues
        # We'll export each note separately and build JSON in Python
        applescript_count = '''
        tell application "Notes"
            set allNotes to every note
            return count of allNotes
        end tell
        '''
        
        count_result = subprocess.run(
            ['osascript', '-e', applescript_count],
            capture_output=True,
            text=True,
            check=True
        )
        
        note_count = int(count_result.stdout.strip())
        print(f"Found {note_count} notes")
        
        # Limit to 50 notes for performance
        note_count = min(note_count, 50)
        
        notes_data = []
        for i in range(1, note_count + 1):
            # Get note by index (1-based in AppleScript)
            applescript = f'''
            tell application "Notes"
                set allNotes to every note
                set currentNote to item {i} of allNotes
                set noteName to name of currentNote
                set noteBody to body of currentNote
                set noteCreation to creation date of currentNote as string
                set noteModification to modification date of currentNote as string
                
                return noteName & "\\n---SEPARATOR---\\n" & noteBody & "\\n---SEPARATOR---\\n" & noteCreation & "\\n---SEPARATOR---\\n" & noteModification
            end tell
            '''
            
            try:
                result = subprocess.run(
                    ['osascript', '-e', applescript],
                    capture_output=True,
                    text=True,
                    check=True
                )
                output = result.stdout.strip()
                parts = output.split('---SEPARATOR---')
                
                if len(parts) >= 4:
                    name = parts[0].strip()
                    body = parts[1].strip()
                    created = parts[2].strip()
                    modified = parts[3].strip()
                    
                    # Skip empty names
                    if name:
                        notes_data.append({
                            'name': name,
                            'body': body,
                            'created': created,
                            'modified': modified
                        })
                        print(f"Exported note {i}/{note_count}: {name[:30]}...")
            except Exception as e:
                print(f"Error exporting note {i}: {e}")
                continue
        
        return {
            "message": f"Successfully fetched {len(notes_data)} Apple Notes",
            "notes": notes_data
        }
    
    except subprocess.CalledProcessError as e:
        raise Exception(f"Error running AppleScript: {e.stderr}")
    except Exception as e:
        raise Exception(str(e))


async def fetch_apple_calendar(apple_calendar_email=None, apple_calendar_password=None):
    """Fetch Apple Calendar events using CalDAV (preferred) or AppleScript (fallback)"""
    try:
        # Try CalDAV first if credentials are provided
        if apple_calendar_email and apple_calendar_password:
            try:
                sys.path.append(str(Path(__file__).parent.parent.parent / "scripts"))
                
                # Import the CalDAV-based fetch function
                from fetch_apple_calendar import connect_to_icloud, list_calendars, get_events
                
                print(f"[APPLE CALENDAR] Using CalDAV to fetch events for {apple_calendar_email}")
                
                # Connect to iCloud
                principal = connect_to_icloud(apple_calendar_email, apple_calendar_password)
                if not principal:
                    raise Exception("Failed to connect to iCloud via CalDAV")
                
                # List calendars
                calendar_names, calendars = list_calendars(principal)
                if not calendars:
                    return {"events": []}
                
                # Get events from last 30 days
                start_date = datetime.now() - timedelta(days=30)
                end_date = datetime.now()
                
                all_events = []
                for calendar_name, calendar in zip(calendar_names, calendars):
                    events = get_events(calendar, start_date, end_date)
                    for event in events:
                        all_events.append({
                            'summary': event.get('summary', 'No Title'),
                            'location': event.get('location', ''),
                            'notes': event.get('notes', ''),
                            'start_date': event.get('start_date', ''),
                            'end_date': event.get('end_date', ''),
                            'calendar': calendar_name
                        })
                
                print(f"[APPLE CALENDAR] Fetched {len(all_events)} events via CalDAV")
                return {"events": all_events}
                
            except Exception as e:
                print(f"[APPLE CALENDAR] CalDAV failed, falling back to AppleScript: {e}")
        
        # Fallback to AppleScript (macOS only)
        print(f"[APPLE CALENDAR] Using AppleScript fallback")
        
        # List calendars
        applescript_list = '''
        tell application "Calendar"
            set allCalendars to every calendar
            set calendarNames to {}
            
            repeat with currentCalendar in allCalendars
                set end of calendarNames to name of currentCalendar
            end repeat
            
            return calendarNames
        end tell
        '''
        
        result = subprocess.run(
            ['osascript', '-e', applescript_list],
            capture_output=True,
            text=True,
            check=True
        )
        
        # Parse the output
        calendar_names = [name.strip().strip('"') for name in result.stdout.split(',')]
        print(f"Found {len(calendar_names)} calendars")
        
        # Get events from last 30 days
        start_date = datetime.now() - timedelta(days=30)
        end_date = datetime.now()
        start_str = start_date.strftime('%Y-%m-%d')
        end_str = end_date.strftime('%Y-%m-%d')
        
        all_events = []
        print(f"Processing {len(calendar_names)} calendars from {start_str} to {end_str}")
        
        for idx, calendar_name in enumerate(calendar_names):
            print(f"[{idx+1}/{len(calendar_names)}] Processing calendar: {calendar_name}")
            applescript = f'''
            tell application "Calendar"
                set targetCalendar to calendar "{calendar_name}"
                set allEvents to every event of targetCalendar
                
                set eventList to {{}}
                
                repeat with currentEvent in allEvents
                    set eventStart to start date of currentEvent
                    set eventEnd to end date of currentEvent
                    
                    -- Check if event is within date range
                    if (eventStart ≥ date "{start_str}") and (eventStart ≤ date "{end_str}") then
                        set eventSummary to summary of currentEvent
                        set eventLocation to location of currentEvent
                        set eventNotes to notes of currentEvent
                        set eventStartDate to start date of currentEvent as string
                        set eventEndDate to end date of currentEvent as string
                        
                        set eventRecord to eventSummary & "|||" & eventLocation & "|||" & eventNotes & "|||" & eventStartDate & "|||" & eventEndDate
                        set end of eventList to eventRecord
                    end if
                end repeat
                
                return eventList as string
            end tell
            '''
            
            try:
                print(f"[{idx+1}/{len(calendar_names)}] Executing AppleScript for {calendar_name}...")
                result = subprocess.run(
                    ['osascript', '-e', applescript],
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=30  # Add timeout to prevent hanging
                )
                print(f"[{idx+1}/{len(calendar_names)}] AppleScript completed for {calendar_name}")
                
                output = result.stdout.strip()
                print(f"[{idx+1}/{len(calendar_names)}] Output length: {len(output)} characters")
                
                if output:
                    event_strings = output.split('|||')
                    print(f"[{idx+1}/{len(calendar_names)}] Found {len(event_strings) // 5} events in {calendar_name}")
                    # Each event has 5 parts: summary, location, notes, start_date, end_date
                    for i in range(0, len(event_strings), 5):
                        if i + 4 < len(event_strings):
                            all_events.append({
                                'calendar': calendar_name,
                                'summary': event_strings[i],
                                'location': event_strings[i + 1],
                                'notes': event_strings[i + 2],
                                'start_date': event_strings[i + 3],
                                'end_date': event_strings[i + 4]
                            })
                    print(f"[{idx+1}/{len(calendar_names)}] Fetched {len(event_strings) // 5} events from {calendar_name}")
                else:
                    print(f"[{idx+1}/{len(calendar_names)}] No events found in {calendar_name}")
            except subprocess.TimeoutExpired:
                print(f"[{idx+1}/{len(calendar_names)}] TIMEOUT fetching events from {calendar_name} (30s)")
                continue
            except Exception as e:
                print(f"[{idx+1}/{len(calendar_names)}] ERROR fetching events from {calendar_name}: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        print(f"Total events fetched across all calendars: {len(all_events)}")
        
        return {
            "message": f"Successfully fetched {len(all_events)} Apple Calendar events",
            "events": all_events
        }
    
    except subprocess.CalledProcessError as e:
        raise Exception(f"Error running AppleScript: {e.stderr}")
    except Exception as e:
        raise Exception(str(e))


async def fetch_user_library_with_token(music_user_token: str):
    """Fetch user's Apple Music library using Music User Token"""
    try:
        import requests

        # Apple Music API endpoint for user's library
        base_url = 'https://api.music.apple.com/v1/me/library'

        headers = {
            'Authorization': f'Bearer {music_user_token}',
            'Music-User-Token': music_user_token,
            'Content-Type': 'application/json'
        }

        # Fetch songs from user's library
        songs_url = f'{base_url}/songs'
        songs_response = requests.get(songs_url, headers=headers, params={'limit': 100})

        # Fetch albums from user's library
        albums_url = f'{base_url}/albums'
        albums_response = requests.get(albums_url, headers=headers, params={'limit': 50})

        # Fetch artists from user's library
        artists_url = f'{base_url}/artists'
        artists_response = requests.get(artists_url, headers=headers, params={'limit': 50})

        # Combine results
        music_data = {
            'results': {
                'songs': songs_response.json() if songs_response.status_code == 200 else {},
                'albums': albums_response.json() if albums_response.status_code == 200 else {},
                'artists': artists_response.json() if artists_response.status_code == 200 else {}
            }
        }

        return music_data
    except Exception as e:
        print(f"[APPLE MUSIC] Error fetching user library with token: {e}")
        import traceback
        traceback.print_exc()
        return None


def generate_apple_music_token(key_id: str, team_id: str, private_key_path: str):
    """Generate a JWT developer token for Apple Music API"""
    try:
        import jwt
        import time
        
        with open(private_key_path, 'r') as f:
            private_key = f.read()
        
        now = int(time.time())
        expiration = now + (6 * 30 * 24 * 60 * 60)
        
        payload = {
            'iss': team_id,
            'iat': now,
            'exp': expiration,
            'sub': 'user-music-library-read'
        }
        
        token = jwt.encode(payload, private_key, algorithm='ES256', headers={'kid': key_id})
        return token
    except Exception as e:
        print(f"[APPLE MUSIC] Error generating token: {e}")
        return None


async def fetch_apple_music_data(key_id: str, team_id: str, private_key_path: str, storefront: str = 'us'):
    """Fetch music data from Apple Music API"""
    try:
        import requests
        
        print(f"[APPLE MUSIC] Generating developer token...")
        token = generate_apple_music_token(key_id, team_id, private_key_path)
        
        if not token:
            raise Exception("Failed to generate developer token")
        
        print(f"[APPLE MUSIC] Token generated successfully")
        
        headers = {
            'Authorization': f'Bearer {token}',
        }
        
        base_url = f'https://api.music.apple.com/v1/catalog/{storefront}'
        
        # Search for popular music as a sample (full library access requires user OAuth)
        search_url = f'{base_url}/search'
        params = {
            'term': 'popular',
            'types': 'songs,albums,artists',
            'limit': 20
        }
        
        print(f"[APPLE MUSIC] Fetching music data...")
        response = requests.get(search_url, headers=headers, params=params)
        
        if response.status_code == 200:
            data = response.json()
            print(f"[APPLE MUSIC] Data fetched successfully")
            return data
        else:
            print(f"[APPLE MUSIC] Error: {response.status_code} - {response.text}")
            raise Exception(f"API error: {response.status_code}")
    except Exception as e:
        print(f"[APPLE MUSIC] Fatal error: {e}")
        import traceback
        traceback.print_exc()
        raise Exception(f"Error fetching Apple Music data: {str(e)}")
