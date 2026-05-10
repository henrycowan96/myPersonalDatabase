"""
Orchestrates the full fact processing pipeline:
1. Vector search among existing facts
2. Timestamp-based conflict resolution
3. LLM classification
4. Promotion / staging / supersession
"""

import numpy as np
from datetime import datetime
from typing import Dict, Any, List, Optional

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import utils
from facts.vocabulary import (
    CONFIDENCE_THRESHOLDS,
    CONFIRMATION_THRESHOLDS,
    get_category_for_key,
)
from facts.classifier import classify_claim_against_existing


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    a_vec = np.array(a, dtype=np.float32)
    b_vec = np.array(b, dtype=np.float32)
    norm = np.linalg.norm(a_vec) * np.linalg.norm(b_vec)
    if norm == 0:
        return 0.0
    return float(np.dot(a_vec, b_vec) / norm)


def _parse_timestamp(ts: Any) -> datetime:
    if isinstance(ts, datetime):
        return ts
    if isinstance(ts, str):
        ts = ts.replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(ts)
        except ValueError:
            pass
    return datetime.now()


def _vector_search_facts(claim_text: str, user_id: str, entity_category: str, top_k: int = 3) -> List[Dict[str, Any]]:
    """Brute-force similarity search among current facts for a user."""
    if not utils.embedding_model:
        return []

    try:
        result = utils.supabase.table("facts").select("*").eq("user_id", user_id).eq("is_current", True).execute()
        facts = result.data or []
    except Exception as e:
        print(f"[FACTS PIPELINE] Error fetching facts: {e}")
        return []

    if not facts:
        return []

    claim_emb = utils.embedding_model.encode(claim_text).tolist()

    scored = []
    for fact in facts:
        if fact.get("entity_category") != entity_category:
            continue
        fact_text = f"{fact.get('entity_key', '')}: {fact.get('value', '')}"
        fact_emb = utils.embedding_model.encode(fact_text).tolist()
        sim = _cosine_similarity(claim_emb, fact_emb)
        scored.append((sim, fact))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [fact for _, fact in scored[:top_k]]


def _upsert_candidate(claim: Dict[str, Any]) -> None:
    """Stage a claim as a candidate fact, incrementing confirmation count if it already exists."""
    if not utils.supabase:
        return

    try:
        # Check for existing candidate with same user_id, entity_key, and value
        existing = utils.supabase.table("candidate_facts").select("*").eq("user_id", claim["user_id"]).eq("entity_key", claim["entity_key"]).eq("value", claim["value"]).execute()

        if existing.data:
            cand = existing.data[0]
            new_count = cand.get("confirmation_count", 1) + 1
            new_chunk_ids = list(cand.get("source_chunk_ids", []))
            if claim.get("source_chunk_id") and claim["source_chunk_id"] not in new_chunk_ids:
                new_chunk_ids.append(claim["source_chunk_id"])

            # Update confirmation count and timestamp
            utils.supabase.table("candidate_facts").update({
                "confirmation_count": new_count,
                "source_timestamp": claim["source_timestamp"],
                "source_chunk_ids": new_chunk_ids,
                "confidence": max(cand.get("confidence", 0), claim.get("confidence", 0)),
            }).eq("id", cand["id"]).execute()
            print(f"[FACTS PIPELINE] Incremented candidate {cand['id']} to count {new_count}")
        else:
            # Insert new candidate
            record = {
                "user_id": claim["user_id"],
                "entity_key": claim["entity_key"],
                "entity_category": claim["entity_category"],
                "value": claim["value"],
                "confidence": claim["confidence"],
                "tense": claim.get("tense", "present"),
                "source_timestamp": claim["source_timestamp"],
                "source_chunk_ids": [claim.get("source_chunk_id", "")] if claim.get("source_chunk_id") else [],
                "confirmation_count": 1,
            }
            utils.supabase.table("candidate_facts").insert(record).execute()
            print(f"[FACTS PIPELINE] Created new candidate for {claim['entity_key']}")
    except Exception as e:
        print(f"[FACTS PIPELINE] Error upserting candidate: {e}")
        import traceback
        traceback.print_exc()


def _insert_fact(claim: Dict[str, Any]) -> Optional[str]:
    """Insert a new fact and return its ID."""
    if not utils.supabase:
        return None

    try:
        record = {
            "user_id": claim["user_id"],
            "entity_key": claim["entity_key"],
            "entity_category": claim["entity_category"],
            "value": claim["value"],
            "confidence": claim["confidence"],
            "tense": claim.get("tense", "present"),
            "first_seen_at": claim["source_timestamp"],
            "last_confirmed_at": claim["source_timestamp"],
            "is_current": True,
            "source_chunk_ids": [claim.get("source_chunk_id", "")] if claim.get("source_chunk_id") else [],
        }
        result = utils.supabase.table("facts").insert(record).execute()
        if result.data:
            return result.data[0]["id"]
    except Exception as e:
        print(f"[FACTS PIPELINE] Error inserting fact: {e}")
        import traceback
        traceback.print_exc()
    return None


def _check_reversion(user_id: str, entity_key: str, new_value: str) -> bool:
    """Check if this value has appeared before in the fact history."""
    if not utils.supabase:
        return False
    try:
        result = utils.supabase.table("fact_changes").select("id").eq("user_id", user_id).eq("entity_key", entity_key).eq("new_value", new_value).order("source_timestamp", desc=True).limit(1).execute()
        return len(result.data) > 0
    except Exception as e:
        print(f"[FACTS PIPELINE] Error checking reversion: {e}")
        return False


def process_extracted_claim(claim: Dict[str, Any]) -> None:
    """
    Main pipeline entry point for a single extracted claim.
    Decides whether to stage, confirm, or supersede.
    """
    if not utils.supabase:
        print("[FACTS PIPELINE] Supabase not available, skipping claim processing")
        return

    user_id = claim["user_id"]
    source_ts = _parse_timestamp(claim["source_timestamp"])
    entity_category = claim.get("entity_category", get_category_for_key(claim.get("entity_key", "")))
    claim["entity_category"] = entity_category  # normalize

    # 1. Vector search existing facts in same category
    claim_text = f"{claim['entity_key']}: {claim['value']}"
    similar_facts = _vector_search_facts(claim_text, user_id, entity_category, top_k=3)

    # 2. No similar fact exists — stage as candidate
    if not similar_facts:
        _upsert_candidate(claim)
        return

    best_match = similar_facts[0]
    best_match_ts = _parse_timestamp(best_match.get("last_confirmed_at", best_match.get("first_seen_at", datetime.now().isoformat())))

    # 3. Skip if existing fact is newer than this claim's source
    if best_match_ts > source_ts:
        print(f"[FACTS PIPELINE] Existing fact is newer ({best_match_ts}) than claim source ({source_ts}), skipping")
        return

    # 4. Classify the relationship via LLM
    classification = classify_claim_against_existing(claim, best_match)
    relationship = classification.get("relationship", "new_distinct")
    detection_reason = classification.get("detection_reason", "")

    print(f"[FACTS PIPELINE] Classification: {relationship} — {detection_reason}")

    if relationship == "same":
        # Refresh confirmation timestamp and append chunk ID
        try:
            new_confirmed = max(best_match_ts, source_ts).isoformat()
            chunk_ids = list(best_match.get("source_chunk_ids", []))
            if claim.get("source_chunk_id") and claim["source_chunk_id"] not in chunk_ids:
                chunk_ids.append(claim["source_chunk_id"])
            utils.supabase.table("facts").update({
                "last_confirmed_at": new_confirmed,
                "source_chunk_ids": chunk_ids,
            }).eq("id", best_match["id"]).execute()
            print(f"[FACTS PIPELINE] Refreshed fact {best_match['id']}")
        except Exception as e:
            print(f"[FACTS PIPELINE] Error refreshing fact: {e}")

    elif relationship == "new_distinct":
        _upsert_candidate(claim)

    elif relationship == "supersedes":
        category = claim["entity_category"]
        threshold_conf = CONFIDENCE_THRESHOLDS.get(category, 0.75)
        threshold_conf_count = CONFIRMATION_THRESHOLDS.get(category, 1)

        if claim["confidence"] < threshold_conf:
            print(f"[FACTS PIPELINE] Confidence {claim['confidence']} below threshold {threshold_conf}, staging as candidate")
            _upsert_candidate(claim)
            return

        # Check if this is a reversion to a prior value
        is_reversion = _check_reversion(user_id, claim["entity_key"], claim["value"])
        if is_reversion:
            print(f"[FACTS PIPELINE] Detected reversion for {claim['entity_key']} back to '{claim['value']}'")

        # Supersede old fact
        try:
            utils.supabase.table("facts").update({
                "is_current": False,
                "superseded_at": claim["source_timestamp"],
            }).eq("id", best_match["id"]).execute()
            print(f"[FACTS PIPELINE] Superseded fact {best_match['id']}")
        except Exception as e:
            print(f"[FACTS PIPELINE] Error superseding fact: {e}")
            return

        # Insert new fact
        new_fact_id = _insert_fact(claim)
        if not new_fact_id:
            print("[FACTS PIPELINE] Failed to insert new fact, aborting supersession")
            return

        # Write the change event
        try:
            change_record = {
                "user_id": user_id,
                "old_fact_id": best_match["id"],
                "new_fact_id": new_fact_id,
                "entity_key": claim["entity_key"],
                "entity_category": claim["entity_category"],
                "old_value": best_match.get("value"),
                "new_value": claim["value"],
                "detected_at": datetime.now().isoformat(),
                "source_timestamp": claim["source_timestamp"],
                "confidence": claim["confidence"],
                "detection_reason": detection_reason,
                "is_reversion": is_reversion,
            }
            utils.supabase.table("fact_changes").insert(change_record).execute()
            print(f"[FACTS PIPELINE] Recorded fact change: '{best_match.get('value')}' -> '{claim['value']}'")
        except Exception as e:
            print(f"[FACTS PIPELINE] Error recording fact change: {e}")
            import traceback
            traceback.print_exc()


async def promote_confirmed_candidates(user_id: str) -> int:
    """
    Background job: promote candidates that have hit their confirmation threshold.
    Returns the number of candidates promoted.
    """
    if not utils.supabase:
        return 0

    try:
        result = utils.supabase.table("candidate_facts").select("*").eq("user_id", user_id).execute()
        candidates = result.data or []
    except Exception as e:
        print(f"[FACTS PROMOTE] Error fetching candidates: {e}")
        return 0

    promoted = 0
    for c in candidates:
        cat = c.get("entity_category", "")
        threshold = CONFIRMATION_THRESHOLDS.get(cat, 1)
        if c.get("confirmation_count", 0) >= threshold:
            try:
                claim = {
                    "user_id": c["user_id"],
                    "entity_key": c["entity_key"],
                    "entity_category": c["entity_category"],
                    "value": c["value"],
                    "confidence": c["confidence"],
                    "tense": c.get("tense", "present"),
                    "source_chunk_id": c.get("source_chunk_ids", [None])[0] if c.get("source_chunk_ids") else None,
                    "source_timestamp": c["source_timestamp"],
                }
                process_extracted_claim(claim)
                utils.supabase.table("candidate_facts").delete().eq("id", c["id"]).execute()
                promoted += 1
            except Exception as e:
                print(f"[FACTS PROMOTE] Error promoting candidate {c['id']}: {e}")

    print(f"[FACTS PROMOTE] Promoted {promoted}/{len(candidates)} candidates for user {user_id}")
    return promoted
