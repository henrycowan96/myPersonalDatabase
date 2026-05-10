"""
LLM-based classification of new claims against existing facts.
Determines whether a claim is: same, new_distinct, or supersedes.
"""

import json
import re
from typing import Dict, Any

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import utils


CLASSIFICATION_SYSTEM_PROMPT = """You compare two factual claims about the same person.

Given an existing claim and a new claim, classify their relationship as exactly one of:
- "same": same fact reconfirmed (same or very similar meaning)
- "new_distinct": genuinely different fact in same category, not a contradiction
- "supersedes": new claim directly updates or contradicts the old one

Also write a one-sentence detection_reason explaining the transition in plain English.
The new claim's source_timestamp determines which is more recent — newer ALWAYS wins.

Return JSON: {"relationship": "...", "detection_reason": "..."}"""


def _parse_classification_json(text: str) -> Dict[str, str]:
    """Parse LLM classification response."""
    text = text.strip()
    code_block_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
    if code_block_match:
        text = code_block_match.group(1).strip()
    obj_match = re.search(r'\{[\s\S]*\}', text)
    if obj_match:
        text = obj_match.group(0)
    try:
        parsed = json.loads(text)
        return {
            "relationship": parsed.get("relationship", "new_distinct"),
            "detection_reason": parsed.get("detection_reason", "Claim classified as distinct."),
        }
    except json.JSONDecodeError:
        print(f"[FACTS CLASSIFY] JSON decode failed for: {text[:200]}")
        # Fallback: keyword-based classification
        lower = text.lower()
        if "same" in lower and "reconfirm" in lower:
            return {"relationship": "same", "detection_reason": "Reconfirmed existing fact."}
        if "supersede" in lower or "update" in lower or "contradict" in lower:
            return {"relationship": "supersedes", "detection_reason": "New claim updates prior fact."}
        return {"relationship": "new_distinct", "detection_reason": "Distinct claim detected."}


def classify_claim_against_existing(
    new_claim: Dict[str, Any],
    existing_fact: Dict[str, Any]
) -> Dict[str, str]:
    """
    Classify relationship between a new claim and an existing fact.
    Returns {"relationship": "same|new_distinct|supersedes", "detection_reason": "..."}
    """
    if not utils.llm:
        print("[FACTS CLASSIFY] LLM not available, defaulting to new_distinct")
        return {"relationship": "new_distinct", "detection_reason": "LLM unavailable."}

    existing_ts = existing_fact.get("first_seen_at", "unknown")
    new_ts = new_claim.get("source_timestamp", "unknown")

    prompt = f"""Existing claim (from {existing_ts}):
entity_key: {existing_fact.get('entity_key', '')}
value: {existing_fact.get('value', '')}

New claim (from {new_ts}):
entity_key: {new_claim.get('entity_key', '')}
value: {new_claim.get('value', '')}"""

    try:
        from langchain_core.messages import HumanMessage, SystemMessage
        messages = [
            SystemMessage(content=CLASSIFICATION_SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ]
        response = utils.llm.invoke(messages)
        return _parse_classification_json(response.content)
    except Exception as e:
        print(f"[FACTS CLASSIFY] Error calling LLM: {e}")
        return {"relationship": "new_distinct", "detection_reason": "Classification failed."}
