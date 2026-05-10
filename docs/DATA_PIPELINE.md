# Data Extraction & Processing Pipeline Documentation

## Overview

The Personal Database Mobile data pipeline is a sophisticated system designed to extract, process, and ingest data from multiple sources while maintaining data integrity, privacy, and performance. The pipeline follows an ETL (Extract, Transform, Load) pattern with additional enrichment and indexing stages.

## Pipeline Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Data Sources  │───▶│   Extraction    │───▶│  Processing     │
│                 │    │                 │    │                 │
│ • Apple Notes   │    │ • API Clients   │    │ • Text Mining   │
│ • Google Drive  │    │ • File Readers  │    │ • Metadata      │
│ • Gmail         │    │ • Parsers       │    │ • Enrichment    │
│ • Calendar      │    │ • Validators    │    │ • Deduplication │
│ • Messages      │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        │
                                                        ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Search Index  │◀───│   Ingestion     │◀───│   Quality       │
│                 │    │                 │    │                 │
│ • Vector Store  │    │ • Embeddings    │    │ • Validation    │
│ • Metadata      │    │ • Indexing      │    │ • Filtering     │
│ • Search API    │    │ • Storage       │    │ • Scoring       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Core Components

### 1. Extraction Layer (`scripts/`)

#### Apple Ecosystem Integration
```python
# Apple-specific data sources
├── fetch_apple_notes.py      # Notes extraction from macOS
├── fetch_apple_calendar.py    # Calendar events extraction
├── fetch_apple_music.py       # Apple Music data (optional)
└── parse_messages.py          # iMessage parsing
```

**Key Features:**
- **Native Integration:** Direct access to macOS databases
- **Privacy-First:** Local processing without cloud transmission
- **Format Handling:** Multiple file format support
- **Incremental Updates:** Only new/changed data extracted

#### Google Services Integration
```python
# Google Workspace integration
├── fetch_google_docs.py       # Google Docs extraction
├── fetch_drive_files.py       # Google Drive files
├── fetch_emails.py           # Gmail extraction
├── fetch_calendar.py          # Google Calendar
└── fetch_google_search_history.py # Search history (takeout)
```

**Key Features:**
- **OAuth2 Authentication:** Secure API access
- **Rate Limiting:** Respectful API usage
- **Batch Processing:** Efficient data retrieval
- **Error Handling:** Robust retry mechanisms

#### Universal File Processing
```python
# File format conversion and processing
├── convert_drive_files.py     # Document format conversion
├── entity_extraction.py       # Named entity recognition
├── metadata_utils.py         # Metadata generation
└── organize_root_files.py    # File categorization
```

### 2. Processing Layer

#### Text Processing Pipeline
```python
# Text analysis and enrichment
def process_document(content: str, metadata: dict) -> ProcessedDocument:
    """
    Core document processing pipeline
    """
    # 1. Content cleaning and normalization
    cleaned_content = clean_text(content)
    
    # 2. Entity extraction and tagging
    entities = extract_entities(cleaned_content)
    
    # 3. Content categorization
    category = categorize_content(cleaned_content, metadata)
    
    # 4. Quality scoring
    quality_score = calculate_quality_score(cleaned_content, metadata)
    
    # 5. Metadata enrichment
    enriched_metadata = enrich_metadata(metadata, entities, category)
    
    return ProcessedDocument(
        content=cleaned_content,
        metadata=enriched_metadata,
        entities=entities,
        category=category,
        quality_score=quality_score
    )
```

#### Metadata Generation
```python
# Comprehensive metadata extraction
def generate_metadata(
    source: str,
    type: str,
    author: Optional[str],
    created_date: Optional[str],
    modified_date: Optional[str],
    **kwargs
) -> dict:
    """
    Generate standardized metadata for documents
    """
    return {
        "source": source,
        "type": type,
        "author": author,
        "created_date": created_date,
        "modified_date": modified_date,
        "extracted_date": datetime.now().isoformat(),
        "language": detect_language(content),
        "word_count": len(content.split()),
        "character_count": len(content),
        "has_tables": contains_tables(content),
        "has_images": contains_images(content),
        "sentiment_score": analyze_sentiment(content),
        "keywords": extract_keywords(content),
        "summary": generate_summary(content),
        **kwargs
    }
```

### 3. Ingestion Layer

#### Vector Embedding Pipeline
```python
# Document embedding and indexing
class DocumentIndexer:
    def __init__(self, embedding_model, vector_store):
        self.embedding_model = embedding_model
        self.vector_store = vector_store
    
    async def index_document(self, document: ProcessedDocument) -> str:
        """
        Index document in vector store
        """
        # 1. Generate embeddings
        embeddings = await self.generate_embeddings(document.content)
        
        # 2. Prepare vector store entry
        vector_entry = {
            "id": document.id,
            "values": embeddings,
            "metadata": {
                "text": document.content,
                "source": document.metadata.source,
                "type": document.metadata.type,
                "author": document.metadata.author,
                "created_date": document.metadata.created_date,
                "category": document.category,
                "quality_score": document.quality_score,
                "entities": document.entities,
                **document.metadata
            }
        }
        
        # 3. Store in vector database
        result = await self.vector_store.upsert([vector_entry])
        
        return result["ids"][0]
```

## Data Source Integrations

### 1. Apple Notes Integration

#### Extraction Process
```python
# Apple Notes extraction from macOS database
def fetch_apple_notes():
    """
    Extract notes from Apple Notes database
    """
    notes_db_path = "~/Library/Group Containers/group.com.apple.notes/NoteStore.sqlite"
    
    # Connect to SQLite database
    conn = sqlite3.connect(os.path.expanduser(notes_db_path))
    
    # Extract notes with metadata
    query = """
    SELECT 
        ZUUID,
        ZTITLE1,
        ZTEXT,
        ZCREATIONDATE1,
        ZMODIFICATIONDATE1,
        ZFOLDER
    FROM ZICNOTEDATA
    JOIN ZICNOTE ON ZICNOTEDATA.ZNOTE = ZICNOTE.Z_PK
    """
    
    notes = []
    for row in conn.execute(query):
        note = {
            "id": row[0],
            "title": row[1],
            "content": row[2],
            "created_date": convert_mac_timestamp(row[3]),
            "modified_date": convert_mac_timestamp(row[4]),
            "folder": row[5]
        }
        notes.append(note)
    
    return notes
```

#### Data Processing
- **Content Cleaning:** Remove Apple-specific formatting
- **Attachment Handling:** Extract and process attached files
- **Folder Structure:** Preserve organizational hierarchy
- **Privacy Filtering:** Remove sensitive system information

### 2. Google Workspace Integration

#### Gmail Integration
```python
# Gmail extraction with OAuth2
async def fetch_gmail_emails(max_emails: int = 100):
    """
    Fetch emails from Gmail API
    """
    service = build('gmail', 'v1', credentials=credentials)
    
    # Get message list
    results = service.users().messages().list(
        userId='me',
        maxResults=max_emails,
        q='is:inbox'
    ).execute()
    
    messages = results.get('messages', [])
    
    emails = []
    for message in messages:
        msg = service.users().messages().get(
            userId='me',
            id=message['id'],
            format='full'
        ).execute()
        
        # Extract email data
        email_data = parse_gmail_message(msg)
        emails.append(email_data)
    
    return emails
```

#### Google Drive Integration
```python
# Google Drive file extraction
async def fetch_drive_files():
    """
    Fetch files from Google Drive
    """
    service = build('drive', 'v3', credentials=credentials)
    
    # Get all files
    results = service.files().list(
        pageSize=1000,
        fields="nextPageToken, files(id, name, mimeType, createdTime, modifiedTime)"
    ).execute()
    
    files = results.get('files', [])
    
    processed_files = []
    for file in files:
        # Download and process file
        file_content = download_file_content(service, file['id'])
        processed_file = process_file(file, file_content)
        processed_files.append(processed_file)
    
    return processed_files
```

### 3. Message Processing

#### iMessage Integration
```python
# iMessage database parsing
def parse_messages():
    """
    Parse iMessage database
    """
    chat_db_path = "~/Library/Messages/chat.db"
    
    conn = sqlite3.connect(os.path.expanduser(chat_db_path))
    
    # Extract messages with metadata
    query = """
    SELECT 
        message.ROWID,
        message.text,
        message.handle_id,
        message.date,
        message.is_from_me,
        handle.id
    FROM message
    JOIN handle ON message.handle_id = handle.ROWID
    WHERE message.text IS NOT NULL
    ORDER BY message.date
    """
    
    messages = []
    for row in conn.execute(query):
        message = {
            "id": row[0],
            "text": row[1],
            "handle_id": row[2],
            "date": convert_ios_timestamp(row[3]),
            "is_from_me": bool(row[4]),
            "contact": row[5]
        }
        messages.append(message)
    
    return messages
```

## Data Processing Stages

### 1. Content Cleaning

#### Text Normalization
```python
def clean_text(text: str) -> str:
    """
    Clean and normalize text content
    """
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Remove special characters (keep basic punctuation)
    text = re.sub(r'[^\w\s\.\,\!\?\;\:\-\(\)]', '', text)
    
    # Normalize line endings
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    
    # Remove leading/trailing whitespace
    text = text.strip()
    
    return text
```

#### Format-Specific Processing
```python
# Document format conversion
def convert_document(file_path: str, output_format: str = 'text') -> str:
    """
    Convert various document formats to plain text
    """
    file_extension = Path(file_path).suffix.lower()
    
    if file_extension == '.docx':
        return convert_docx_to_text(file_path)
    elif file_extension == '.pdf':
        return convert_pdf_to_text(file_path)
    elif file_extension == '.pptx':
        return convert_pptx_to_text(file_path)
    elif file_extension == '.xlsx':
        return convert_xlsx_to_text(file_path)
    else:
        # Assume plain text
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
```

### 2. Entity Extraction

#### Named Entity Recognition
```python
def extract_entities(text: str) -> dict:
    """
    Extract named entities from text
    """
    entities = {
        "persons": [],
        "organizations": [],
        "locations": [],
        "dates": [],
        "emails": [],
        "phone_numbers": [],
        "urls": []
    }
    
    # Email extraction
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    entities["emails"] = re.findall(email_pattern, text)
    
    # Phone number extraction
    phone_pattern = r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'
    entities["phone_numbers"] = re.findall(phone_pattern, text)
    
    # URL extraction
    url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    entities["urls"] = re.findall(url_pattern, text)
    
    # Date extraction
    date_pattern = r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b|\b\d{4}-\d{2}-\d{2}\b'
    entities["dates"] = re.findall(date_pattern, text)
    
    return entities
```

### 3. Content Categorization

#### Automatic Categorization
```python
def categorize_content(content: str, metadata: dict) -> str:
    """
    Automatically categorize document content
    """
    # Define category keywords and patterns
    categories = {
        'personal': ['personal', 'private', 'family', 'friend'],
        'work': ['work', 'project', 'meeting', 'deadline', 'office'],
        'finance': ['money', 'payment', 'invoice', 'budget', 'expense'],
        'health': ['health', 'medical', 'doctor', 'medicine', 'appointment'],
        'travel': ['travel', 'trip', 'flight', 'hotel', 'vacation'],
        'education': ['study', 'course', 'class', 'homework', 'exam'],
        'shopping': ['buy', 'purchase', 'order', 'shopping', 'store']
    }
    
    content_lower = content.lower()
    scores = {}
    
    for category, keywords in categories.items():
        score = 0
        for keyword in keywords:
            score += content_lower.count(keyword)
        scores[category] = score
    
    # Return category with highest score
    if max(scores.values()) > 0:
        return max(scores, key=scores.get)
    else:
        return 'general'
```

## Quality Assurance

### 1. Data Validation

#### Content Quality Scoring
```python
def calculate_quality_score(content: str, metadata: dict) -> float:
    """
    Calculate quality score for document
    """
    score = 0.0
    
    # Length scoring
    word_count = len(content.split())
    if word_count > 10:
        score += 0.2
    if word_count > 50:
        score += 0.2
    
    # Metadata completeness
    metadata_fields = ['author', 'created_date', 'source']
    complete_fields = sum(1 for field in metadata_fields if metadata.get(field))
    score += (complete_fields / len(metadata_fields)) * 0.3
    
    # Content structure
    if '\n' in content:  # Has structure
        score += 0.1
    if any(punct in content for punct in ['.', '!', '?']):  # Has sentences
        score += 0.1
    
    # Language detection
    if detect_language(content) == 'en':
        score += 0.1
    
    return min(score, 1.0)
```

### 2. Deduplication

#### Document Similarity Detection
```python
def detect_duplicates(documents: List[ProcessedDocument]) -> List[int]:
    """
    Detect duplicate documents based on content similarity
    """
    duplicates = []
    
    for i, doc1 in enumerate(documents):
        for j, doc2 in enumerate(documents[i+1:], i+1):
            # Calculate similarity
            similarity = calculate_similarity(doc1.content, doc2.content)
            
            if similarity > 0.9:  # High similarity threshold
                duplicates.append(j)  # Mark second document as duplicate
    
    return duplicates
```

## Performance Optimization

### 1. Batch Processing

#### Parallel Processing
```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

async def process_documents_batch(documents: List[str]) -> List[ProcessedDocument]:
    """
    Process documents in parallel batches
    """
    batch_size = 10
    results = []
    
    with ThreadPoolExecutor(max_workers=4) as executor:
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i+batch_size]
            
            # Process batch in parallel
            loop = asyncio.get_event_loop()
            batch_results = await loop.run_in_executor(
                executor, 
                process_single_batch, 
                batch
            )
            
            results.extend(batch_results)
    
    return results
```

### 2. Memory Management

#### Streaming Processing
```python
def process_large_file(file_path: str, chunk_size: int = 1024):
    """
    Process large files in chunks to manage memory
    """
    with open(file_path, 'r', encoding='utf-8') as file:
        chunk = []
        for line in file:
            chunk.append(line)
            
            if len(chunk) >= chunk_size:
                # Process chunk
                process_chunk(chunk)
                chunk = []  # Reset chunk
        
        # Process remaining lines
        if chunk:
            process_chunk(chunk)
```

## Error Handling & Recovery

### 1. Retry Logic

#### Exponential Backoff
```python
import time
import random

def retry_with_backoff(func, max_retries=3, base_delay=1):
    """
    Retry function with exponential backoff
    """
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            
            # Calculate delay with jitter
            delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
            time.sleep(delay)
```

### 2. Data Recovery

#### Checkpoint System
```python
class ProcessingCheckpoint:
    """
    Checkpoint system for data processing recovery
    """
    def __init__(self, checkpoint_file: str):
        self.checkpoint_file = checkpoint_file
        self.checkpoints = self.load_checkpoints()
    
    def save_checkpoint(self, batch_id: str, status: str):
        """Save processing checkpoint"""
        self.checkpoints[batch_id] = {
            'status': status,
            'timestamp': datetime.now().isoformat()
        }
        self.save_checkpoints()
    
    def get_failed_batches(self) -> List[str]:
        """Get list of failed batches for retry"""
        return [
            batch_id for batch_id, data in self.checkpoints.items()
            if data['status'] == 'failed'
        ]
```

## Monitoring & Analytics

### 1. Pipeline Metrics

#### Processing Statistics
```python
class PipelineMetrics:
    """
    Track pipeline processing metrics
    """
    def __init__(self):
        self.metrics = {
            'documents_processed': 0,
            'processing_time_total': 0,
            'errors_count': 0,
            'duplicate_count': 0,
            'quality_scores': []
        }
    
    def record_processing(self, processing_time: float, quality_score: float):
        """Record processing metrics"""
        self.metrics['documents_processed'] += 1
        self.metrics['processing_time_total'] += processing_time
        self.metrics['quality_scores'].append(quality_score)
    
    def get_average_processing_time(self) -> float:
        """Calculate average processing time"""
        if self.metrics['documents_processed'] == 0:
            return 0
        return self.metrics['processing_time_total'] / self.metrics['documents_processed']
```

### 2. Data Quality Monitoring

#### Quality Dashboards
```python
def generate_quality_report(metrics: PipelineMetrics) -> dict:
    """
    Generate data quality report
    """
    return {
        'total_documents': metrics.metrics['documents_processed'],
        'average_quality_score': np.mean(metrics.metrics['quality_scores']),
        'processing_errors': metrics.metrics['errors_count'],
        'duplicate_rate': metrics.metrics['duplicate_count'] / metrics.metrics['documents_processed'],
        'average_processing_time': metrics.get_average_processing_time()
    }
```

## Security & Compliance

### 1. Data Privacy

#### PII Detection and Redaction
```python
def redact_pii(text: str) -> str:
    """
    Detect and redact personally identifiable information
    """
    # Redact emails
    text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL_REDACTED]', text)
    
    # Redact phone numbers
    text = re.sub(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '[PHONE_REDACTED]', text)
    
    # Redate social security numbers
    text = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '[SSN_REDACTED]', text)
    
    return text
```

### 2. Compliance Logging

#### Audit Trail
```python
def log_data_access(user_id: str, document_id: str, action: str):
    """
    Log data access for compliance
    """
    access_log = {
        'timestamp': datetime.now().isoformat(),
        'user_id': user_id,
        'document_id': document_id,
        'action': action,
        'ip_address': get_client_ip()
    }
    
    # Store in secure audit log
    store_audit_log(access_log)
```

---

*This documentation is proprietary and confidential. All rights reserved.*
