"""
Controlled vocabulary for the Personal Knowledge Graph.
This is the single source of truth for entity keys and categories.
The LLM extraction prompt includes this list verbatim.
"""

ENTITY_CATEGORIES = {
    "location": ["city", "country", "neighborhood", "workplace_location"],
    "work": ["employer", "job_title", "industry", "employment_status", "side_project"],
    "relationships": ["relationship_status", "close_friend", "family_dynamic"],
    "health": ["health_condition", "medication", "fitness_habit", "diet"],
    "finance": ["financial_situation", "major_expense", "savings_goal"],
    "identity": ["core_belief", "religion", "political_lean", "personality_trait"],
    "goals": ["current_goal", "completed_goal", "abandoned_goal"],
    "habits": ["daily_habit", "hobby", "sleep_pattern"],
}

# Flat lookup used in prompts
ALL_ENTITY_KEYS = [k for keys in ENTITY_CATEGORIES.values() for k in keys]
ALL_ENTITY_CATEGORIES = list(ENTITY_CATEGORIES.keys())

# Confidence thresholds before a candidate is promoted to a real fact.
# Higher for high-stakes identity claims, lower for soft patterns.
CONFIDENCE_THRESHOLDS = {
    "location": 0.80,
    "work": 0.85,
    "relationships": 0.85,
    "health": 0.80,
    "finance": 0.75,
    "identity": 0.90,
    "goals": 0.75,
    "habits": 0.70,
}

# How many corroborating chunks are needed before promotion
CONFIRMATION_THRESHOLDS = {
    "location": 2,
    "work": 2,
    "relationships": 3,
    "health": 2,
    "finance": 1,
    "identity": 3,
    "goals": 1,
    "habits": 2,
}


def get_category_for_key(entity_key: str) -> str:
    """Return the category for a given entity_key."""
    for category, keys in ENTITY_CATEGORIES.items():
        if entity_key in keys:
            return category
    return "unknown"


def is_valid_entity_key(entity_key: str) -> bool:
    """Check if an entity_key is in the controlled vocabulary."""
    return entity_key in ALL_ENTITY_KEYS
