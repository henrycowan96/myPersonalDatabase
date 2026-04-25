"""
Entity extraction module for identifying people, companies, projects, and topics
from text documents to enable relationship tracking.
"""

import re
from typing import List, Dict, Set
from collections import Counter


class EntityExtractor:
    """Extract entities from text for relationship tracking"""
    
    def __init__(self):
        # Common company name patterns (can be extended)
        self.company_patterns = [
            r'\b[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*(?:\s+(?:Inc|Corp|LLC|Ltd|Co|Company|Technologies|Systems|Solutions))\b',
            r'\b(?:Apple|Google|Microsoft|Amazon|Meta|NVIDIA|AMD|Intel|Tesla|SpaceX|OpenAI|Anthropic|Palantir|CoreWeave|Adyen)\b'
        ]
        
        # Person name patterns (capitalized words, 2-3 words)
        self.person_patterns = [
            r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b',  # First Last
            r'\b[A-Z][a-z]+\s+[A-Z]\.\s+[A-Z][a-z]+\b',  # First M. Last
        ]
        
        # Topic/keyword patterns for categorization
        self.topic_keywords = {
            'investment': ['investment', 'stock', 'etf', 'portfolio', 'bullish', 'bearish', 'dividend', 'trading'],
            'ai_ml': ['ai', 'artificial intelligence', 'machine learning', 'neural network', 'llm', 'gpt', 'transformer'],
            'crypto': ['bitcoin', 'ethereum', 'cryptocurrency', 'blockchain', 'nft', 'defi'],
            'career': ['resume', 'interview', 'job', 'career', 'internship', 'offer', 'salary'],
            'education': ['school', 'university', 'college', 'class', 'exam', 'homework', 'assignment', 'degree'],
            'finance': ['finance', 'financial', 'revenue', 'earnings', 'profit', 'debt', 'loan'],
            'technology': ['software', 'hardware', 'chip', 'gpu', 'cpu', 'data center', 'cloud'],
            'energy': ['energy', 'oil', 'gas', 'nuclear', 'renewable', 'solar', 'wind', 'uranium'],
            'healthcare': ['medical', 'health', 'cancer', 'treatment', 'therapy', 'fda', 'drug'],
            'music': ['song', 'album', 'artist', 'band', 'music', 'playlist', 'track', 'genre', 'concert', 'vinyl', 'spotify', 'apple music'],
        }
        
        # Project/task patterns
        self.project_patterns = [
            r'\b(?:Project|Task)\s+[A-Z][a-zA-Z]+\b',
            r'\b[A-Z][a-zA-Z]+\s+(?:Project|Initiative|Program)\b',
        ]
    
    def extract_companies(self, text: str) -> List[str]:
        """Extract company names from text"""
        companies = set()
        for pattern in self.company_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            companies.update([m.strip() for m in matches])
        return sorted(list(companies))
    
    def extract_people(self, text: str) -> List[str]:
        """Extract person names from text"""
        people = set()
        for pattern in self.person_patterns:
            matches = re.findall(pattern, text)
            # Filter out common false positives
            for match in matches:
                words = match.split()
                if len(words) >= 2 and all(word[0].isupper() for word in words):
                    people.add(match)
        return sorted(list(people))
    
    def extract_topics(self, text: str) -> List[str]:
        """Extract topics based on keyword matching"""
        text_lower = text.lower()
        found_topics = set()
        
        for topic, keywords in self.topic_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                found_topics.add(topic)
        
        return sorted(list(found_topics))
    
    def extract_projects(self, text: str) -> List[str]:
        """Extract project/task references"""
        projects = set()
        for pattern in self.project_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            projects.update([m.strip() for m in matches])
        return sorted(list(projects))
    
    def extract_emails(self, text: str) -> List[str]:
        """Extract email addresses"""
        email_pattern = r'[\w\.-]+@[\w\.-]+\.\w+'
        emails = re.findall(email_pattern, text)
        return sorted(list(set(emails)))
    
    def extract_dates(self, text: str) -> List[str]:
        """Extract date references (ISO format or common formats)"""
        date_patterns = [
            r'\b\d{4}-\d{2}-\d{2}\b',  # ISO format
            r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4}\b',  # Month Day, Year
            r'\b\d{1,2}/\d{1,2}/\d{4}\b',  # MM/DD/YYYY
        ]
        dates = set()
        for pattern in date_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            dates.update(matches)
        return sorted(list(dates))
    
    def extract_all(self, text: str) -> Dict[str, List[str]]:
        """Extract all entities from text"""
        return {
            'companies': self.extract_companies(text),
            'people': self.extract_people(text),
            'topics': self.extract_topics(text),
            'projects': self.extract_projects(text),
            'emails': self.extract_emails(text),
            'dates': self.extract_dates(text)
        }
    
    def generate_entity_ids(self, entities: Dict[str, List[str]]) -> List[str]:
        """Generate standardized entity IDs from extracted entities"""
        entity_ids = []
        
        # Prefix entities by type for uniqueness
        for company in entities.get('companies', []):
            entity_ids.append(f"company_{company.lower().replace(' ', '_')}")
        
        for person in entities.get('people', []):
            entity_ids.append(f"person_{person.lower().replace(' ', '_')}")
        
        for project in entities.get('projects', []):
            entity_ids.append(f"project_{project.lower().replace(' ', '_')}")
        
        for email in entities.get('emails', []):
            entity_ids.append(f"email_{email.lower()}")
        
        return entity_ids
    
    def infer_time_context(self, text: str, metadata: Dict = None) -> Dict:
        """Infer time context from text and existing metadata"""
        time_context = {}
        
        # Extract dates from text
        dates = self.extract_dates(text)
        if dates:
            time_context['mentioned_dates'] = dates
        
        # Use existing created_date if available
        if metadata and metadata.get('created_date'):
            time_context['document_date'] = metadata['created_date']
        
        return time_context if time_context else None


def extract_entities_for_document(text: str, metadata: Dict = None) -> Dict:
    """
    Convenience function to extract all entities and generate enhanced metadata fields.
    
    Args:
        text: Document text content
        metadata: Existing metadata dict (optional)
    
    Returns:
        Dict with entity_ids, topics, and time_context for enhanced metadata
    """
    extractor = EntityExtractor()
    entities = extractor.extract_all(text)
    
    result = {
        'entity_ids': extractor.generate_entity_ids(entities),
        'topics': entities['topics'],
        'time_context': extractor.infer_time_context(text, metadata)
    }
    
    # Remove None values
    return {k: v for k, v in result.items() if v}


if __name__ == "__main__":
    # Test the extractor
    test_text = """
    Henry and Matt discussed investment opportunities in NVIDIA and AMD.
    The meeting was on 2024-03-15. They considered CoreWeave as a potential investment
    but were concerned about the company's debt. Henry is also working on the AI Research Project.
    Contact henry@example.com for more information.
    """
    
    extractor = EntityExtractor()
    entities = extractor.extract_all(test_text)
    
    print("Extracted Entities:")
    for entity_type, items in entities.items():
        print(f"  {entity_type}: {items}")
    
    print("\nEntity IDs:")
    entity_ids = extractor.generate_entity_ids(entities)
    print(f"  {entity_ids}")
    
    print("\nEnhanced metadata fields:")
    enhanced = extract_entities_for_document(test_text)
    for key, value in enhanced.items():
        print(f"  {key}: {value}")
