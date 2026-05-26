"""
One-time backfill job to extract facts from existing Apple Notes chunks.
Run this after the fact pipeline is deployed but before deprecating regex detection.
Customized for Apple Notes data source only.
"""

import asyncio
import sys
from pathlib import Path
from typing import List, Dict
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import utils
from facts.extractor import extract_facts_from_chunk
from facts.pipeline import process_extracted_claim


async def run_backfill_for_user(user_id: str, batch_size: int = 50, daily_limit: int = 200):
    """Run fact extraction over all existing Apple Notes chunks for a user"""
    if not utils.supabase:
        print("[BACKFILL] Supabase not available")
        return
    
    print(f"[BACKFILL] Starting backfill for user {user_id} (Apple Notes only)")
    
    # Get all Apple Notes chunks for this user that haven't been processed for facts
    # We'll track processed chunks in a separate table or metadata to avoid re-processing
    try:
        # First, let's see what Apple Notes chunks exist
        chunks_result = utils.supabase.table("ingested_chunks").select(
            "id", "source_type", "source_id", "content_preview", "metadata", "ingested_at"
        ).eq("user_id", user_id).eq("source_type", "apple_notes").eq("is_deleted", False).order("ingested_at", desc=True).execute()
        
        if not chunks_result.data:
            print(f"[BACKFILL] No Apple Notes chunks found for user {user_id}")
            return
        
        total_chunks = len(chunks_result.data)
        print(f"[BACKFILL] Found {total_chunks} Apple Notes chunks to process")
        
        # Process in batches to avoid overwhelming the LLM
        processed = 0
        daily_used = 0
        
        for i in range(0, total_chunks, batch_size):
            batch = chunks_result.data[i:i + batch_size]
            print(f"[BACKFILL] Processing batch {i//batch_size + 1}/{(total_chunks + batch_size - 1)//batch_size}")
            
            # Check daily limit
            if daily_used >= daily_limit:
                print(f"[BACKFILL] Daily limit reached ({daily_limit}). Stopping for today.")
                break
            
            batch_tasks = []
            for chunk in batch:
                if daily_used >= daily_limit:
                    break
                
                # Reconstruct chunk text from stored data
                # Note: ingested_chunks only stores content_preview (200 chars)
                # For full backfill, we'd need to fetch from Pinecone or have stored full content
                # This is a simplified version that works with previews
                chunk_text = chunk.get('content_preview', '')
                if not chunk_text or len(chunk_text) < 20:
                    continue
                
                # Extract source timestamp from metadata
                metadata = chunk.get('metadata', {})
                source_ts = metadata.get('created_date') or metadata.get('date') or chunk.get('ingested_at')
                if source_ts and isinstance(source_ts, str):
                    try:
                        source_ts = datetime.fromisoformat(source_ts.replace('Z', '+00:00'))
                    except:
                        source_ts = chunk.get('ingested_at')
                
                chunk_id = chunk.get('id')
                task = process_chunk_for_backfill(chunk_id, chunk_text, source_ts, user_id)
                batch_tasks.append(task)
                daily_used += 1
            
            # Process batch concurrently
            if batch_tasks:
                results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                processed += len([r for r in results if not isinstance(r, Exception)])
                
                # Small delay to avoid rate limiting
                await asyncio.sleep(0.5)
        
        print(f"[BACKFILL] Completed. Processed {processed}/{total_chunks} chunks")
        
    except Exception as e:
        print(f"[BACKFILL] Error: {e}")
        import traceback
        traceback.print_exc()


async def process_chunk_for_backfill(chunk_id: str, text: str, source_ts, user_id: str):
    """Process a single chunk for fact extraction during backfill"""
    try:
        # Extract facts from the chunk
        facts = extract_facts_from_chunk(text, source_ts, chunk_id, user_id)
        
        if not facts:
            return 0
        
        # Process each extracted claim through the pipeline
        processed = 0
        for fact in facts:
            try:
                process_extracted_claim(fact)
                processed += 1
            except Exception as e:
                print(f"[BACKFILL] Error processing claim: {e}")
                continue
        
        return processed
        
    except Exception as e:
        print(f"[BACKFILL] Error processing chunk {chunk_id}: {e}")
        return 0


async def backfill_all_users():
    """Run backfill for all users who have ingested data"""
    if not utils.supabase:
        print("[BACKFILL] Supabase not available")
        return
    
    try:
        # Get all users who have ingested chunks
        users_result = utils.supabase.table("ingested_chunks").select("user_id").execute()
        
        if not users_result.data:
            print("[BACKFILL] No users with ingested data found")
            return
        
        # Get unique user IDs
        user_ids = list(set(row['user_id'] for row in users_result.data))
        print(f"[BACKFILL] Found {len(user_ids)} users to backfill")
        
        for user_id in user_ids:
            await run_backfill_for_user(user_id)
            print(f"[BACKFILL] Completed backfill for user {user_id}")
            
    except Exception as e:
        print(f"[BACKFILL] Error in backfill_all_users: {e}")


if __name__ == "__main__":
    # Run backfill
    asyncio.run(backfill_all_users())
