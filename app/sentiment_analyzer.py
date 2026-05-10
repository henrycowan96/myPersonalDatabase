"""
Sentiment analysis for text documents
"""

from typing import Dict


class SentimentAnalyzer:
    """Simple sentiment analysis for text"""
    
    def __init__(self):
        # Simple word-based sentiment lexicon
        self.positive_words = {
            'happy', 'great', 'excellent', 'amazing', 'wonderful', 'fantastic',
            'love', 'excited', 'thrilled', 'delighted', 'pleased', 'satisfied',
            'success', 'achieved', 'accomplished', 'won', 'celebration',
            'promoted', 'hired', 'offer', 'accepted', 'congratulations',
            'birthday', 'anniversary', 'wedding', 'graduation', 'milestone'
        }
        
        self.negative_words = {
            'sad', 'unhappy', 'disappointed', 'frustrated', 'angry', 'upset',
            'worried', 'anxious', 'stressed', 'overwhelmed', 'exhausted',
            'failed', 'rejected', 'denied', 'lost', 'cancelled', 'delayed',
            'sick', 'ill', 'hospital', 'doctor', 'medical', 'emergency',
            'fired', 'laid off', 'quit', 'resigned', 'left', 'departure'
        }
        
        self.urgent_words = {
            'urgent', 'asap', 'immediately', 'deadline', 'due', 'overdue',
            'emergency', 'critical', 'important', 'priority', 'required',
            'meeting', 'appointment', 'call', 'interview', 'deadline'
        }
    
    def analyze(self, text: str) -> Dict[str, float]:
        """Analyze sentiment of text"""
        text_lower = text.lower()
        words = set(text_lower.split())
        
        positive_count = len(words & self.positive_words)
        negative_count = len(words & self.negative_words)
        urgent_count = len(words & self.urgent_words)
        
        total_sentiment_words = positive_count + negative_count
        if total_sentiment_words == 0:
            sentiment = 0.0
        else:
            sentiment = (positive_count - negative_count) / total_sentiment_words
        
        return {
            'sentiment': sentiment,  # -1 to 1
            'positive': positive_count,
            'negative': negative_count,
            'urgent': urgent_count,
            'intensity': total_sentiment_words / len(words) if words else 0
        }
