import os
import sys
import asyncio
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks
import tempfile
import uuid
from pinecone import Pinecone
from sentence_transformers import SentenceTransformer

sys.path.insert(0, str(Path(__file__).parent.parent))

from models import DocumentResponse, CreateUserDatabaseRequest, AppleMusicRequest
from utils import RAW_DOCS_DIR, PROCESSED_CHUNKS_DIR, CREDENTIALS_DIR
import utils
from services.apple_services import fetch_apple_notes, fetch_apple_calendar, fetch_user_library_with_token

sys.path.append(str(Path(__file__).parent.parent.parent / "scripts"))
from entity_extraction import extract_entities_for_document

router = APIRouter()


@router.post("/fetch-apple-notes")
async def fetch_apple_notes_endpoint():
    """Fetch Apple Notes using AppleScript (macOS only)"""
    try:
        return await fetch_apple_notes()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/fetch-apple-calendar")
async def fetch_apple_calendar_endpoint(request: Optional[CreateUserDatabaseRequest] = None):
    """Fetch Apple Calendar events using CalDAV (preferred) or AppleScript (fallback)"""
    try:
        apple_calendar_email = request.apple_calendar_email if request else None
        apple_calendar_password = request.apple_calendar_password if request else None
        return await fetch_apple_calendar(apple_calendar_email, apple_calendar_password)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ingest-apple-notes")
async def ingest_apple_notes_endpoint(request: CreateUserDatabaseRequest):
    """Fetch and ingest Apple Notes into the database"""
    try:
        print(f"[APPLE NOTES INGEST] Starting ingestion for user {request.user_id}")
        
        # Get user's Pinecone index
        if not utils.supabase:
            raise HTTPException(status_code=503, detail="Supabase not initialized")

        user_settings = utils.supabase.table("user_settings").select("*").eq("user_id", request.user_id).execute()

        if not user_settings.data:
            raise HTTPException(status_code=400, detail="User database not found. Please create database first.")

        pinecone_index_name = user_settings.data[0].get("pinecone_index")
        print(f"[APPLE NOTES INGEST] Using Pinecone index: {pinecone_index_name}")
        
        # Fetch notes
        print(f"[APPLE NOTES INGEST] Fetching notes...")
        notes_response = await fetch_apple_notes()
        notes_data = notes_response["notes"]
        print(f"[APPLE NOTES INGEST] Fetched {len(notes_data)} notes")
        
        # Process and ingest
        if not utils.embedding_model:
            print(f"[APPLE NOTES INGEST] Initializing embedding model...")
            utils.embedding_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
        
        if not os.getenv("PINECONE_API_KEY"):
            raise HTTPException(status_code=500, detail="PINECONE_API_KEY not found in environment variables")
        
        pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
        index_to_use = pc.Index(pinecone_index_name)
        print(f"[APPLE NOTES INGEST] Connected to Pinecone index")
        
        vectors = []
        for note in notes_data:
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
        
        print(f"[APPLE NOTES INGEST] Created {len(vectors)} vectors")
        
        # Upsert in batches
        batch_size = 100
        for i in range(0, len(vectors), batch_size):
            batch = vectors[i:i+batch_size]
            print(f"[APPLE NOTES INGEST] Upserting batch {i//batch_size + 1}/{(len(vectors) + batch_size - 1)//batch_size}")
            try:
                index_to_use.upsert(vectors=batch)
            except Exception as e:
                print(f"[APPLE NOTES INGEST] Error upserting batch: {e}")
                continue
        
        print(f"[APPLE NOTES INGEST] Successfully ingested {len(notes_data)} notes")
        
        return {
            "message": f"Successfully ingested {len(notes_data)} Apple Notes",
            "count": len(notes_data)
        }
    
    except Exception as e:
        print(f"[APPLE NOTES INGEST] ERROR: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ingest-apple-calendar")
async def ingest_apple_calendar_endpoint(request: CreateUserDatabaseRequest):
    """Fetch and ingest Apple Calendar events into the database"""
    try:
        print(f"[APPLE CALENDAR INGEST] Starting ingestion for user {request.user_id}")
        
        # Get user's Pinecone index
        if not utils.supabase:
            raise HTTPException(status_code=503, detail="Supabase not initialized")

        user_settings = utils.supabase.table("user_settings").select("*").eq("user_id", request.user_id).execute()

        if not user_settings.data:
            raise HTTPException(status_code=400, detail="User database not found. Please create database first.")

        pinecone_index_name = user_settings.data[0].get("pinecone_index")
        print(f"[APPLE CALENDAR INGEST] Using Pinecone index: {pinecone_index_name}")
        
        # Fetch calendar events with CalDAV credentials if provided
        print(f"[APPLE CALENDAR INGEST] Fetching calendar events...")
        
        # Create a temporary request object with CalDAV credentials
        from models import UploadDocumentsRequest
        temp_request = UploadDocumentsRequest(
            user_id=request.user_id,
            permissions={},
            apple_calendar_email=request.apple_calendar_email,
            apple_calendar_password=request.apple_calendar_password
        )
        
        calendar_response = await fetch_apple_calendar(temp_request.apple_calendar_email, temp_request.apple_calendar_password)
        events_data = calendar_response["events"]
        print(f"[APPLE CALENDAR INGEST] Fetched {len(events_data)} events")
        
        # Process and ingest
        if not utils.embedding_model:
            print(f"[APPLE CALENDAR INGEST] Initializing embedding model...")
            utils.embedding_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
        
        if not os.getenv("PINECONE_API_KEY"):
            raise HTTPException(status_code=500, detail="PINECONE_API_KEY not found in environment variables")
        
        pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
        index_to_use = pc.Index(pinecone_index_name)
        print(f"[APPLE CALENDAR INGEST] Connected to Pinecone index")
        
        vectors = []
        for event in events_data:
            # Truncate notes if too long
            notes = event.get('notes', '')
            if len(notes) > 1000:
                notes = notes[:1000] + "... (truncated)"
            
            # Truncate summary if too long
            summary = event.get('summary', 'No Title')
            if len(summary) > 100:
                summary = summary[:100] + "..."
            
            text = f"Calendar Event: {summary}\n"
            text += f"Calendar: {event['calendar']}\n"
            text += f"Start: {event['start_date']}\n"
            text += f"End: {event['end_date']}\n"
            
            if event.get('location'):
                text += f"Location: {event['location']}\n"
            
            if notes:
                text += f"\nNotes:\n{notes}\n"
            
            embedding = utils.embedding_model.encode(text).tolist()
            vectors.append({
                'id': str(uuid.uuid4()),
                'values': embedding,
                'metadata': {
                    'text': text,
                    'source': 'apple_calendar',
                    'type': 'calendar_event',
                    'calendar': event['calendar'],
                    'event_title': summary,
                    'start_date': event['start_date'][:50] if event.get('start_date') else '',
                    'end_date': event['end_date'][:50] if event.get('end_date') else ''
                }
            })
        
        print(f"[APPLE CALENDAR INGEST] Created {len(vectors)} vectors")
        
        # Upsert one at a time to avoid batch size issues
        for i, vector in enumerate(vectors):
            print(f"[APPLE CALENDAR INGEST] Upserting vector {i+1}/{len(vectors)}")
            try:
                index_to_use.upsert(vectors=[vector])
            except Exception as e:
                print(f"[APPLE CALENDAR INGEST] Error upserting vector {i+1}: {e}")
                continue
        
        print(f"[APPLE CALENDAR INGEST] Successfully ingested {len(events_data)} events")
        
        return {
            "message": f"Successfully ingested {len(events_data)} Apple Calendar events",
            "count": len(events_data)
        }
    
    except Exception as e:
        print(f"[APPLE CALENDAR INGEST] ERROR: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ingest-apple-music")
async def ingest_apple_music_endpoint(request: AppleMusicRequest):
    """Fetch and ingest Apple Music data into the database using Music User Token"""
    try:
        print(f"[APPLE MUSIC INGEST] Starting ingestion for user {request.user_id}")

        # Get user's Pinecone index
        if not utils.supabase:
            raise HTTPException(status_code=503, detail="Supabase not initialized")

        user_settings = utils.supabase.table("user_settings").select("*").eq("user_id", request.user_id).execute()

        if not user_settings.data:
            raise HTTPException(status_code=400, detail="User database not found. Please create database first.")

        pinecone_index_name = user_settings.data[0].get("pinecone_index")
        print(f"[APPLE MUSIC INGEST] Using Pinecone index: {pinecone_index_name}")

        # Use Music User Token from request (from Apple ID authentication)
        music_user_token = request.music_user_token

        if not music_user_token:
            # Fallback to developer credentials if no user token provided
            key_id = request.key_id or os.getenv("APPLE_MUSIC_KEY_ID")
            team_id = request.team_id or os.getenv("APPLE_MUSIC_TEAM_ID")
            private_key = request.private_key or os.getenv("APPLE_MUSIC_PRIVATE_KEY_PATH")

            if not all([key_id, team_id, private_key]):
                raise HTTPException(
                    status_code=400,
                    detail="Apple Music credentials not provided. Please provide music_user_token or key_id, team_id, and private_key."
                )

            # Import the fetch_apple_music script
            scripts_path = Path(__file__).parent.parent.parent / "scripts"
            sys.path.append(str(scripts_path))

            from fetch_apple_music import generate_developer_token, fetch_user_library, format_song, format_album, format_artist

            # If private_key is a file path, read from file. Otherwise, treat as the key content
            if request.private_key and len(request.private_key) > 100 and '\n' in request.private_key:
                # It's the actual key content, save to temp file
                print(f"[APPLE MUSIC INGEST] Using provided private key content")
                with tempfile.NamedTemporaryFile(mode='w', suffix='.p8', delete=False) as f:
                    f.write(request.private_key)
                    private_key_path = f.name
            else:
                # It's a file path
                private_key_path = private_key

            # Generate developer token
            print(f"[APPLE MUSIC INGEST] Generating developer token...")
            token = generate_developer_token(key_id, team_id, private_key_path)

            if not token:
                raise HTTPException(status_code=500, detail="Failed to generate Apple Music developer token")

            print(f"[APPLE MUSIC INGEST] Developer token generated successfully")

            # Fetch music data using developer token (catalog search)
            print(f"[APPLE MUSIC INGEST] Fetching music data...")
            music_data = fetch_user_library(token, storefront='us')
        else:
            # Use Music User Token to fetch user's library
            print(f"[APPLE MUSIC INGEST] Using Music User Token to fetch user library")
            music_data = await fetch_user_library_with_token(music_user_token)

        if not music_data:
            raise HTTPException(status_code=500, detail="Failed to fetch Apple Music data")

        print(f"[APPLE MUSIC INGEST] Music data fetched successfully")

        # Process and ingest
        if not utils.embedding_model:
            print(f"[APPLE MUSIC INGEST] Initializing embedding model...")
            utils.embedding_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')

        if not os.getenv("PINECONE_API_KEY"):
            raise HTTPException(status_code=500, detail="PINECONE_API_KEY not found in environment variables")

        pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
        index_to_use = pc.Index(pinecone_index_name)
        print(f"[APPLE MUSIC INGEST] Connected to Pinecone index")

        vectors = []
        total_items = 0

        # Process songs
        songs = music_data.get('results', {}).get('songs', {}).get('data', [])
        for song in songs:
            text = format_song(song)
            embedding = utils.embedding_model.encode(text).tolist()
            vectors.append({
                'id': str(uuid.uuid4()),
                'values': embedding,
                'metadata': {
                    'text': text,
                    'source': 'apple_music',
                    'type': 'song',
                    'data_type': 'song'
                }
            })
            total_items += 1

        # Process albums
        albums = music_data.get('results', {}).get('albums', {}).get('data', [])
        for album in albums:
            text = format_album(album)
            embedding = utils.embedding_model.encode(text).tolist()
            vectors.append({
                'id': str(uuid.uuid4()),
                'values': embedding,
                'metadata': {
                    'text': text,
                    'source': 'apple_music',
                    'type': 'album',
                    'data_type': 'album'
                }
            })
            total_items += 1

        # Process artists
        artists = music_data.get('results', {}).get('artists', {}).get('data', [])
        for artist in artists:
            text = format_artist(artist)
            embedding = utils.embedding_model.encode(text).tolist()
            vectors.append({
                'id': str(uuid.uuid4()),
                'values': embedding,
                'metadata': {
                    'text': text,
                    'source': 'apple_music',
                    'type': 'artist',
                    'data_type': 'artist'
                }
            })
            total_items += 1

        print(f"[APPLE MUSIC INGEST] Created {len(vectors)} vectors from {total_items} music items")

        # Upsert in batches
        batch_size = 100
        for i in range(0, len(vectors), batch_size):
            batch = vectors[i:i+batch_size]
            print(f"[APPLE MUSIC INGEST] Upserting batch {i//batch_size + 1}/{(len(vectors) + batch_size - 1)//batch_size}")
            try:
                index_to_use.upsert(vectors=batch)
            except Exception as e:
                print(f"[APPLE MUSIC INGEST] Error upserting batch: {e}")
                continue

        print(f"[APPLE MUSIC INGEST] Successfully ingested {total_items} Apple Music items")

        return {
            "message": f"Successfully ingested {total_items} Apple Music items (songs, albums, artists)",
            "count": total_items
        }

    except Exception as e:
        print(f"[APPLE MUSIC INGEST] ERROR: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
