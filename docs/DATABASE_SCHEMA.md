# Database Schema & Data Models Documentation

## Overview

Personal Database Mobile utilizes a dual-database architecture: Supabase (PostgreSQL) for relational data and Pinecone for vector storage. This document provides comprehensive documentation of the database schema, data models, relationships, and optimization strategies.

## Database Architecture

```
┌─────────────────┐    ┌─────────────────┐
│   Supabase      │    │    Pinecone     │
│  (PostgreSQL)   │    │  (Vector DB)    │
│                 │    │                 │
│ • User Data     │    │ • Document      │
│ • Sessions      │    │   Embeddings    │
│ • Settings      │    │ • Search Index  │
│ • Audit Logs    │    │ • Metadata      │
│ • Analytics     │    │                 │
└─────────────────┘    └─────────────────┘
```

## Supabase Database Schema

### 1. User Management Tables

#### users
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    full_name VARCHAR(255),
    avatar_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_login TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT true,
    subscription_tier VARCHAR(50) DEFAULT 'free',
    storage_quota_mb INTEGER DEFAULT 1000,
    current_storage_mb INTEGER DEFAULT 0
);

-- Indexes
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_created_at ON users(created_at);
CREATE INDEX idx_users_subscription_tier ON users(subscription_tier);
```

#### user_settings
```sql
CREATE TABLE user_settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    setting_key VARCHAR(100) NOT NULL,
    setting_value JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, setting_key)
);

-- Indexes
CREATE INDEX idx_user_settings_user_id ON user_settings(user_id);
CREATE INDEX idx_user_settings_key ON user_settings(setting_key);
```

#### user_preferences
```sql
CREATE TABLE user_preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    theme VARCHAR(20) DEFAULT 'system',
    language VARCHAR(10) DEFAULT 'en',
    notifications_enabled BOOLEAN DEFAULT true,
    auto_sync_enabled BOOLEAN DEFAULT true,
    search_preferences JSONB DEFAULT '{}',
    privacy_settings JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_user_preferences_user_id ON user_preferences(user_id);
```

### 2. Authentication & Sessions

#### auth_sessions
```sql
CREATE TABLE auth_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_token VARCHAR(255) UNIQUE NOT NULL,
    refresh_token VARCHAR(255) UNIQUE,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_accessed TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    ip_address INET,
    user_agent TEXT,
    is_active BOOLEAN DEFAULT true
);

-- Indexes
CREATE INDEX idx_auth_sessions_user_id ON auth_sessions(user_id);
CREATE INDEX idx_auth_sessions_token ON auth_sessions(session_token);
CREATE INDEX idx_auth_sessions_expires_at ON auth_sessions(expires_at);
```

#### oauth_providers
```sql
CREATE TABLE oauth_providers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider VARCHAR(50) NOT NULL, -- 'google', 'apple', 'github'
    provider_user_id VARCHAR(255) NOT NULL,
    access_token TEXT,
    refresh_token TEXT,
    token_expires_at TIMESTAMP WITH TIME ZONE,
    scope TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, provider)
);

-- Indexes
CREATE INDEX idx_oauth_providers_user_id ON oauth_providers(user_id);
CREATE INDEX idx_oauth_providers_provider ON oauth_providers(provider);
```

### 3. Data Source Management

#### data_sources
```sql
CREATE TABLE data_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    source_type VARCHAR(50) NOT NULL, -- 'google_drive', 'apple_notes', 'gmail', etc.
    source_name VARCHAR(255) NOT NULL,
    connection_config JSONB NOT NULL,
    is_active BOOLEAN DEFAULT true,
    last_sync TIMESTAMP WITH TIME ZONE,
    sync_frequency VARCHAR(20) DEFAULT 'daily', -- 'hourly', 'daily', 'weekly'
    sync_status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'syncing', 'completed', 'failed'
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_data_sources_user_id ON data_sources(user_id);
CREATE INDEX idx_data_sources_type ON data_sources(source_type);
CREATE INDEX idx_data_sources_active ON data_sources(is_active);
```

#### sync_logs
```sql
CREATE TABLE sync_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    data_source_id UUID NOT NULL REFERENCES data_sources(id) ON DELETE CASCADE,
    sync_type VARCHAR(50) NOT NULL, -- 'full', 'incremental'
    status VARCHAR(20) NOT NULL, -- 'started', 'completed', 'failed', 'cancelled'
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    items_processed INTEGER DEFAULT 0,
    items_created INTEGER DEFAULT 0,
    items_updated INTEGER DEFAULT 0,
    items_failed INTEGER DEFAULT 0,
    error_message TEXT,
    metadata JSONB DEFAULT '{}'
);

-- Indexes
CREATE INDEX idx_sync_logs_data_source_id ON sync_logs(data_source_id);
CREATE INDEX idx_sync_logs_status ON sync_logs(status);
CREATE INDEX idx_sync_logs_started_at ON sync_logs(started_at);
```

### 4. Document Management

#### documents
```sql
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    data_source_id UUID REFERENCES data_sources(id) ON DELETE SET NULL,
    title VARCHAR(500),
    content TEXT,
    content_hash VARCHAR(64) UNIQUE, -- SHA-256 hash for deduplication
    file_path TEXT,
    file_size BIGINT,
    mime_type VARCHAR(100),
    source_type VARCHAR(50), -- 'apple_notes', 'google_drive', 'gmail', etc.
    source_id VARCHAR(255), -- Original ID from source
    author VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE,
    modified_at TIMESTAMP WITH TIME ZONE,
    indexed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_deleted BOOLEAN DEFAULT false,
    quality_score DECIMAL(3,2) DEFAULT 0.0,
    metadata JSONB DEFAULT '{}',
    tags TEXT[],
    category VARCHAR(100),
    language VARCHAR(10) DEFAULT 'en'
);

-- Indexes
CREATE INDEX idx_documents_user_id ON documents(user_id);
CREATE INDEX idx_documents_data_source_id ON documents(data_source_id);
CREATE INDEX idx_documents_content_hash ON documents(content_hash);
CREATE INDEX idx_documents_source_type ON documents(source_type);
CREATE INDEX idx_documents_created_at ON documents(created_at);
CREATE INDEX idx_documents_indexed_at ON documents(indexed_at);
CREATE INDEX idx_documents_category ON documents(category);
CREATE INDEX idx_documents_tags ON documents USING GIN(tags);
CREATE INDEX idx_documents_metadata ON documents USING GIN(metadata);
```

#### document_entities
```sql
CREATE TABLE document_entities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    entity_type VARCHAR(50) NOT NULL, -- 'person', 'organization', 'location', 'date', etc.
    entity_value VARCHAR(500) NOT NULL,
    confidence_score DECIMAL(3,2) DEFAULT 0.0,
    start_position INTEGER,
    end_position INTEGER,
    context TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_document_entities_document_id ON document_entities(document_id);
CREATE INDEX idx_document_entities_type ON document_entities(entity_type);
CREATE INDEX idx_document_entities_value ON document_entities(entity_value);
CREATE INDEX idx_document_entities_confidence ON document_entities(confidence_score);
```

### 5. Search & Analytics

#### search_history
```sql
CREATE TABLE search_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    query TEXT NOT NULL,
    filters JSONB DEFAULT '{}',
    results_count INTEGER DEFAULT 0,
    response_time_ms INTEGER,
    clicked_result_id UUID REFERENCES documents(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_search_history_user_id ON search_history(user_id);
CREATE INDEX idx_search_history_created_at ON search_history(created_at);
CREATE INDEX idx_search_history_query ON search_history USING GIN(to_tsvector('english', query));
```

#### user_analytics
```sql
CREATE TABLE user_analytics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    event_type VARCHAR(100) NOT NULL, -- 'search', 'document_view', 'sync', etc.
    event_data JSONB DEFAULT '{}',
    session_id UUID,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_user_analytics_user_id ON user_analytics(user_id);
CREATE INDEX idx_user_analytics_event_type ON user_analytics(event_type);
CREATE INDEX idx_user_analytics_created_at ON user_analytics(created_at);
CREATE INDEX idx_user_analytics_session_id ON user_analytics(session_id);
```

### 6. Chat & Conversations

#### conversations
```sql
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_active BOOLEAN DEFAULT true,
    metadata JSONB DEFAULT '{}'
);

-- Indexes
CREATE INDEX idx_conversations_user_id ON conversations(user_id);
CREATE INDEX idx_conversations_created_at ON conversations(created_at);
CREATE INDEX idx_conversations_active ON conversations(is_active);
```

#### chat_messages
```sql
CREATE TABLE chat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    message_type VARCHAR(20) NOT NULL, -- 'user', 'assistant', 'system'
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}', -- sources, tokens, etc.
    llm_thoughts TEXT, -- AI reasoning process
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    feedback_score INTEGER CHECK (feedback_score >= 1 AND feedback_score <= 5),
    feedback_comment TEXT
);

-- Indexes
CREATE INDEX idx_chat_messages_conversation_id ON chat_messages(conversation_id);
CREATE INDEX idx_chat_messages_created_at ON chat_messages(created_at);
CREATE INDEX idx_chat_messages_type ON chat_messages(message_type);
```

### 7. System & Audit Tables

#### audit_logs
```sql
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL, -- 'create', 'read', 'update', 'delete'
    resource_type VARCHAR(100) NOT NULL, -- 'document', 'user', 'data_source'
    resource_id UUID,
    old_values JSONB,
    new_values JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);
CREATE INDEX idx_audit_logs_resource_type ON audit_logs(resource_type);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at);
```

#### system_settings
```sql
CREATE TABLE system_settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    setting_key VARCHAR(100) UNIQUE NOT NULL,
    setting_value JSONB NOT NULL,
    description TEXT,
    is_public BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_system_settings_key ON system_settings(setting_key);
CREATE INDEX idx_system_settings_public ON system_settings(is_public);
```

## Pinecone Vector Database Schema

### Vector Index Structure

#### Index Configuration
```python
# Pinecone index configuration
index_config = {
    "name": "personal-database",
    "dimension": 384,  # Sentence Transformers all-MiniLM-L6-v2
    "metric": "cosine",
    "pods": 1,
    "replicas": 1,
    "pod_type": "p1.x1"
}

# Metadata schema for vectors
vector_metadata_schema = {
    "document_id": "string",
    "user_id": "string",
    "content": "string",
    "source_type": "string",
    "category": "string",
    "author": "string",
    "created_date": "string",
    "modified_date": "string",
    "quality_score": "float",
    "language": "string",
    "tags": "list<string>",
    "entities": "dict",
    "chunk_index": "int",
    "chunk_count": "int"
}
```

#### Vector Storage Strategy
```python
# Document chunking for vector storage
class DocumentChunker:
    def __init__(self, chunk_size: int = 500, overlap: int = 50):
        self.chunk_size = chunk_size
        self.overlap = overlap
    
    def chunk_document(self, document: dict) -> List[dict]:
        """
        Split document into chunks for vector storage
        """
        content = document['content']
        metadata = document['metadata']
        
        # Split content into chunks
        chunks = []
        words = content.split()
        
        for i in range(0, len(words), self.chunk_size - self.overlap):
            chunk_words = words[i:i + self.chunk_size]
            chunk_content = ' '.join(chunk_words)
            
            chunk_metadata = {
                **metadata,
                'chunk_index': len(chunks),
                'chunk_count': math.ceil(len(words) / (self.chunk_size - self.overlap)),
                'content': chunk_content
            }
            
            chunks.append(chunk_metadata)
        
        return chunks
```

## Data Models (Python)

### 1. User Models

#### User Model
```python
from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum

class SubscriptionTier(str, Enum):
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"

class User(BaseModel):
    id: str
    email: EmailStr
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None
    is_active: bool = True
    subscription_tier: SubscriptionTier = SubscriptionTier.FREE
    storage_quota_mb: int = 1000
    current_storage_mb: int = 0

class UserCreate(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    password: str

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    is_active: Optional[bool] = None
    subscription_tier: Optional[SubscriptionTier] = None
```

#### User Settings Model
```python
class UserSetting(BaseModel):
    id: str
    user_id: str
    setting_key: str
    setting_value: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

class UserPreferences(BaseModel):
    id: str
    user_id: str
    theme: str = "system"
    language: str = "en"
    notifications_enabled: bool = True
    auto_sync_enabled: bool = True
    search_preferences: Dict[str, Any] = {}
    privacy_settings: Dict[str, Any] = {}
    created_at: datetime
    updated_at: datetime
```

### 2. Document Models

#### Document Model
```python
class Document(BaseModel):
    id: str
    user_id: str
    data_source_id: Optional[str] = None
    title: Optional[str] = None
    content: Optional[str] = None
    content_hash: Optional[str] = None
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    source_type: Optional[str] = None
    source_id: Optional[str] = None
    author: Optional[str] = None
    created_at: Optional[datetime] = None
    modified_at: Optional[datetime] = None
    indexed_at: datetime
    is_deleted: bool = False
    quality_score: float = 0.0
    metadata: Dict[str, Any] = {}
    tags: List[str] = []
    category: Optional[str] = None
    language: str = "en"

class DocumentCreate(BaseModel):
    title: Optional[str] = None
    content: str
    file_path: Optional[str] = None
    mime_type: Optional[str] = None
    source_type: Optional[str] = None
    source_id: Optional[str] = None
    author: Optional[str] = None
    created_at: Optional[datetime] = None
    modified_at: Optional[datetime] = None
    metadata: Dict[str, Any] = {}
    tags: List[str] = []
    category: Optional[str] = None

class DocumentUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    category: Optional[str] = None
    is_deleted: Optional[bool] = None
```

#### Document Entity Model
```python
class EntityType(str, Enum):
    PERSON = "person"
    ORGANIZATION = "organization"
    LOCATION = "location"
    DATE = "date"
    EMAIL = "email"
    PHONE = "phone"
    URL = "url"
    MONEY = "money"

class DocumentEntity(BaseModel):
    id: str
    document_id: str
    entity_type: EntityType
    entity_value: str
    confidence_score: float = 0.0
    start_position: Optional[int] = None
    end_position: Optional[int] = None
    context: Optional[str] = None
    created_at: datetime
```

### 3. Search Models

#### Search Request/Response
```python
class SearchRequest(BaseModel):
    query: str
    limit: int = 10
    threshold: float = 0.7
    filters: Optional[Dict[str, Any]] = None
    include_metadata: bool = True
    sort_by: str = "relevance"

class SearchResult(BaseModel):
    id: str
    content: str
    score: float
    metadata: Dict[str, Any]
    highlights: List[str] = []

class SearchResponse(BaseModel):
    results: List[SearchResult]
    total: int
    query_time_ms: int
    suggestions: List[str] = []
```

#### Search History Model
```python
class SearchHistory(BaseModel):
    id: str
    user_id: str
    query: str
    filters: Dict[str, Any] = {}
    results_count: int = 0
    response_time_ms: Optional[int] = None
    clicked_result_id: Optional[str] = None
    created_at: datetime
```

### 4. Chat Models

#### Conversation Models
```python
class Conversation(BaseModel):
    id: str
    user_id: str
    title: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    is_active: bool = True
    metadata: Dict[str, Any] = {}

class ChatMessage(BaseModel):
    id: str
    conversation_id: str
    message_type: str  # 'user', 'assistant', 'system'
    content: str
    metadata: Dict[str, Any] = {}
    llm_thoughts: Optional[str] = None
    created_at: datetime
    feedback_score: Optional[int] = None
    feedback_comment: Optional[str] = None

class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    include_sources: bool = True

class ChatResponse(BaseModel):
    message: str
    conversation_id: str
    sources: List[SearchResult] = []
    llm_thoughts: Optional[str] = None
    metadata: Dict[str, Any] = {}
```

### 5. Data Source Models

#### Data Source Models
```python
class DataSourceType(str, Enum):
    GOOGLE_DRIVE = "google_drive"
    GOOGLE_DOCS = "google_docs"
    GMAIL = "gmail"
    APPLE_NOTES = "apple_notes"
    APPLE_MESSAGES = "apple_messages"
    APPLE_CALENDAR = "apple_calendar"
    SPOTIFY = "spotify"

class SyncStatus(str, Enum):
    PENDING = "pending"
    SYNCING = "syncing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class DataSource(BaseModel):
    id: str
    user_id: str
    source_type: DataSourceType
    source_name: str
    connection_config: Dict[str, Any]
    is_active: bool = True
    last_sync: Optional[datetime] = None
    sync_frequency: str = "daily"
    sync_status: SyncStatus = SyncStatus.PENDING
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

class DataSourceCreate(BaseModel):
    source_type: DataSourceType
    source_name: str
    connection_config: Dict[str, Any]
    sync_frequency: str = "daily"

class SyncLog(BaseModel):
    id: str
    data_source_id: str
    sync_type: str
    status: SyncStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    items_processed: int = 0
    items_created: int = 0
    items_updated: int = 0
    items_failed: int = 0
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = {}
```

## Database Optimization

### 1. Indexing Strategy

#### PostgreSQL Indexes
```sql
-- Composite indexes for common queries
CREATE INDEX idx_documents_user_category ON documents(user_id, category);
CREATE INDEX idx_documents_user_source ON documents(user_id, source_type);
CREATE INDEX idx_documents_user_created ON documents(user_id, created_at DESC);

-- Partial indexes for better performance
CREATE INDEX idx_active_documents ON documents(user_id, indexed_at) WHERE is_deleted = false;
CREATE INDEX idx_recent_searches ON search_history(user_id, created_at) WHERE created_at > NOW() - INTERVAL '30 days';

-- Text search indexes
CREATE INDEX idx_documents_content_fts ON documents USING GIN(to_tsvector('english', content));
CREATE INDEX idx_documents_title_fts ON documents USING GIN(to_tsvector('english', title));
```

#### Pinecone Optimization
```python
# Optimized vector search configuration
search_config = {
    "top_k": 10,
    "include_metadata": True,
    "include_values": False,  # Don't return vectors to save bandwidth
    "filter": {
        "user_id": {"$eq": "user_id"},
        "quality_score": {"$gte": 0.5}
    }
}

# Batch processing for efficiency
batch_size = 100
def upsert_vectors(vectors: List[dict]):
    for i in range(0, len(vectors), batch_size):
        batch = vectors[i:i + batch_size]
        pinecone_index.upsert(vectors=batch)
```

### 2. Query Optimization

#### Optimized Queries
```sql
-- Efficient document search with pagination
SELECT d.id, d.title, d.content, d.created_at, d.category
FROM documents d
WHERE d.user_id = $1 
  AND d.is_deleted = false
  AND (to_tsvector('english', d.content || ' ' || COALESCE(d.title, '')) @@ plainto_tsquery('english', $2))
ORDER BY d.created_at DESC
LIMIT $3 OFFSET $4;

-- Analytics query optimization
SELECT 
    DATE_TRUNC('day', created_at) as date,
    COUNT(*) as searches,
    AVG(response_time_ms) as avg_response_time
FROM search_history 
WHERE user_id = $1 
  AND created_at >= NOW() - INTERVAL '30 days'
GROUP BY DATE_TRUNC('day', created_at)
ORDER BY date DESC;
```

### 3. Connection Pooling

#### Database Connection Configuration
```python
# SQLAlchemy connection pool configuration
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=30,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False  # Set to True for SQL debugging
)

# Connection pool monitoring
def get_pool_status():
    pool = engine.pool
    return {
        "size": pool.size(),
        "checked_in": pool.checkedin(),
        "checked_out": pool.checkedout(),
        "overflow": pool.overflow(),
        "invalid": pool.invalid()
    }
```

## Data Migration Strategy

### 1. Version Control

#### Alembic Migration Setup
```python
# alembic/env.py
from alembic import context
from sqlalchemy import engine_from_config, pool
from app.models import Base

def run_migrations_online():
    """Run migrations in 'online' mode."""
    configuration = context.config
    configuration.set_main_option('sqlalchemy.url', DATABASE_URL)
    
    connectable = engine_from_config(
        configuration.get_section(configuration.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=Base.metadata
        )

        with context.begin_transaction():
            context.run_migrations()
```

### 2. Migration Scripts

#### Example Migration
```python
# alembic/versions/001_add_user_preferences.py
"""Add user preferences table

Revision ID: 001
Revises: 
Create Date: 2024-01-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Create user_preferences table
    op.create_table('user_preferences',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('theme', sa.String(length=20), nullable=True),
        sa.Column('language', sa.String(length=10), nullable=True),
        sa.Column('notifications_enabled', sa.Boolean(), nullable=True),
        sa.Column('auto_sync_enabled', sa.Boolean(), nullable=True),
        sa.Column('search_preferences', sa.JSON(), nullable=True),
        sa.Column('privacy_settings', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

def downgrade():
    op.drop_table('user_preferences')
```

## Backup & Recovery

### 1. Backup Strategy

#### Automated Backup Script
```bash
#!/bin/bash
# backup_database.sh

# Configuration
DB_URL="postgresql://user:password@localhost:5432/personal_db"
BACKUP_DIR="/backups/postgresql"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p $BACKUP_DIR

# Database backup
pg_dump $DB_URL > $BACKUP_DIR/db_backup_$DATE.sql

# Compress backup
gzip $BACKUP_DIR/db_backup_$DATE.sql

# Upload to cloud storage
aws s3 cp $BACKUP_DIR/db_backup_$DATE.sql.gz s3://personal-db-backups/postgresql/

# Clean old backups (keep 30 days)
find $BACKUP_DIR -name "*.sql.gz" -mtime +30 -delete

echo "Backup completed: db_backup_$DATE.sql.gz"
```

### 2. Recovery Procedures

#### Database Restoration
```bash
#!/bin/bash
# restore_database.sh

BACKUP_FILE=$1
DB_URL="postgresql://user:password@localhost:5432/personal_db"

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <backup_file>"
    exit 1
fi

# Download backup from S3 if needed
if [[ $BACKUP_FILE == s3://* ]]; then
    aws s3 cp $BACKUP_FILE /tmp/backup.sql.gz
    BACKUP_FILE="/tmp/backup.sql.gz"
fi

# Extract backup
gunzip -c $BACKUP_FILE > /tmp/backup.sql

# Restore database
psql $DB_URL < /tmp/backup.sql

echo "Database restored from $BACKUP_FILE"
```

---

*This documentation is proprietary and confidential. All rights reserved.*
