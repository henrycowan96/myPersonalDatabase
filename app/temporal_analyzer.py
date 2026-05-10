"""
Temporal analysis of user data patterns
"""

from datetime import datetime, timedelta
from typing import List, Dict
from collections import defaultdict


class TemporalAnalyzer:
    """Analyzes temporal patterns in user data"""
    
    def __init__(self):
        pass
    
    def analyze_frequency(self, documents: List[Dict], time_window_days: int = 30) -> Dict[str, float]:
        """Analyze frequency of topics/entities over time"""
        now = datetime.now()
        cutoff = now - timedelta(days=time_window_days)
        
        entity_frequency = defaultdict(int)
        topic_frequency = defaultdict(int)
        
        for doc in documents:
            created_date = doc.get('metadata', {}).get('created_date', '')
            if created_date:
                try:
                    doc_date = datetime.fromisoformat(created_date.replace('Z', '+00:00'))
                    if doc_date >= cutoff:
                        entities = doc.get('metadata', {}).get('entity_ids', [])
                        for entity in entities:
                            entity_frequency[entity] += 1
                        
                        topics = doc.get('metadata', {}).get('topics', [])
                        for topic in topics:
                            topic_frequency[topic] += 1
                except:
                    pass
        
        return {
            'entities': dict(entity_frequency),
            'topics': dict(topic_frequency)
        }
    
    def detect_trends(self, frequency_data: Dict, threshold: float = 2.0) -> List[str]:
        """Detect trending topics/entities based on frequency"""
        trends = []
        
        for entity, count in frequency_data.get('entities', {}).items():
            if count >= threshold:
                trends.append(entity)
        
        for topic, count in frequency_data.get('topics', {}).items():
            if count >= threshold:
                trends.append(topic)
        
        return trends
