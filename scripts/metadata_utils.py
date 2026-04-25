import json
from datetime import datetime
from pathlib import Path


def generate_metadata(source, type, author=None, created_date=None, modified_date=None, 
                      entity_ids=None, time_context=None, relationships=None, 
                      tags=None, topics=None, **extra_fields):
    """
    Generate standardized metadata for extracted files with relationship tracking.
    
    Args:
        source: Where the file came from (e.g., 'apple_notes', 'gmail', 'google_drive')
        type: What type of thing it is (e.g., 'note', 'email', 'document', 'event')
        author: Who created it (if available)
        created_date: When it was created (ISO format string or datetime)
        modified_date: When it was last modified (ISO format string or datetime)
        entity_ids: List of entity identifiers (people, companies, projects)
        time_context: Dict with time_range_start, time_range_end, related_events
        relationships: List of dicts with 'type' and 'target' for document relationships
        tags: List of user-defined tags
        topics: List of extracted topics/themes
        **extra_fields: Additional source-specific metadata
    
    Returns:
        dict: Standardized metadata dictionary
    """
    metadata = {
        "source": source,
        "type": type,
        "author": author,
        "created_date": _format_date(created_date) if created_date else None,
        "modified_date": _format_date(modified_date) if modified_date else None,
        "extracted_at": datetime.now().isoformat(),
    }
    
    # Add relationship tracking fields if provided
    if entity_ids:
        metadata["entity_ids"] = entity_ids
    if time_context:
        metadata["time_context"] = time_context
    if relationships:
        metadata["relationships"] = relationships
    if tags:
        metadata["tags"] = tags
    if topics:
        metadata["topics"] = topics
    
    # Add any extra fields
    metadata.update(extra_fields)
    
    # Remove None values
    metadata = {k: v for k, v in metadata.items() if v is not None}
    
    return metadata


def _format_date(date_value):
    """Convert various date formats to ISO string"""
    if isinstance(date_value, str):
        return date_value
    elif isinstance(date_value, datetime):
        return date_value.isoformat()
    else:
        return str(date_value)


def format_metadata_header(metadata):
    """Format metadata as a header block for text files"""
    lines = ["=== METADATA ==="]
    lines.append(json.dumps(metadata, indent=2))
    lines.append("=== END METADATA ===")
    lines.append("")
    return "\n".join(lines)


def save_with_metadata(file_path, content, metadata):
    """
    Save content with metadata header to a file.
    
    Args:
        file_path: Path to save the file
        content: Main content to save
        metadata: Metadata dictionary from generate_metadata()
    """
    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(format_metadata_header(metadata))
        f.write(content)
    
    return file_path
