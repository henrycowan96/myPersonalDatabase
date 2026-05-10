"""
Detection of significant life events from documents
"""

import re
from typing import List, Dict


class LifeEventDetector:
    """Detects significant life events from documents"""
    
    def __init__(self):
        # Expanded career patterns
        self.career_patterns = [
            (r'\b(?:promoted|promotion|raise|salary increase|new role|new position|advancement|career growth)\b', 'career_promotion'),
            (r'\b(?:hired|offer|accepted|joined|started.*job|new job|employment|onboarding)\b', 'career_new_job'),
            (r'\b(?:fired|laid off|terminated|let go|resigned|quit|left.*job|departure|unemployment)\b', 'career_job_loss'),
            (r'\b(?:interview|screening|technical|offer call|recruiter|headhunter|application)\b', 'career_interview'),
            (r'\b(?:project|launch|release|deadline|presentation|meeting|conference|training|certification)\b', 'career_work'),
            (r'\b(?:client|customer|contract|freelance|consulting|business|startup|entrepreneur)\b', 'career_business'),
        ]
        
        # Expanded location patterns
        self.location_patterns = [
            (r'\b(?:moved|relocated|moving|new address|change of address|packing|unpacking)\b', 'location_move'),
            (r'\b(?:apartment|house|rent|lease|mortgage|property|real estate|home|neighborhood)\b', 'location_housing'),
            (r'\b(?:travel|trip|vacation|flight|hotel|airbnb|booking|destination)\b', 'location_travel'),
            (r'\b(?:city|state|country|abroad|international|domestic)\b', 'location_geographic'),
        ]
        
        # Expanded relationship patterns
        self.relationship_patterns = [
            (r'\b(?:married|wedding|engagement|fianc[ée]|marriage|proposal)\b', 'relationship_milestone'),
            (r'\b(?:dating|relationship|boyfriend|girlfriend|partner|romance|love)\b', 'relationship_dating'),
            (r'\b(?:breakup|broke up|split|separated|divorce|break|ended)\b', 'relationship_end'),
            (r'\b(?:family|parent|child|sibling|relative|mom|dad|brother|sister)\b', 'relationship_family'),
            (r'\b(?:friend|friendship|social|meetup|gathering|party)\b', 'relationship_social'),
        ]
        
        # Expanded health patterns
        self.health_patterns = [
            (r'\b(?:doctor|hospital|medical|appointment|checkup|surgery|treatment|clinic)\b', 'health_medical'),
            (r'\b(?:sick|ill|diagnosis|condition|symptom|pain|injury|accident)\b', 'health_condition'),
            (r'\b(?:exercise|workout|gym|fitness|diet|nutrition|weight|health|wellness)\b', 'health_wellness'),
            (r'\b(?:mental|therapy|counseling|stress|anxiety|depression|meditation)\b', 'health_mental'),
        ]
        
        # Expanded financial patterns
        self.financial_patterns = [
            (r'\b(?:purchase|bought|paid|investment|stock|portfolio|trading|market)\b', 'financial_transaction'),
            (r'\b(?:loan|debt|credit|mortgage|payment|bank|account|finance)\b', 'financial_debt'),
            (r'\b(?:income|salary|wage|bonus|commission|raise|promotion|pay)\b', 'financial_income'),
            (r'\b(?:budget|saving|expense|cost|price|value|worth|afford)\b', 'financial_planning'),
        ]
        
        # Expanded milestone patterns
        self.milestone_patterns = [
            (r'\b(?:birthday|anniversary|graduation|graduated|degree|diploma)\b', 'milestone_celebration'),
            (r'\b(?:achievement|award|recognition|certificate|trophy|medal|honor)\b', 'milestone_achievement'),
            (r'\b(?:success|accomplish|complete|finish|goal|target|objective)\b', 'milestone_success'),
            (r'\b(?:begin|start|launch|initiate|commence|embark)\b', 'milestone_beginning'),
        ]
        
        # Expanded personal development patterns
        self.personal_patterns = [
            (r'\b(?:learn|study|course|education|school|university|college|class)\b', 'personal_learning'),
            (r'\b(?:skill|ability|talent|expertise|master|improve|develop)\b', 'personal_skill'),
            (r'\b(?:hobby|interest|passion|creative|art|music|writing|reading)\b', 'personal_hobby'),
            (r'\b(?:decision|choice|plan|strategy|resolution|commitment)\b', 'personal_decision'),
        ]
        
        # Emotion and sentiment patterns
        self.emotion_patterns = [
            (r'\b(?:happy|excited|thrilled|joy|celebrate|proud|satisfied)\b', 'emotion_positive'),
            (r'\b(?:sad|angry|frustrated|disappointed|worried|stressed|overwhelmed)\b', 'emotion_negative'),
            (r'\b(?:grateful|thankful|appreciate|blessed|fortunate)\b', 'emotion_gratitude'),
            (r'\b(?:hopeful|optimistic|confident|motivated|inspired)\b', 'emotion_motivation'),
        ]
    
    def detect_events(self, text: str, metadata: Dict) -> List[Dict]:
        """Detect life events from text"""
        events = []
        text_lower = text.lower()
        
        all_patterns = [
            *self.career_patterns,
            *self.location_patterns,
            *self.relationship_patterns,
            *self.health_patterns,
            *self.financial_patterns,
            *self.milestone_patterns,
            *self.personal_patterns,
            *self.emotion_patterns
        ]
        
        for pattern, event_type in all_patterns:
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            if matches:
                events.append({
                    'type': event_type,
                    'matches': matches,
                    'count': len(matches)
                })
        
        return events
