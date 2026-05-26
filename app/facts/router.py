"""
Multi-tier fact extraction router for Apple Notes.
Routes Apple Notes documents to different extraction strategies based on size (number of chunks).
Customized for Apple Notes data source only.
"""

import asyncio
import json
import re
from datetime import datetime
from typing import List, Dict, Any
from enum import Enum
import time

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import utils
from facts.vocabulary import ALL_ENTITY_KEYS, ALL_ENTITY_CATEGORIES, get_category_for_key
from facts.extractor import EXTRACTION_SYSTEM_PROMPT, _parse_json_safely


class DocTier(Enum):
    TINY = "tiny"    # 1–5 chunks   → 1 call
    SMALL = "small"   # 6–15 chunks  → 2–3 calls parallel
    MEDIUM = "medium"  # 16–50 chunks → spine sample + gap scan
    LARGE = "large"   # 51+ chunks   → hierarchical summarize → extract


TIER_THRESHOLDS = {
    DocTier.TINY: (1, 5),
    DocTier.SMALL: (6, 15),
    DocTier.MEDIUM: (16, 50),
    DocTier.LARGE: (51, float("inf")),
}


async def _llm_call_with_retry(messages, max_retries=3, base_delay=2):
    """LLM call with exponential backoff for rate limit errors."""
    from langchain_openai import OpenAI
    
    for attempt in range(max_retries):
        try:
            response = utils.llm.invoke(messages)
            return response
        except Exception as e:
            error_str = str(e)
            is_rate_limit = "429" in error_str or "rate limit" in error_str.lower()
            
            if is_rate_limit and attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)  # Exponential backoff
                print(f"[FACTS ROUTER] Rate limit hit, retrying in {delay}s (attempt {attempt + 1}/{max_retries})")
                await asyncio.sleep(delay)
            else:
                raise  # Re-raise if not rate limit or max retries exceeded


def classify_doc(chunks: list) -> DocTier:
    """Classify a document by number of chunks."""
    n = len(chunks)
    for tier, (lo, hi) in TIER_THRESHOLDS.items():
        if lo <= n <= hi:
            return tier
    return DocTier.LARGE


# ── Entry point ──────────────────────────────────────────────────────────────

async def extract_facts_for_doc(
    chunks: List[Dict[str, Any]],
    doc_metadata: Dict[str, Any],
    user_id: str
) -> List[Dict[str, Any]]:
    """
    Route a document to the right extraction strategy based on size.
    
    Each chunk: {"text": str, "chunk_id": str, "source_timestamp": datetime}
    doc_metadata: {"doc_id": str, "source_type": str, "source_timestamp": datetime}
    """
    if not utils.llm:
        print("[FACTS ROUTER] LLM not initialized, skipping fact extraction")
        return []

    tier = classify_doc(chunks)
    print(f"[FACTS ROUTER] Document classified as {tier.value} ({len(chunks)} chunks)")
    
    handlers = {
        DocTier.TINY: _extract_tiny,
        DocTier.SMALL: _extract_small,
        DocTier.MEDIUM: _extract_medium,
        DocTier.LARGE: _extract_large,
    }
    
    facts = await handlers[tier](chunks, doc_metadata, user_id)
    
    # Tag every fact with doc-level metadata before returning
    for f in facts:
        f.setdefault("doc_id", doc_metadata.get("doc_id"))
        f.setdefault("source_type", doc_metadata.get("source_type"))
        f.setdefault("source_timestamp", doc_metadata.get("source_timestamp"))
    
    print(f"[FACTS ROUTER] Extracted {len(facts)} total facts (tier: {tier.value})")
    return facts


# ── Tier 1: Tiny (1–5 chunks) ─────────────────────────────────────────────
# All chunks fit in one prompt. One LLM call.

async def _extract_tiny(
    chunks: List[Dict[str, Any]], 
    meta: Dict[str, Any],
    user_id: str
) -> List[Dict[str, Any]]:
    combined = _format_chunks_for_prompt(chunks)
    return await _extraction_call(combined, meta["source_timestamp"], user_id)


# ── Tier 2: Small (6–15 chunks) ──────────────────────────────────────────
# Split into batches of 5, run all in parallel.

async def _extract_small(
    chunks: List[Dict[str, Any]], 
    meta: Dict[str, Any],
    user_id: str
) -> List[Dict[str, Any]]:
    batches = _batch(chunks, size=3)  # Reduced from 5 to 3 to avoid rate limits
    results = await asyncio.gather(*[
        _extraction_call(_format_chunks_for_prompt(b), meta["source_timestamp"], user_id)
        for b in batches
    ])
    return _deduplicate(_flatten(results))


# ── Tier 3: Medium (16–50 chunks) ────────────────────────────────────────
# Two-pass strategy:
#   Pass 1: Extract from a representative spine (every Nth chunk)
#   Pass 2: Scan skipped chunks only for entity keys NOT found in pass 1

async def _extract_medium(
    chunks: List[Dict[str, Any]], 
    meta: Dict[str, Any],
    user_id: str
) -> List[Dict[str, Any]]:
    n = len(chunks)
    step = max(2, n // 8)  # sample ~8 representative chunks
    
    spine_indices = set(range(0, n, step))
    spine_indices.add(0)
    spine_indices.add(n - 1)  # always include first and last
    spine = [chunks[i] for i in sorted(spine_indices)]
    skipped = [c for i, c in enumerate(chunks) if i not in spine_indices]
    
    print(f"[FACTS ROUTER] MEDIUM tier: spine={len(spine)} chunks, skipped={len(skipped)} chunks")
    
    # Pass 1: full extraction on spine (parallel batches of 3)
    spine_batches = _batch(spine, size=3)  # Reduced from 5 to 3 to avoid rate limits
    spine_results = await asyncio.gather(*[
        _extraction_call(_format_chunks_for_prompt(b), meta["source_timestamp"], user_id)
        for b in spine_batches
    ])
    spine_facts = _deduplicate(_flatten(spine_results))
    found_keys = {f["entity_key"] for f in spine_facts}
    
    print(f"[FACTS ROUTER] Spine found {len(found_keys)} unique entity keys")
    
    if not skipped:
        return spine_facts
    
    # Pass 2: targeted gap scan — only look for keys we haven't found yet
    missing_keys = set(ALL_ENTITY_KEYS) - found_keys
    if not missing_keys:
        print(f"[FACTS ROUTER] Spine found all entity keys, skipping gap scan")
        return spine_facts
    
    print(f"[FACTS ROUTER] Gap scanning for {len(missing_keys)} missing keys")
    gap_batches = _batch(skipped, size=3)  # Reduced from 5 to 3 to avoid rate limits
    gap_results = await asyncio.gather(*[
        _gap_scan_call(
            _format_chunks_for_prompt(b),
            meta["source_timestamp"],
            user_id,
            missing_keys
        )
        for b in gap_batches
    ])
    gap_facts = _deduplicate(_flatten(gap_results))
    
    return _deduplicate(spine_facts + gap_facts)


# ── Tier 4: Large (51+ chunks) ───────────────────────────────────────────
# Three-pass hierarchical strategy:
#   Pass 1: Summarize the document into a ~400-word factual portrait
#   Pass 2: Extract facts from the summary (1 call, very fast)
#   Pass 3: Light gap scan on skipped chunks for any keys not in the summary

async def _extract_large(
    chunks: List[Dict[str, Any]], 
    meta: Dict[str, Any],
    user_id: str
) -> List[Dict[str, Any]]:
    n = len(chunks)
    
    # Build a spine: first chunk, last chunk, every ~10th in between
    step = max(3, n // 10)
    spine_indices = set(range(0, n, step))
    spine_indices.update([0, n - 1])
    spine = [chunks[i] for i in sorted(spine_indices)]
    skipped = [c for i, c in enumerate(chunks) if i not in spine_indices]
    
    print(f"[FACTS ROUTER] LARGE tier: spine={len(spine)} chunks, skipped={len(skipped)} chunks")
    
    # Pass 1: summarize spine into a factual portrait
    spine_text = "\n\n---\n\n".join(
        f"[Excerpt {i+1}]:\n{c['text']}" for i, c in enumerate(spine)
    )
    summary = await _summarize_call(spine_text, meta["source_timestamp"], len(chunks))
    
    # Pass 2: extract facts from the summary
    summary_facts = await _extraction_call(summary, meta["source_timestamp"], user_id)
    found_keys = {f["entity_key"] for f in summary_facts}
    
    print(f"[FACTS ROUTER] Summary found {len(found_keys)} unique entity keys")
    
    if not skipped:
        return summary_facts
    
    # Pass 3: gap scan on skipped chunks for anything the summary missed
    missing_keys = set(ALL_ENTITY_KEYS) - found_keys
    if not missing_keys:
        print(f"[FACTS ROUTER] Summary found all entity keys, skipping gap scan")
        return summary_facts
    
    # Don't scan ALL skipped chunks — sample them too
    gap_sample_step = max(1, len(skipped) // 6)
    gap_sample = skipped[::gap_sample_step]
    
    print(f"[FACTS ROUTER] Gap scanning {len(gap_sample)} of {len(skipped)} skipped chunks for {len(missing_keys)} missing keys")
    gap_batches = _batch(gap_sample, size=3)  # Reduced from 5 to 3 to avoid rate limits
    gap_results = await asyncio.gather(*[
        _gap_scan_call(
            _format_chunks_for_prompt(b),
            meta["source_timestamp"],
            user_id,
            missing_keys
        )
        for b in gap_batches
    ])
    gap_facts = _deduplicate(_flatten(gap_results))
    
    return _deduplicate(summary_facts + gap_facts)


# ── LLM call wrappers ────────────────────────────────────────────────────

SUMMARY_SYSTEM_PROMPT = """Summarize this Apple Note into a factual portrait of the author.
Focus only on persistent states: where they live, what they do for work, relationships,
health, finances, goals, beliefs, habits. Ignore specific events, meetings, or one-off occurrences.
Focus on personal reflections, goals, and self-documentation typical of Apple Notes.
Write in third person. Max 400 words. Be specific — prefer "works at Google as a PM" over "works in tech"."""

async def _summarize_call(spine_text: str, source_ts: datetime, total_chunks: int) -> str:
    """Generate a factual summary of the Apple Note from spine chunks."""
    from langchain_core.messages import HumanMessage, SystemMessage
    
    user_prompt = (
        f"Apple Note written around {source_ts.strftime('%B %Y')}. "
        f"{total_chunks} pages total.\n\n{spine_text}"
    )
    
    messages = [
        SystemMessage(content=SUMMARY_SYSTEM_PROMPT),
        HumanMessage(content=user_prompt),
    ]
    
    response = await _llm_call_with_retry(messages)
    return response.content


async def _extraction_call(
    text: str, 
    source_ts: datetime,
    user_id: str
) -> List[Dict[str, Any]]:
    """Extract facts from Apple Notes text using the standard extraction prompt."""
    from langchain_core.messages import HumanMessage, SystemMessage
    
    # Increase text limit from 2000 to 3000 chars to capture more context
    text_to_send = text[:3000]
    print(f"[FACTS ROUTER] Sending {len(text_to_send)} chars to LLM for extraction")
    
    user_prompt = (
        f"Apple Note content from around {source_ts.strftime('%B %Y')}:\n\n"
        f"{text_to_send}"
    )
    
    messages = [
        SystemMessage(content=EXTRACTION_SYSTEM_PROMPT),
        HumanMessage(content=user_prompt),
    ]
    
    response = await _llm_call_with_retry(messages)
    print(f"[FACTS ROUTER] LLM response length: {len(response.content)}")
    print(f"[FACTS ROUTER] LLM response content: {response.content[:200]}")
    
    claims = _parse_json_safely(response.content)
    print(f"[FACTS ROUTER] Parsed {len(claims)} claims from LLM response")
    
    # Enrich claims with metadata
    results = []
    skipped_hypothetical = 0
    skipped_low_confidence = 0
    skipped_invalid_value = 0
    skipped_unknown_key = 0
    
    for claim in claims:
        if not isinstance(claim, dict):
            continue
        entity_key = claim.get("entity_key", "").strip().lower()
        entity_category = claim.get("entity_category", "").strip().lower()
        value = claim.get("value", "").strip()
        confidence = float(claim.get("confidence", 0))
        tense = claim.get("tense", "present").strip().lower()

        # Normalize entity key
        if entity_key not in [k.lower() for k in ALL_ENTITY_KEYS]:
            matched_key = None
            for k in ALL_ENTITY_KEYS:
                if k.lower() == entity_key:
                    matched_key = k
                    break
            if matched_key:
                entity_key = matched_key
            else:
                skipped_unknown_key += 1
                continue

        # Ensure category matches key
        expected_category = get_category_for_key(entity_key)
        if expected_category != "unknown" and entity_category != expected_category:
            entity_category = expected_category

        # Skip hypothetical and low-confidence
        if tense == "hypothetical":
            skipped_hypothetical += 1
            continue
        if confidence < 0.6:
            skipped_low_confidence += 1
            continue
        if not value or len(value) > 200:
            skipped_invalid_value += 1
            continue

        results.append({
            "user_id": user_id,
            "entity_key": entity_key,
            "entity_category": entity_category,
            "value": value,
            "confidence": confidence,
            "tense": tense,
            "source_timestamp": source_ts.isoformat(),
        })
    
    if skipped_hypothetical > 0 or skipped_low_confidence > 0 or skipped_invalid_value > 0 or skipped_unknown_key > 0:
        print(f"[FACTS ROUTER] Skipped: {skipped_hypothetical} hypothetical, {skipped_low_confidence} low confidence, {skipped_invalid_value} invalid value, {skipped_unknown_key} unknown key")
    print(f"[FACTS ROUTER] Returning {len(results)} valid facts")
    
    return results


async def _gap_scan_call(
    text: str, 
    source_ts: datetime,
    user_id: str,
    target_keys: set
) -> List[Dict[str, Any]]:
    """Like extraction but constrained to only the missing entity keys from Apple Notes."""
    from langchain_core.messages import HumanMessage, SystemMessage
    
    keys_list = ", ".join(sorted(target_keys))
    
    user_prompt = (
        f"Apple Note content from around {source_ts.strftime('%B %Y')}.\n"
        f"Only extract facts for these specific entity keys: {keys_list}\n"
        f"Return [] if none found.\n\n{text[:3000]}"  # Increased from 2000 to 3000
    )
    
    messages = [
        SystemMessage(content=EXTRACTION_SYSTEM_PROMPT),
        HumanMessage(content=user_prompt),
    ]
    
    response = await _llm_call_with_retry(messages)
    print(f"[FACTS ROUTER] Gap scan LLM response length: {len(response.content)}")
    print(f"[FACTS ROUTER] Gap scan LLM response content: {response.content[:200]}")
    
    claims = _parse_json_safely(response.content)
    print(f"[FACTS ROUTER] Gap scan parsed {len(claims)} claims")
    
    # Enrich claims with metadata (same as _extraction_call)
    results = []
    for claim in claims:
        if not isinstance(claim, dict):
            continue
        entity_key = claim.get("entity_key", "").strip().lower()
        entity_category = claim.get("entity_category", "").strip().lower()
        value = claim.get("value", "").strip()
        confidence = float(claim.get("confidence", 0))
        tense = claim.get("tense", "present").strip().lower()

        # Normalize entity key
        if entity_key not in [k.lower() for k in ALL_ENTITY_KEYS]:
            matched_key = None
            for k in ALL_ENTITY_KEYS:
                if k.lower() == entity_key:
                    matched_key = k
                    break
            if matched_key:
                entity_key = matched_key
            else:
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
            "source_timestamp": source_ts.isoformat(),
        })
    
    return results


# ── Helpers ──────────────────────────────────────────────────────────────

def _batch(items: list, size: int) -> list[list]:
    """Split items into batches of given size."""
    return [items[i:i+size] for i in range(0, len(items), size)]

def _flatten(nested: list[list]) -> list:
    """Flatten a nested list."""
    return [item for sublist in nested for item in sublist]

def _format_chunks_for_prompt(chunks: List[Dict[str, Any]]) -> str:
    """Format chunks for LLM prompt."""
    if len(chunks) == 1:
        return chunks[0]["text"]
    return "\n\n---\n\n".join(
        f"[Doc {i+1}]:\n{c['text']}" for i, c in enumerate(chunks)
    )

def _deduplicate(facts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Remove near-duplicate facts with the same entity_key and similar value."""
    seen = {}
    for f in facts:
        key = f["entity_key"]
        if key not in seen:
            seen[key] = f
        else:
            # Keep the higher-confidence version
            if f.get("confidence", 0) > seen[key].get("confidence", 0):
                seen[key] = f
    return list(seen.values())
