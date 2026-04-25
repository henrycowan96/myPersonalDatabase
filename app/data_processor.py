import os
import sys
import uuid
from pathlib import Path
from pinecone import Pinecone
from sentence_transformers import SentenceTransformer
sys.path.insert(0, str(Path(__file__).parent))

import utils


async def process_and_ingest_data(user_id: str, service: str, data, pinecone_index_name: str):
    """Process fetched data and ingest into Pinecone"""
    print(f"[INGEST] Starting process_and_ingest_data for user {user_id}, service {service}")
    print(f"[INGEST] Data items received: {len(data)}")

    if not utils.embedding_model:
        print(f"[INGEST] Initializing embedding model...")
        utils.embedding_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')

    # Get user's Pinecone index
    print(f"[INGEST] Connecting to Pinecone index: {pinecone_index_name}")
    pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
    index_to_use = pc.Index(pinecone_index_name)

    vectors = []

    if service == 'google_calendar':
        print(f"[INGEST] Processing {len(data)} calendar events")
        for i, item in enumerate(data):
            summary = item.get('summary', 'No Title')
            start = item.get('start', {})
            end = item.get('end', {})
            location = item.get('location', '')
            description = item.get('description', '')

            text = f"Calendar Event: {summary}\n"
            text += f"Calendar: {item['calendar']}\n"
            text += f"Start: {start.get('dateTime', start.get('date', 'Unknown'))}\n"
            text += f"End: {end.get('dateTime', end.get('date', 'Unknown'))}\n"
            if location:
                text += f"Location: {location}\n"
            if description:
                text += f"Description: {description}\n"

            embedding = utils.embedding_model.encode(text).tolist()
            vectors.append({
                'id': str(uuid.uuid4()),
                'values': embedding,
                'metadata': {
                    'text': text,
                    'source': 'google_calendar',
                    'type': 'calendar_event',
                    'calendar': item['calendar'],
                    'event_title': summary
                }
            })
            if (i + 1) % 10 == 0:
                print(f"[INGEST] Processed {i+1}/{len(data)} calendar events")
    
    elif service == 'gmail':
        print(f"[INGEST] Processing {len(data)} Gmail messages")
        for i, message in enumerate(data):
            payload = message.get('payload', {})
            headers = payload.get('headers', [])

            subject = ''
            sender = ''
            date = ''
            for header in headers:
                if header['name'] == 'Subject':
                    subject = header['value']
                elif header['name'] == 'From':
                    sender = header['value']
                elif header['name'] == 'Date':
                    date = header['value']

            # Get body
            body = ''
            if 'parts' in payload:
                for part in payload['parts']:
                    if part['mimeType'] == 'text/plain':
                        if 'data' in part['body']:
                            import base64
                            body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                            break
            elif 'body' in payload and 'data' in payload['body']:
                import base64
                body = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')

            text = f"Email Subject: {subject}\n"
            text += f"From: {sender}\n"
            text += f"Date: {date}\n"
            text += f"\n{body}"

            embedding = utils.embedding_model.encode(text).tolist()
            vectors.append({
                'id': str(uuid.uuid4()),
                'values': embedding,
                'metadata': {
                    'text': text,
                    'source': 'gmail',
                    'type': 'email',
                    'subject': subject,
                    'sender': sender
                }
            })
            if (i + 1) % 10 == 0:
                print(f"[INGEST] Processed {i+1}/{len(data)} Gmail messages")

    elif service == 'google_drive':
        print(f"[INGEST] Processing {len(data)} Google Drive files")
        for i, file in enumerate(data):
            content = file['content']
            # Truncate content if too long
            if isinstance(content, str) and len(content) > 2000:
                content = content[:2000] + "... (truncated)"
            
            # Truncate title if too long
            title = file['name']
            if len(title) > 100:
                title = title[:100] + "..."
            
            text = f"File: {title}\n"
            text += f"Type: {file['mime_type']}\n"
            text += f"\n{content}"

            embedding = utils.embedding_model.encode(text).tolist()
            vectors.append({
                'id': str(uuid.uuid4()),
                'values': embedding,
                'metadata': {
                    'text': text,
                    'source': 'google_drive',
                    'type': 'file',
                    'title': title,
                    'mime_type': file['mime_type'],
                    'modified_date': file.get('modified_time', '')[:50] if file.get('modified_time') else ''
                }
            })
            if (i + 1) % 5 == 0:
                print(f"[INGEST] Processed {i+1}/{len(data)} Drive files")
    
    elif service == 'apple_notes':
        print(f"[INGEST] Processing {len(data)} Apple Notes")
        for i, note in enumerate(data):
            name = note.get('name', 'Untitled')
            body = note.get('body', '')
            created = note.get('created', '')
            modified = note.get('modified', '')
            
            # Truncate body if too long
            if len(body) > 3000:
                body = body[:3000] + "... (truncated)"
            
            text = f"Note: {name}\n"
            if created:
                text += f"Created: {created}\n"
            if modified:
                text += f"Modified: {modified}\n"
            text += f"\n{body}"
            
            embedding = utils.embedding_model.encode(text).tolist()
            vectors.append({
                'id': str(uuid.uuid4()),
                'values': embedding,
                'metadata': {
                    'text': text,
                    'source': 'apple_notes',
                    'type': 'note',
                    'note_name': name,
                    'created_date': created[:50] if created else '',
                    'modified_date': modified[:50] if modified else ''
                }
            })
            if (i + 1) % 10 == 0:
                print(f"[INGEST] Processed {i+1}/{len(data)} notes")
    
    elif service == 'apple_calendar':
        print(f"[INGEST] Processing {len(data)} Apple Calendar events")
        for i, event in enumerate(data):
            calendar = event.get('calendar', 'Unknown')
            summary = event.get('summary', 'No Title')
            location = event.get('location', '')
            notes = event.get('notes', '')
            start_date = event.get('start_date', '')
            end_date = event.get('end_date', '')
            
            text = f"Calendar Event: {summary}\n"
            text += f"Calendar: {calendar}\n"
            text += f"Start: {start_date}\n"
            text += f"End: {end_date}\n"
            if location:
                text += f"Location: {location}\n"
            if notes:
                text += f"Notes: {notes}\n"
            
            embedding = utils.embedding_model.encode(text).tolist()
            vectors.append({
                'id': str(uuid.uuid4()),
                'values': embedding,
                'metadata': {
                    'text': text,
                    'source': 'apple_calendar',
                    'type': 'calendar_event',
                    'calendar': calendar,
                    'event_title': summary,
                    'start_date': start_date[:50] if start_date else '',
                    'end_date': end_date[:50] if end_date else ''
                }
            })
            if (i + 1) % 10 == 0:
                print(f"[INGEST] Processed {i+1}/{len(data)} calendar events")
    
    elif service == 'apple_music':
        print(f"[INGEST] Processing Apple Music data")
        # Process songs
        songs = data.get('results', {}).get('songs', {}).get('data', [])
        for i, song in enumerate(songs):
            attributes = song.get('attributes', {})
            name = attributes.get('name', 'Unknown')
            artist = attributes.get('artistName', 'Unknown')
            album = attributes.get('albumName', 'Unknown')
            genre = attributes.get('genreNames', [])
            duration = attributes.get('durationInMillis', 0) / 1000
            
            text = f"Song: {name}\n"
            text += f"Artist: {artist}\n"
            text += f"Album: {album}\n"
            text += f"Duration: {duration:.1f} seconds\n"
            if genre:
                text += f"Genres: {', '.join(genre)}\n"
            
            embedding = utils.embedding_model.encode(text).tolist()
            vectors.append({
                'id': str(uuid.uuid4()),
                'values': embedding,
                'metadata': {
                    'text': text,
                    'source': 'apple_music',
                    'type': 'song',
                    'song_name': name,
                    'artist': artist,
                    'album': album
                }
            })
            if (i + 1) % 5 == 0:
                print(f"[INGEST] Processed {i+1}/{len(songs)} songs")
        
        # Process albums
        albums = data.get('results', {}).get('albums', {}).get('data', [])
        for i, album in enumerate(albums):
            attributes = album.get('attributes', {})
            name = attributes.get('name', 'Unknown')
            artist = attributes.get('artistName', 'Unknown')
            genre = attributes.get('genreNames', [])
            release_date = attributes.get('releaseDate', 'Unknown')
            
            text = f"Album: {name}\n"
            text += f"Artist: {artist}\n"
            text += f"Release Date: {release_date}\n"
            if genre:
                text += f"Genres: {', '.join(genre)}\n"
            
            embedding = utils.embedding_model.encode(text).tolist()
            vectors.append({
                'id': str(uuid.uuid4()),
                'values': embedding,
                'metadata': {
                    'text': text,
                    'source': 'apple_music',
                    'type': 'album',
                    'album_name': name,
                    'artist': artist
                }
            })
            if (i + 1) % 5 == 0:
                print(f"[INGEST] Processed {i+1}/{len(albums)} albums")
        
        # Process artists
        artists = data.get('results', {}).get('artists', {}).get('data', [])
        for i, artist_data in enumerate(artists):
            attributes = artist_data.get('attributes', {})
            name = attributes.get('name', 'Unknown')
            genre = attributes.get('genreNames', [])
            
            text = f"Artist: {name}\n"
            if genre:
                text += f"Genres: {', '.join(genre)}\n"
            
            embedding = utils.embedding_model.encode(text).tolist()
            vectors.append({
                'id': str(uuid.uuid4()),
                'values': embedding,
                'metadata': {
                    'text': text,
                    'source': 'apple_music',
                    'type': 'artist',
                    'artist_name': name
                }
            })
            if (i + 1) % 5 == 0:
                print(f"[INGEST] Processed {i+1}/{len(artists)} artists")
    
    # Upsert one at a time to avoid batch size issues
    print(f"[INGEST] Upserting {len(vectors)} vectors to Pinecone one at a time")
    success_count = 0
    for i, vector in enumerate(vectors):
        print(f"[INGEST] Upserting vector {i+1}/{len(vectors)}")
        try:
            index_to_use.upsert(vectors=[vector])
            success_count += 1
        except Exception as e:
            print(f"[INGEST] Error upserting vector {i+1}: {e}")
            continue
    
    print(f"[INGEST] Successfully upserted {success_count}/{len(vectors)} vectors")
    return success_count
