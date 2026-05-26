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
    """Process fetched Apple Notes data and ingest into Pinecone with deduplication"""
    # Only Apple Notes is supported
    if service != 'apple_notes':
        print(f"[INGEST] Unsupported service: {service} (Apple Notes only)")
        return 0
    
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

    # All non-Apple Notes services disabled - only Apple Notes supported
    # Google Calendar disabled
    # Gmail disabled
    # Google Drive disabled
    # Apple Calendar disabled
    # Apple Music disabled
    
    # Apple Notes processing
    if service == 'apple_notes':
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
