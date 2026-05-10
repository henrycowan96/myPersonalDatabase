"""
Scoring documents and insights by significance
"""

from datetime import datetime
from typing import Dict, List


class SignificanceScorer:
    """Scores documents and insights by significance"""
    
    def __init__(self):
        self.source_weights = {
            'google_calendar': 0.9,
            'apple_calendar': 0.9,
            'gmail': 0.8,
            'apple_notes': 0.7,
            'google_drive': 0.6,
            'apple_music': 0.4,
            'spotify': 0.4
        }
        
        self.type_weights = {
            'calendar_event': 0.9,
            'email': 0.8,
            'note': 0.7,
            'file': 0.6,
            'song': 0.3,
            'album': 0.3
        }
    
    def score_document(self, document: Dict, sentiment: Dict, events: List[Dict]) -> float:
        """Calculate significance score for a document"""
        score = 0.0
        
        # Source weight
        source = document.get('metadata', {}).get('source', 'unknown')
        score += self.source_weights.get(source, 0.5) * 0.3
        
        # Type weight
        doc_type = document.get('metadata', {}).get('type', 'unknown')
        score += self.type_weights.get(doc_type, 0.5) * 0.2
        
        # Recency score
        created_date = document.get('metadata', {}).get('created_date', '')
        if created_date:
            try:
                doc_date = datetime.fromisoformat(created_date.replace('Z', '+00:00'))
                days_old = (datetime.now(doc_date.tzinfo) - doc_date).days
                recency_score = max(0, 1 - (days_old / 365))  # Decay over a year
                score += recency_score * 0.2
            except:
                pass
        
        # Sentiment intensity
        sentiment_intensity = sentiment.get('intensity', 0)
        score += min(sentiment_intensity * 5, 1.0) * 0.15
        
        # Event presence
        if events:
            score += min(len(events) * 0.2, 1.0) * 0.15
        
        return min(score, 1.0)
