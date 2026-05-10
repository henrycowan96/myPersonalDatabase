"""
Data models for the insights engine
"""

from dataclasses import dataclass
from typing import List, Dict


@dataclass
class Insight:
    """Represents a single insight about the user's life"""
    id: str
    category: str  # 'urgent', 'important', 'interesting', 'trending', 'milestone'
    title: str
    description: str
    significance_score: float
    sources: List[Dict]
    detected_at: str
    time_context: Dict
    entities: List[str]
    actionable: bool = False
