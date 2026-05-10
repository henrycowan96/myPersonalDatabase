"""
Entity extraction utilities for document processing.
"""

import re
from typing import List, Dict, Any
from datetime import datetime


def extract_entities_for_document(text: str, document_type: str = "general") -> Dict[str, Any]:
    """
    Extract entities from a document text.
    
    Args:
        text: The document text to analyze
        document_type: Type of document (email, calendar, note, etc.)
    
    Returns:
        Dictionary containing extracted entities
    """
    entities = {
        "people": [],
        "organizations": [],
        "locations": [],
        "dates": [],
        "emails": [],
        "phone_numbers": [],
        "urls": [],
        "keywords": []
    }
    
    # Extract email addresses
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    entities["emails"] = re.findall(email_pattern, text)
    
    # Extract phone numbers (basic pattern)
    phone_pattern = r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'
    entities["phone_numbers"] = re.findall(phone_pattern, text)
    
    # Extract URLs
    url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    entities["urls"] = re.findall(url_pattern, text)
    
    # Extract dates (basic patterns)
    date_patterns = [
        r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',  # MM/DD/YYYY
        r'\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b',    # YYYY/MM/DD
        r'\b\w+ \d{1,2}, \d{4}\b',             # January 1, 2024
    ]
    
    for pattern in date_patterns:
        entities["dates"].extend(re.findall(pattern, text))
    
    # Document-specific extraction
    if document_type == "email":
        entities.update(_extract_email_entities(text))
    elif document_type == "calendar":
        entities.update(_extract_calendar_entities(text))
    elif document_type == "note":
        entities.update(_extract_note_entities(text))
    
    # Extract common proper nouns (simplified)
    words = text.split()
    for word in words:
        if word.istitle() and len(word) > 3 and word not in entities["keywords"]:
            entities["keywords"].append(word)
    
    return entities


def _extract_email_entities(text: str) -> Dict[str, Any]:
    """Extract email-specific entities"""
    entities = {
        "subject": "",
        "sender": "",
        "recipients": []
    }
    
    lines = text.split('\n')
    for line in lines:
        if line.lower().startswith('subject:'):
            entities["subject"] = line.replace('Subject:', '').strip()
        elif line.lower().startswith('from:'):
            entities["sender"] = line.replace('From:', '').strip()
        elif line.lower().startswith('to:'):
            entities["recipients"].append(line.replace('To:', '').strip())
    
    return entities


def _extract_calendar_entities(text: str) -> Dict[str, Any]:
    """Extract calendar-specific entities"""
    entities = {
        "event_title": "",
        "location": "",
        "attendees": []
    }
    
    lines = text.split('\n')
    for line in lines:
        if 'Event:' in line:
            entities["event_title"] = line.replace('Event:', '').strip()
        elif 'Location:' in line:
            entities["location"] = line.replace('Location:', '').strip()
        elif 'Attendee:' in line:
            entities["attendees"].append(line.replace('Attendee:', '').strip())
    
    return entities


def _extract_note_entities(text: str) -> Dict[str, Any]:
    """Extract note-specific entities"""
    entities = {
        "title": "",
        "tags": []
    }
    
    lines = text.split('\n')
    for line in lines:
        if line.startswith('#') or line.startswith('Note:'):
            entities["title"] = line.replace('#', '').replace('Note:', '').strip()
        elif line.startswith('#'):
            entities["tags"].append(line.replace('#', '').strip())
    
    return entities
