"""
Batch fact extraction to reduce LLM costs.
Groups 3-5 short chunks per LLM call instead of one per call.
"""

import sys
from pathlib import Path
from typing import List, Dict, Tuple
import json

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import utils
from facts.vocabulary import ENTITY_CATEGORIES, ALL_ENTITY_KEYS


def extract_facts_from_batch(chunks: List[Dict], user_id: str) -> List[Dict]:
    """
    Extract facts from 3-5 chunks in a single LLM call.
    
    Args:
        chunks: List of chunk dicts with keys: id, text, source_timestamp, source_type
        user_id: User ID for fact ownership
    
    Returns:
        List of extracted fact claims
    """
    if not utils.llm:
        print("[BATCH_EXTRACT] LLM not available")
        return []
    
    if not chunks or len(chunks) == 0:
        return []
    
    # Limit batch size to 5 chunks to avoid overwhelming the LLM
    chunks = chunks[:5]
    
    # Build batch prompt
    chunk_texts = []
    for i, chunk in enumerate(chunks):
        text = chunk.get('text', '')
        source = chunk.get('source_type', 'unknown')
        ts = chunk.get('source_timestamp', '')
        
        chunk_texts.append(f"Chunk {i+1} ({source}, {ts}):\n{text[:800]}")
    
    batch_content = "\n\n".join(chunk_texts)
    
    prompt = f"""Extract factual claims about the user from these document chunks.

{batch_content}

IMPORTANT RULES:
- Only extract PERSISTENT STATES about the user (employer, location, relationship status, health conditions, etc.)
- SKIP events (meetings, trips, one-time activities)
- SKIP hypothetical statements ("thinking about", "considering")
- REQUIRE confidence >= 0.6
- Use ONLY these entity categories: {list(ENTITY_CATEGORIES.keys())}
- Use ONLY these entity keys: {ALL_ENTITY_KEYS}

For each fact claim, provide:
- entity_key (from the approved list)
- entity_category (from the approved list)
- value (the specific fact)
- confidence (0.0-1.0)
- tense (present/past)
- source_timestamp (use the timestamp provided with each chunk)
- chunk_ids (list of chunk IDs where this was found)

Return ONLY a JSON array. No explanations.

Example:
[
  {{
    "entity_key": "employer",
    "entity_category": "work",
    "value": "Google",
    "confidence": 0.9,
    "tense": "present",
    "source_timestamp": "2024-03-15T10:00:00Z",
    "chunk_ids": ["chunk_1", "chunk_2"]
  }}
]"""

    try:
        response = utils.llm.invoke(prompt).content.strip()
        
        # Parse JSON response
        facts = []
        try:
            # Try direct JSON parse first
            facts = json.loads(response)
            if not isinstance(facts, list):
                facts = []
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code blocks
            import re
            json_match = re.search(r'```(?:json)?\s*(\[.*?\])\s*```', response, re.DOTALL)
            if json_match:
                try:
                    facts = json.loads(json_match.group(1))
                except json.JSONDecodeError:
                    facts = []
            else:
                # Last resort: any array-like structure
                array_match = re.search(r'\[.*?\]', response, re.DOTALL)
                if array_match:
                    try:
                        facts = json.loads(array_match.group(0))
                    except json.JSONDecodeError:
                        facts = []
        
        # Validate and enrich facts with chunk IDs
        validated_facts = []
        for fact in facts:
            if not isinstance(fact, dict):
                continue
            
            # Validate required fields
            entity_key = fact.get('entity_key')
            entity_category = fact.get('entity_category')
            value = fact.get('value')
            confidence = fact.get('confidence', 0)
            
            if not all([entity_key, entity_category, value]):
                continue
            
            # Validate against vocabulary
            if entity_category not in ENTITY_CATEGORIES:
                continue
            if entity_key not in ALL_ENTITY_KEYS:
                continue
            if confidence < 0.6:
                continue
            
            # Ensure chunk_ids is populated
            chunk_ids = fact.get('chunk_ids', [])
            if not chunk_ids:
                # If no chunk_ids provided, associate with all chunks in batch
                chunk_ids = [chunk.get('id') for chunk in chunks]
            
            # Add user_id and clean up
            validated_fact = {
                'entity_key': entity_key,
                'entity_category': entity_category,
                'value': str(value).strip(),
                'confidence': float(confidence),
                'tense': fact.get('tense', 'present'),
                'source_timestamp': fact.get('source_timestamp'),
                'chunk_ids': chunk_ids,
                'user_id': user_id
            }
            
            validated_facts.append(validated_fact)
        
        print(f"[BATCH_EXTRACT] Extracted {len(validated_facts)} facts from {len(chunks)} chunks")
        return validated_facts
        
    except Exception as e:
        print(f"[BATCH_EXTRACT] Error: {e}")
        return []


def group_chunks_for_batch(chunks: List[Dict], max_batch_size: int = 5) -> List[List[Dict]]:
    """
    Group chunks into batches for batch extraction.
    Prioritizes shorter chunks together to maximize tokens per call.
    
    Args:
        chunks: List of chunk dicts
        max_batch_size: Maximum chunks per batch
    
    Returns:
        List of chunk batches
    """
    if not chunks:
        return []
    
    # Sort chunks by text length (shorter first) to optimize batching
    sorted_chunks = sorted(chunks, key=lambda x: len(x.get('text', '')))
    
    batches = []
    current_batch = []
    current_length = 0
    
    for chunk in sorted_chunks:
        chunk_length = len(chunk.get('text', ''))
        
        # If adding this chunk would exceed reasonable size, start new batch
        if (len(current_batch) >= max_batch_size or 
            current_length + chunk_length > 2000):  # 2000 chars per batch limit
            if current_batch:
                batches.append(current_batch)
                current_batch = []
                current_length = 0
        
        current_batch.append(chunk)
        current_length += chunk_length
    
    # Add remaining chunks
    if current_batch:
        batches.append(current_batch)
    
    return batches


async def extract_facts_with_budget(chunks: List[Dict], user_id: str, daily_limit: int = 200) -> Tuple[List[Dict], int]:
    """
    Extract facts from chunks with daily budget limits.
    
    Args:
        chunks: List of chunks to process
        user_id: User ID
        daily_limit: Maximum extraction calls per day
    
    Returns:
        Tuple of (extracted_facts, calls_used)
    """
    if not utils.supabase:
        print("[BATCH_EXTRACT] Supabase not available")
        return [], 0
    
    # Check current daily usage
    try:
        today = datetime.now().date().isoformat()
        usage_result = utils.supabase.table("extraction_usage").select("calls_used").eq("user_id", user_id).eq("date", today).execute()
        
        calls_used_today = 0
        if usage_result.data:
            calls_used_today = usage_result.data[0].get('calls_used', 0)
        
        remaining_budget = daily_limit - calls_used_today
        
        if remaining_budget <= 0:
            print(f"[BATCH_EXTRACT] Daily limit reached ({daily_limit})")
            return [], 0
            
    except Exception as e:
        print(f"[BATCH_EXTRACT] Error checking usage: {e}")
        remaining_budget = daily_limit
    
    # Group chunks into batches
    batches = group_chunks_for_batch(chunks)
    
    # Limit batches to remaining budget
    batches_to_process = batches[:remaining_budget]
    all_facts = []
    calls_used = 0
    
    for batch in batches_to_process:
        facts = extract_facts_from_batch(batch, user_id)
        all_facts.extend(facts)
        calls_used += 1
        
        # Update usage tracking
        try:
            utils.supabase.table("extraction_usage").upsert({
                'user_id': user_id,
                'date': datetime.now().date().isoformat(),
                'calls_used': calls_used_today + calls_used
            }, on_conflict="user_id,date").execute()
        except Exception as e:
            print(f"[BATCH_EXTRACT] Error updating usage: {e}")
    
    print(f"[BATCH_EXTRACT] Used {calls_used}/{remaining_budget} calls, extracted {len(all_facts)} facts")
    return all_facts, calls_used


# Need to import datetime for usage tracking
from datetime import datetime
