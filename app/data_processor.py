import os
import sys
import uuid
from pathlib import Path
from pinecone import Pinecone
from sentence_transformers import SentenceTransformer
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import utils
from entity_extraction import extract_entities_for_document
from facts.extractor import extract_facts_from_chunk, _extract_source_timestamp
from facts.pipeline import process_extracted_claim


async def process_and_ingest_data(user_id: str, service: str, data, pinecone_index_name: str, sync_job_id: str = None):
    """Process fetched data and ingest into Pinecone with deduplication"""
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
    source_ids_seen = []
    items_created = 0
    items_updated = 0
    items_skipped = 0

    if service == 'google_calendar':
        print(f"[INGEST] Processing {len(data)} calendar events")
        for i, item in enumerate(data):
            summary = item.get('summary', 'No Title')
            start = item.get('start', {})
            end = item.get('end', {})
            location = item.get('location', '')
            description = item.get('description', '')
            event_id = item.get('id', str(uuid.uuid4()))  # Use event ID if available

            text = f"Calendar Event: {summary}\n"
            text += f"Calendar: {item['calendar']}\n"
            text += f"Start: {start.get('dateTime', start.get('date', 'Unknown'))}\n"
            text += f"End: {end.get('dateTime', end.get('date', 'Unknown'))}\n"
            if location:
                text += f"Location: {location}\n"
            if description:
                text += f"Description: {description}\n"

            # Generate content hash for deduplication
            content_hash = utils.generate_content_hash(text)

            # Check if this chunk already exists
            existing_chunk = utils.check_chunk_exists(user_id, 'google_calendar', content_hash)
            if existing_chunk:
                # Update last_seen_at for existing chunk
                utils.update_chunk_last_seen(existing_chunk['id'], sync_job_id)
                items_skipped += 1
                source_ids_seen.append(event_id)
                if (i + 1) % 10 == 0:
                    print(f"[INGEST] Processed {i+1}/{len(data)} calendar events (skipped {items_skipped} duplicates)")
                continue

            embedding = utils.embedding_model.encode(text).tolist()
            vector_id = str(uuid.uuid4())
            try:
                source_ts = _extract_source_timestamp(item, service)
                facts = extract_facts_from_chunk(text, source_ts, vector_id, user_id)
                for fact in facts:
                    process_extracted_claim(fact)
            except Exception as e:
                print(f"[FACTS] Error extracting facts from calendar event: {e}")
            vectors.append({
                'id': vector_id,
                'values': embedding,
                'metadata': {
                    'text': text,
                    'source': 'google_calendar',
                    'type': 'calendar_event',
                    'calendar': item['calendar'],
                    'event_title': summary,
                    'event_id': event_id,
                    'content_hash': content_hash
                }
            })
            source_ids_seen.append(event_id)
            items_created += 1
            if (i + 1) % 10 == 0:
                print(f"[INGEST] Processed {i+1}/{len(data)} calendar events")
    
    elif service == 'gmail':
        print(f"[INGEST] Processing {len(data)} Gmail messages")
        for i, message in enumerate(data):
            payload = message.get('payload', {})
            headers = payload.get('headers', [])
            
            # Get basic email info
            subject = message.get('subject', 'No Subject')
            sender = message.get('sender', 'Unknown Sender')
            date = message.get('date', 'Unknown Date')
            message_id = message.get('id', str(uuid.uuid4()))  # Gmail message ID
            
            print(f"[INGEST] Email {i}: subject='{subject}', sender='{sender}', date='{date}'")
            
            # Get body text
            import base64
            body = ""
            if 'body' in payload and 'data' in payload['body']:
                body = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')
            
            # Store only the body content in text field (headers are metadata)
            text = f"{body}"
            
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

            # Generate content hash for deduplication
            content_hash = utils.generate_content_hash(text)

            # Check if this chunk already exists
            existing_chunk = utils.check_chunk_exists(user_id, 'gmail', content_hash)
            if existing_chunk:
                utils.update_chunk_last_seen(existing_chunk['id'], sync_job_id)
                items_skipped += 1
                source_ids_seen.append(message_id)
                if (i + 1) % 10 == 0:
                    print(f"[INGEST] Processed {i+1}/{len(data)} Gmail messages (skipped {items_skipped} duplicates)")
                continue

            embedding = utils.embedding_model.encode(text).tolist()
            vector_id = str(uuid.uuid4())
            try:
                source_ts = _extract_source_timestamp(message, service)
                facts = extract_facts_from_chunk(text, source_ts, vector_id, user_id)
                for fact in facts:
                    process_extracted_claim(fact)
            except Exception as e:
                print(f"[FACTS] Error extracting facts from email: {e}")
            vectors.append({
                'id': vector_id,
                'values': embedding,
                'metadata': {
                    'text': text,
                    'source': 'gmail',
                    'type': 'email',
                    'subject': subject,
                    'sender': sender,
                    'message_id': message_id,
                    'content_hash': content_hash
                }
            })
            source_ids_seen.append(message_id)
            items_created += 1
            if (i + 1) % 10 == 0:
                print(f"[INGEST] Processed {i+1}/{len(data)} Gmail messages")

    elif service == 'google_drive':
        print(f"[INGEST] Processing {len(data)} Google Drive files")
        for i, file in enumerate(data):
            content = file['content']
            file_id = file.get('id', str(uuid.uuid4()))  # Drive file ID
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

            # Generate content hash for deduplication
            content_hash = utils.generate_content_hash(text)

            # Check if this chunk already exists
            existing_chunk = utils.check_chunk_exists(user_id, 'google_drive', content_hash)
            if existing_chunk:
                utils.update_chunk_last_seen(existing_chunk['id'], sync_job_id)
                items_skipped += 1
                source_ids_seen.append(file_id)
                if (i + 1) % 5 == 0:
                    print(f"[INGEST] Processed {i+1}/{len(data)} Drive files (skipped {items_skipped} duplicates)")
                continue

            embedding = utils.embedding_model.encode(text).tolist()
            vector_id = str(uuid.uuid4())
            try:
                source_ts = _extract_source_timestamp(file, service)
                facts = extract_facts_from_chunk(text, source_ts, vector_id, user_id)
                for fact in facts:
                    process_extracted_claim(fact)
            except Exception as e:
                print(f"[FACTS] Error extracting facts from drive file: {e}")
            vectors.append({
                'id': vector_id,
                'values': embedding,
                'metadata': {
                    'text': text,
                    'source': 'google_drive',
                    'type': 'file',
                    'title': title,
                    'mime_type': file['mime_type'],
                    'modified_date': file.get('modified_time', '')[:50] if file.get('modified_time') else '',
                    'file_id': file_id,
                    'content_hash': content_hash
                }
            })
            source_ids_seen.append(file_id)
            items_created += 1
            if (i + 1) % 5 == 0:
                print(f"[INGEST] Processed {i+1}/{len(data)} Drive files")
    
    elif service == 'apple_notes':
        print(f"[INGEST] Processing {len(data)} Apple Notes")
        for i, note in enumerate(data):
            name = note.get('name', 'Untitled')
            body = note.get('body', '')
            created = note.get('created', '')
            modified = note.get('modified', '')
            note_id = note.get('id', str(uuid.uuid4()))  # Apple Note ID
            
            # Truncate body if too long
            if len(body) > 3000:
                body = body[:3000] + "... (truncated)"
            
            text = f"Note: {name}\n"
            if created:
                text += f"Created: {created}\n"
            if modified:
                text += f"Modified: {modified}\n"
            text += f"\n{body}"
            
            # Generate content hash for deduplication
            content_hash = utils.generate_content_hash(text)

            # Check if this chunk already exists
            existing_chunk = utils.check_chunk_exists(user_id, 'apple_notes', content_hash)
            if existing_chunk:
                utils.update_chunk_last_seen(existing_chunk['id'], sync_job_id)
                items_skipped += 1
                source_ids_seen.append(note_id)
                if (i + 1) % 10 == 0:
                    print(f"[INGEST] Processed {i+1}/{len(data)} notes (skipped {items_skipped} duplicates)")
                continue

            embedding = utils.embedding_model.encode(text).tolist()
            vector_id = str(uuid.uuid4())
            try:
                source_ts = _extract_source_timestamp(note, service)
                facts = extract_facts_from_chunk(text, source_ts, vector_id, user_id)
                for fact in facts:
                    process_extracted_claim(fact)
            except Exception as e:
                print(f"[FACTS] Error extracting facts from note: {e}")
            vectors.append({
                'id': vector_id,
                'values': embedding,
                'metadata': {
                    'text': text,
                    'source': 'apple_notes',
                    'type': 'note',
                    'note_name': name,
                    'created_date': created[:50] if created else '',
                    'modified_date': modified[:50] if modified else '',
                    'note_id': note_id,
                    'content_hash': content_hash
                }
            })
            source_ids_seen.append(note_id)
            items_created += 1
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
            event_id = event.get('id', str(uuid.uuid4()))  # Calendar event ID
            
            text = f"Calendar Event: {summary}\n"
            text += f"Calendar: {calendar}\n"
            text += f"Start: {start_date}\n"
            text += f"End: {end_date}\n"
            if location:
                text += f"Location: {location}\n"
            if notes:
                text += f"Notes: {notes}\n"
            
            # Generate content hash for deduplication
            content_hash = utils.generate_content_hash(text)

            # Check if this chunk already exists
            existing_chunk = utils.check_chunk_exists(user_id, 'apple_calendar', content_hash)
            if existing_chunk:
                utils.update_chunk_last_seen(existing_chunk['id'], sync_job_id)
                items_skipped += 1
                source_ids_seen.append(event_id)
                if (i + 1) % 10 == 0:
                    print(f"[INGEST] Processed {i+1}/{len(data)} calendar events (skipped {items_skipped} duplicates)")
                continue

            embedding = utils.embedding_model.encode(text).tolist()
            vector_id = str(uuid.uuid4())
            try:
                source_ts = _extract_source_timestamp(event, service)
                facts = extract_facts_from_chunk(text, source_ts, vector_id, user_id)
                for fact in facts:
                    process_extracted_claim(fact)
            except Exception as e:
                print(f"[FACTS] Error extracting facts from calendar event: {e}")
            vectors.append({
                'id': vector_id,
                'values': embedding,
                'metadata': {
                    'text': text,
                    'source': 'apple_calendar',
                    'type': 'calendar_event',
                    'calendar': calendar,
                    'event_title': summary,
                    'start_date': start_date[:50] if start_date else '',
                    'end_date': end_date[:50] if end_date else '',
                    'event_id': event_id,
                    'content_hash': content_hash
                }
            })
            source_ids_seen.append(event_id)
            items_created += 1
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
            song_id = attributes.get('id', str(uuid.uuid4()))  # Apple Music song ID
            
            text = f"Song: {name}\n"
            text += f"Artist: {artist}\n"
            text += f"Album: {album}\n"
            text += f"Duration: {duration:.1f} seconds\n"
            if genre:
                text += f"Genres: {', '.join(genre)}\n"
            
            # Generate content hash for deduplication
            content_hash = utils.generate_content_hash(text)

            # Check if this chunk already exists
            existing_chunk = utils.check_chunk_exists(user_id, 'apple_music', content_hash)
            if existing_chunk:
                utils.update_chunk_last_seen(existing_chunk['id'], sync_job_id)
                items_skipped += 1
                source_ids_seen.append(song_id)
                if (i + 1) % 5 == 0:
                    print(f"[INGEST] Processed {i+1}/{len(songs)} songs (skipped {items_skipped} duplicates)")
                continue

            embedding = utils.embedding_model.encode(text).tolist()
            vector_id = str(uuid.uuid4())
            try:
                source_ts = _extract_source_timestamp(song, service)
                facts = extract_facts_from_chunk(text, source_ts, vector_id, user_id)
                for fact in facts:
                    process_extracted_claim(fact)
            except Exception as e:
                print(f"[FACTS] Error extracting facts from music data: {e}")
            vectors.append({
                'id': vector_id,
                'values': embedding,
                'metadata': {
                    'text': text,
                    'source': 'apple_music',
                    'type': 'song',
                    'song_name': name,
                    'artist': artist,
                    'album': album,
                    'song_id': song_id,
                    'content_hash': content_hash
                }
            })
            source_ids_seen.append(song_id)
            items_created += 1
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
            album_id = attributes.get('id', str(uuid.uuid4()))  # Apple Music album ID
            
            text = f"Album: {name}\n"
            text += f"Artist: {artist}\n"
            text += f"Release Date: {release_date}\n"
            if genre:
                text += f"Genres: {', '.join(genre)}\n"
            
            # Generate content hash for deduplication
            content_hash = utils.generate_content_hash(text)

            # Check if this chunk already exists
            existing_chunk = utils.check_chunk_exists(user_id, 'apple_music', content_hash)
            if existing_chunk:
                utils.update_chunk_last_seen(existing_chunk['id'], sync_job_id)
                items_skipped += 1
                source_ids_seen.append(album_id)
                if (i + 1) % 5 == 0:
                    print(f"[INGEST] Processed {i+1}/{len(albums)} albums (skipped {items_skipped} duplicates)")
                continue

            embedding = utils.embedding_model.encode(text).tolist()
            vector_id = str(uuid.uuid4())
            try:
                source_ts = _extract_source_timestamp(album, service)
                facts = extract_facts_from_chunk(text, source_ts, vector_id, user_id)
                for fact in facts:
                    process_extracted_claim(fact)
            except Exception as e:
                print(f"[FACTS] Error extracting facts from music data: {e}")
            vectors.append({
                'id': vector_id,
                'values': embedding,
                'metadata': {
                    'text': text,
                    'source': 'apple_music',
                    'type': 'album',
                    'album_name': name,
                    'artist': artist,
                    'album_id': album_id,
                    'content_hash': content_hash
                }
            })
            source_ids_seen.append(album_id)
            items_created += 1
            if (i + 1) % 5 == 0:
                print(f"[INGEST] Processed {i+1}/{len(albums)} albums")
        
        # Process artists
        artists = data.get('results', {}).get('artists', {}).get('data', [])
        for i, artist_data in enumerate(artists):
            attributes = artist_data.get('attributes', {})
            name = attributes.get('name', 'Unknown')
            genre = attributes.get('genreNames', [])
            artist_id = attributes.get('id', str(uuid.uuid4()))  # Apple Music artist ID
            
            text = f"Artist: {name}\n"
            if genre:
                text += f"Genres: {', '.join(genre)}\n"
            
            # Generate content hash for deduplication
            content_hash = utils.generate_content_hash(text)

            # Check if this chunk already exists
            existing_chunk = utils.check_chunk_exists(user_id, 'apple_music', content_hash)
            if existing_chunk:
                utils.update_chunk_last_seen(existing_chunk['id'], sync_job_id)
                items_skipped += 1
                source_ids_seen.append(artist_id)
                if (i + 1) % 5 == 0:
                    print(f"[INGEST] Processed {i+1}/{len(artists)} artists (skipped {items_skipped} duplicates)")
                continue

            embedding = utils.embedding_model.encode(text).tolist()
            vector_id = str(uuid.uuid4())
            try:
                source_ts = _extract_source_timestamp(artist_data, service)
                facts = extract_facts_from_chunk(text, source_ts, vector_id, user_id)
                for fact in facts:
                    process_extracted_claim(fact)
            except Exception as e:
                print(f"[FACTS] Error extracting facts from music data: {e}")
            vectors.append({
                'id': vector_id,
                'values': embedding,
                'metadata': {
                    'text': text,
                    'source': 'apple_music',
                    'type': 'artist',
                    'artist_name': name,
                    'artist_id': artist_id,
                    'content_hash': content_hash
                }
            })
            source_ids_seen.append(artist_id)
            items_created += 1
            if (i + 1) % 5 == 0:
                print(f"[INGEST] Processed {i+1}/{len(artists)} artists")
    
    # Upsert vectors and record in tracking table
    print(f"[INGEST] Upserting {len(vectors)} vectors to Pinecone")
    success_count = 0
    for i, vector in enumerate(vectors):
        print(f"[INGEST] Upserting vector {i+1}/{len(vectors)}")
        try:
            index_to_use.upsert(vectors=[vector])
            
            # Record the ingested chunk in Supabase
            vector_id = vector['id']
            content_hash = vector['metadata'].get('content_hash', '')
            source_id = vector['metadata'].get('event_id') or vector['metadata'].get('message_id') or vector['metadata'].get('file_id') or vector['metadata'].get('note_id') or vector['metadata'].get('song_id') or vector['metadata'].get('album_id') or vector['metadata'].get('artist_id')
            content_preview = vector['metadata'].get('text', '')
            
            if sync_job_id and content_hash:
                utils.record_ingested_chunk(
                    user_id=user_id,
                    source_type=service,
                    source_id=source_id,
                    chunk_hash=content_hash,
                    pinecone_vector_id=vector_id,
                    content_preview=content_preview,
                    metadata=vector['metadata'],
                    sync_job_id=sync_job_id
                )
            
            success_count += 1
        except Exception as e:
            print(f"[INGEST] Error upserting vector {i+1}: {e}")
            continue
    
    print(f"[INGEST] Successfully upserted {success_count}/{len(vectors)} vectors")
    
    # Mark stale data as deleted if sync_job_id is provided
    if sync_job_id and source_ids_seen:
        print(f"[INGEST] Marking stale data for user {user_id}, source {service}")
        items_deleted = utils.mark_stale_data(user_id, service, source_ids_seen, sync_job_id)
        print(f"[INGEST] Marked {items_deleted} items as deleted")
        
        # Update sync job with final metrics
        utils.update_sync_job(
            sync_job_id,
            status='completed',
            items_processed=len(data),
            items_created=items_created,
            items_updated=items_updated,
            items_skipped=items_skipped,
            items_deleted=items_deleted,
            source_ids_seen=source_ids_seen
        )
    
    return success_count
