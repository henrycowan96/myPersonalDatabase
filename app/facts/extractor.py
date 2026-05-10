"""
Fact extraction from document chunks using LLM.
Hooks into the existing ingestion pipeline after deduplication.
"""

import json
import re
from datetime import datetime
from typing import List, Dict, Any, Optional

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import utils
from facts.vocabulary import ALL_ENTITY_KEYS, ALL_ENTITY_CATEGORIES, get_category_for_key


EXTRACTION_SYSTEM_PROMPT_TEMPLATE = """You extract factual claims about a person's life from personal documents.
Return ONLY a JSON array. Each object must have exactly these fields:
- entity_key: one of [{entity_keys}]
- entity_category: one of [{entity_categories}]
- value: the specific claim as a short phrase (max 10 words)
- confidence: 0.0–1.0 (how confident you are this is a real, current claim)
- tense: "present" | "past" | "hypothetical"

Rules:
- Only extract claims about the document's author, not other people
- "present" tense only for things that appear to be currently true at the time of writing
- "hypothetical" for wishes, plans, or what-ifs ("I want to", "I should", "maybe someday")
- Skip events (meetings, trips) — only extract persistent states
- Skip anything with confidence below 0.6
- Return [] if no claims found

Entity keys available: {entity_keys}"""

EXTRACTION_SYSTEM_PROMPT = EXTRACTION_SYSTEM_PROMPT_TEMPLATE.format(
    entity_keys=", ".join(ALL_ENTITY_KEYS),
    entity_categories=", ".join(ALL_ENTITY_CATEGORIES)
)


def _parse_json_safely(text: str) -> List[Dict[str, Any]]:
    """Extract and parse JSON from LLM response, handling markdown blocks."""
    text = text.strip()
    # Try to extract from markdown code block
    code_block_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
    if code_block_match:
        text = code_block_match.group(1).strip()
    # Try to find a JSON array
    array_match = re.search(r'\[[\s\S]*\]', text)
    if array_match:
        text = array_match.group(0)
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return parsed
        if isinstance(parsed, dict) and "claims" in parsed:
            return parsed["claims"]
        if isinstance(parsed, dict) and "insights" in parsed:
            return parsed["insights"]
        return []
    except json.JSONDecodeError:
        print(f"[FACTS EXTRACT] JSON decode failed for: {text[:200]}")
        return []


def _extract_source_timestamp(item: Any, service: str) -> datetime:
    """Extract the best source timestamp from a raw data item."""
    ts_str = None
    if service == "google_calendar":
        start = item.get("start", {})
        ts_str = start.get("dateTime") or start.get("date")
    elif service == "gmail":
        ts_str = item.get("date")
    elif service == "google_drive":
        ts_str = item.get("modified_time")
    elif service == "apple_notes":
        ts_str = item.get("created") or item.get("modified")
    elif service == "apple_calendar":
        ts_str = item.get("start_date")
    elif service == "apple_music":
        # Apple Music items have no reliable creation date; skip fact extraction
        pass

    if ts_str:
        try:
            # Handle various ISO-like formats
            ts_str = str(ts_str).replace("Z", "+00:00")
            return datetime.fromisoformat(ts_str)
        except (ValueError, TypeError):
            pass

    return datetime.now()


def extract_facts_from_chunk(
    chunk_text: str,
    source_timestamp: datetime,
    chunk_id: str,
    user_id: str
) -> List[Dict[str, Any]]:
    """
    Extract factual claims from a single chunk using the LLM.
    Returns a list of claim dicts enriched with source metadata.
    """
    if not utils.llm:
        print("[FACTS EXTRACT] LLM not initialized, skipping fact extraction")
        return []

    if len(chunk_text.strip()) < 30:
        print("[FACTS EXTRACT] Chunk too short, skipping")
        return []

    try:
        user_prompt = (
            f"Document (written around {source_timestamp.strftime('%B %Y')}):\n\n"
            f"{chunk_text[:2000]}"
        )

        from langchain_core.messages import HumanMessage, SystemMessage
        messages = [
            SystemMessage(content=EXTRACTION_SYSTEM_PROMPT),
            HumanMessage(content=user_prompt),
        ]

        response = utils.llm.invoke(messages)
        claims = _parse_json_safely(response.content)

        # Validate and enrich claims
        results = []
        for claim in claims:
            if not isinstance(claim, dict):
                continue
            entity_key = claim.get("entity_key", "").strip().lower()
            entity_category = claim.get("entity_category", "").strip().lower()
            value = claim.get("value", "").strip()
            confidence = float(claim.get("confidence", 0))
            tense = claim.get("tense", "present").strip().lower()

            # Skip if key not in controlled vocabulary
            if entity_key not in [k.lower() for k in ALL_ENTITY_KEYS]:
                # Try to normalize
                matched_key = None
                for k in ALL_ENTITY_KEYS:
                    if k.lower() == entity_key:
                        matched_key = k
                        break
                if matched_key:
                    entity_key = matched_key
                else:
                    print(f"[FACTS EXTRACT] Skipping unknown entity_key: {entity_key}")
                    continue

            # Ensure category matches key
            expected_category = get_category_for_key(entity_key)
            if expected_category != "unknown" and entity_category != expected_category:
                entity_category = expected_category

            # Skip hypothetical and low-confidence
            if tense == "hypothetical":
                continue
            if confidence < 0.6:
                continue
            if not value or len(value) > 200:
                continue

            results.append({
                "user_id": user_id,
                "entity_key": entity_key,
                "entity_category": entity_category,
                "value": value,
                "confidence": confidence,
                "tense": tense,
                "source_chunk_id": chunk_id,
                "source_timestamp": source_timestamp.isoformat(),
            })

        print(f"[FACTS EXTRACT] Extracted {len(results)} facts from chunk {chunk_id}")
        return results

    except Exception as e:
        print(f"[FACTS EXTRACT] Error: {e}")
        import traceback
        traceback.print_exc()
        return []
