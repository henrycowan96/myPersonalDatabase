"""
Background worker for async fact extraction from Apple Notes.
Processes fact extraction jobs from the queue.
Customized for Apple Notes data source only.
"""

import asyncio
from datetime import datetime
from typing import Dict, Any, List
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import utils
from facts.router import extract_facts_for_doc
from facts.pipeline import process_extracted_claim


class FactExtractionWorker:
    """Background worker for processing fact extraction jobs."""
    
    def __init__(self):
        self.running = False
        self.poll_interval = 5  # seconds
    
    async def start(self):
        """Start the background worker."""
        self.running = True
        print("[FACTS WORKER] Starting background fact extraction worker (Apple Notes only)")
        
        while self.running:
            try:
                await self.process_next_job()
                await asyncio.sleep(self.poll_interval)
            except Exception as e:
                print(f"[FACTS WORKER] Error in worker loop: {e}")
                import traceback
                traceback.print_exc()
                await asyncio.sleep(self.poll_interval)
    
    def stop(self):
        """Stop the background worker."""
        self.running = False
        print("[FACTS WORKER] Stopping background fact extraction worker")
    
    async def process_next_job(self):
        """Process the next pending job from the queue."""
        if not utils.supabase:
            return
        
        try:
            # Get next pending job
            result = utils.supabase.table("fact_extraction_jobs").select("*").eq("status", "pending").order("created_at").limit(1).execute()
            
            if not result.data:
                return
            
            job = result.data[0]
            await self.process_job(job)
            
        except Exception as e:
            print(f"[FACTS WORKER] Error fetching job: {e}")
            import traceback
            traceback.print_exc()
    
    async def process_job(self, job: Dict[str, Any]):
        """Process a single fact extraction job."""
        job_id = job["id"]
        user_id = job["user_id"]
        sync_job_id = job["sync_job_id"]
        source_type = job["source_type"]
        
        # Only process Apple Notes jobs
        if source_type != "apple_notes":
            print(f"[FACTS WORKER] Skipping job {job_id} - source type {source_type} not supported (Apple Notes only)")
            await self.complete_job(job_id, 0, "Source type not supported")
            return
        
        print(f"[FACTS WORKER] Processing job {job_id} for user {user_id}, source {source_type}")
        
        # Update job status to processing
        try:
            utils.supabase.table("fact_extraction_jobs").update({
                "status": "processing",
                "started_at": datetime.now().isoformat()
            }).eq("id", job_id).execute()
        except Exception as e:
            print(f"[FACTS WORKER] Error updating job status: {e}")
            return
        
        try:
            # Fetch ingested chunks for this sync job
            chunks_result = utils.supabase.table("ingested_chunks").select("*").eq("user_id", user_id).eq("source_type", source_type).eq("sync_job_id", sync_job_id).execute()
            chunks = chunks_result.data or []
            
            if not chunks:
                print(f"[FACTS WORKER] No chunks found for job {job_id}")
                await self.complete_job(job_id, 0, "No chunks found")
                return
            
            print(f"[FACTS WORKER] Found {len(chunks)} chunks for job {job_id}")
            
            # Update total chunks
            utils.supabase.table("fact_extraction_jobs").update({
                "total_chunks": len(chunks)
            }).eq("id", job_id).execute()
            
            # Format chunks for router
            chunks_for_extraction = []
            for chunk in chunks:
                chunks_for_extraction.append({
                    'text': chunk.get('content_preview', ''),
                    'chunk_id': chunk.get('id'),
                    'source_timestamp': datetime.fromisoformat(chunk.get('created_at', datetime.now().isoformat())),
                })
            
            # Run tiered extraction
            doc_metadata = {
                'doc_id': sync_job_id,
                'source_type': source_type,
                'source_timestamp': datetime.now()
            }
            
            facts = await extract_facts_for_doc(chunks_for_extraction, doc_metadata, user_id)
            
            # Process each fact through the pipeline
            processed_count = 0
            for fact in facts:
                # Map chunk_id from router to actual chunk_id
                fact['source_chunk_id'] = fact.get('chunk_id')  # Router uses chunk_id field
                process_extracted_claim(fact)
                processed_count += 1
                
                # Update progress
                if processed_count % 10 == 0:
                    utils.supabase.table("fact_extraction_jobs").update({
                        "processed_chunks": processed_count,
                        "facts_extracted": processed_count
                    }).eq("id", job_id).execute()
            
            # Complete job
            await self.complete_job(job_id, len(facts))
            print(f"[FACTS WORKER] Completed job {job_id}, extracted {len(facts)} facts")
            
        except Exception as e:
            print(f"[FACTS WORKER] Error processing job {job_id}: {e}")
            import traceback
            traceback.print_exc()
            await self.fail_job(job_id, str(e))
    
    async def complete_job(self, job_id: str, facts_count: int, error_message: str = None):
        """Mark a job as completed."""
        update_data = {
            "status": "completed",
            "completed_at": datetime.now().isoformat(),
            "facts_extracted": facts_count,
            "processed_chunks": utils.supabase.table("fact_extraction_jobs").select("total_chunks").eq("id", job_id).execute().data[0].get("total_chunks", 0) if utils.supabase else 0
        }
        
        if error_message:
            update_data["error_message"] = error_message
        
        try:
            utils.supabase.table("fact_extraction_jobs").update(update_data).eq("id", job_id).execute()
        except Exception as e:
            print(f"[FACTS WORKER] Error completing job: {e}")
    
    async def fail_job(self, job_id: str, error_message: str):
        """Mark a job as failed."""
        try:
            utils.supabase.table("fact_extraction_jobs").update({
                "status": "failed",
                "completed_at": datetime.now().isoformat(),
                "error_message": error_message
            }).eq("id", job_id).execute()
        except Exception as e:
            print(f"[FACTS WORKER] Error failing job: {e}")


# Global worker instance
_worker = None


def start_background_worker():
    """Start the global background worker."""
    global _worker
    if _worker is None:
        _worker = FactExtractionWorker()
        asyncio.create_task(_worker.start())
    return _worker


def stop_background_worker():
    """Stop the global background worker."""
    global _worker
    if _worker:
        _worker.stop()
        _worker = None


def queue_fact_extraction_job(
    user_id: str,
    sync_job_id: str,
    source_type: str,
    total_chunks: int = 0
) -> str:
    """Queue a fact extraction job for background processing."""
    if not utils.supabase:
        return None
    
    try:
        result = utils.supabase.table("fact_extraction_jobs").insert({
            "user_id": user_id,
            "sync_job_id": sync_job_id,
            "source_type": source_type,
            "status": "pending",
            "total_chunks": total_chunks,
        }).execute()
        
        if result.data:
            job_id = result.data[0]["id"]
            print(f"[FACTS WORKER] Queued job {job_id} for user {user_id}, source {source_type}")
            return job_id
    except Exception as e:
        print(f"[FACTS WORKER] Error queuing job: {e}")
        import traceback
        traceback.print_exc()
    
    return None


def get_fact_extraction_status(sync_job_id: str) -> dict:
    """Get the status of fact extraction for a sync job."""
    if not utils.supabase:
        return {"status": "unknown"}
    
    try:
        result = utils.supabase.table("fact_extraction_jobs").select("*").eq("sync_job_id", sync_job_id).execute()
        
        if not result.data:
            return {"status": "not_found"}
        
        job = result.data[0]
        return {
            "status": job.get("status"),
            "total_chunks": job.get("total_chunks"),
            "processed_chunks": job.get("processed_chunks"),
            "facts_extracted": job.get("facts_extracted"),
            "error_message": job.get("error_message")
        }
    except Exception as e:
        print(f"[FACTS WORKER] Error getting job status: {e}")
        return {"status": "error"}
