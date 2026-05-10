# Backend Architecture Documentation

## Overview

The Personal Database Mobile backend is a high-performance FastAPI application designed for scalability, security, and maintainability. It serves as the central hub for data ingestion, processing, and intelligent search capabilities.

## Architecture Principles

- **Microservice-Ready:** Modular design with clear separation of concerns
- **Async-First:** Non-blocking I/O for high concurrency
- **Security-First:** Authentication, authorization, and data validation
- **Scalable:** Stateless design with external state management
- **Observable:** Comprehensive logging and monitoring capabilities

## Core Components

### 1. FastAPI Application (`app/api.py`)

```python
# Main application entry point
- CORS middleware configuration
- Router registration
- Health check endpoints
- Service initialization
```

**Key Features:**
- Auto-generated OpenAPI documentation
- Request validation and serialization
- Async request handling
- Graceful shutdown handling

### 2. Router Architecture (`app/routes/`)

Each router represents a distinct business domain:

#### Core Routers
- **`query.py`** - Vector search and query processing
- **`chat.py`** - Conversational AI interactions
- **`auth.py`** - Authentication and authorization
- **`user.py`** - User management and preferences

#### Data Ingestion Routers
- **`ingestion.py`** - Generic document ingestion
- **`upload.py`** - File upload and processing
- **`apple_ingestion.py`** - Apple ecosystem data
- **`google_ingestion.py`** - Google services integration
- **`spotify_ingestion.py`** - Spotify data integration

#### Advanced Features
- **`insights.py`** - AI-powered insights generation
- **`llm_thoughts.py`** - LLM reasoning transparency
- **`chat_context.py`** - Conversation context management

### 3. Service Layer (`app/services/`)

Business logic abstraction layer:

```python
services/
├── apple_services.py    # Apple ecosystem integration
├── google_services.py   # Google services integration
└── __init__.py          # Service factory and configuration
```

**Design Patterns:**
- Repository pattern for data access
- Factory pattern for service instantiation
- Strategy pattern for multiple data sources

### 4. Data Processing (`app/processors/`)

Specialized processors for different data types:

```python
processors/
├── __init__.py          # Processor registry
├── text_processor.py    # Text document processing
├── email_processor.py   # Email parsing and analysis
└── calendar_processor.py # Calendar event processing
```

## API Design Patterns

### 1. RESTful Conventions

```
GET    /api/v1/query              # Search documents
POST   /api/v1/query              # Advanced query
GET    /api/v1/documents/{id}     # Get document
PUT    /api/v1/documents/{id}     # Update document
DELETE /api/v1/documents/{id}     # Delete document
```

### 2. Response Format

```python
# Standard response envelope
{
    "success": true,
    "data": {...},
    "message": "Operation completed",
    "timestamp": "2024-01-01T00:00:00Z",
    "request_id": "uuid"
}

# Error response
{
    "success": false,
    "error": {
        "code": "VALIDATION_ERROR",
        "message": "Invalid input parameters",
        "details": {...}
    },
    "timestamp": "2024-01-01T00:00:00Z",
    "request_id": "uuid"
}
```

### 3. Authentication & Authorization

```python
# JWT-based authentication
Authorization: Bearer <jwt_token>

# Role-based access control
- admin: Full system access
- user: Personal data access only
- readonly: Search-only access
```

## Key API Endpoints

### Search & Query

#### `GET /api/v1/query`
**Purpose:** Vector similarity search
**Parameters:**
- `q` (string): Search query
- `limit` (int): Maximum results (default: 10)
- `threshold` (float): Similarity threshold (default: 0.7)
- `filters` (object): Metadata filters

**Response:**
```json
{
  "results": [
    {
      "id": "doc_123",
      "content": "Document excerpt...",
      "score": 0.95,
      "metadata": {
        "source": "gmail",
        "date": "2024-01-01",
        "author": "user@example.com"
      }
    }
  ],
  "total": 1,
  "query_time_ms": 45
}
```

#### `POST /api/v1/chat`
**Purpose:** Conversational AI with context
**Request Body:**
```json
{
  "message": "What did I discuss with John last week?",
  "context": {
    "conversation_id": "uuid",
    "previous_messages": [...]
  }
}
```

### Data Ingestion

#### `POST /api/v1/ingest/file`
**Purpose:** Upload and process documents
**Content-Type:** `multipart/form-data`
**Fields:**
- `file`: Document file
- `metadata` (optional): JSON metadata
- `source`: Data source identifier

#### `POST /api/v1/ingest/batch`
**Purpose:** Batch document processing
**Request Body:**
```json
{
  "documents": [
    {
      "content": "Document text...",
      "metadata": {...}
    }
  ]
}
```

### User Management

#### `GET /api/v1/user/profile`
**Purpose:** Get user profile and settings
**Response:**
```json
{
  "id": "user_123",
  "email": "user@example.com",
  "settings": {
    "search_preferences": {...},
    "privacy_settings": {...}
  },
  "usage_stats": {
    "documents_count": 1500,
    "searches_today": 25,
    "storage_used_mb": 250
  }
}
```

## Data Flow Architecture

### 1. Request Processing Pipeline

```
Request → Authentication → Validation → Business Logic → 
Data Access → Response Formatting → Response
```

### 2. Search Pipeline

```
Query → Embedding Generation → Vector Search → 
Result Ranking → LLM Enhancement → Response
```

### 3. Ingestion Pipeline

```
File Upload → Format Detection → Content Extraction → 
Metadata Generation → Embedding → Vector Storage → Indexing
```

## Performance Optimizations

### 1. Caching Strategy
- **Redis:** Session storage and frequent queries
- **In-Memory:** Embedding model caching
- **CDN:** Static file serving

### 2. Database Optimizations
- **Connection Pooling:** Async database connections
- **Query Optimization:** Indexed searches
- **Batch Operations:** Bulk data processing

### 3. Async Processing
- **Background Tasks:** Heavy processing operations
- **Queue System:** Celery with Redis broker
- **Streaming:** Large file processing

## Security Implementation

### 1. Authentication
```python
# JWT token validation
async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
```

### 2. Input Validation
```python
# Pydantic models for validation
class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)
    limit: int = Field(default=10, ge=1, le=100)
    filters: Optional[Dict[str, Any]] = None
```

### 3. Rate Limiting
```python
# Redis-based rate limiting
@limiter.limit("100/minute")
async def search_endpoint(request: Request, query: str):
    # Implementation
```

## Error Handling

### 1. Exception Hierarchy
```python
class PersonalDatabaseException(Exception):
    """Base exception for all custom errors"""

class ValidationException(PersonalDatabaseException):
    """Input validation errors"""

class AuthenticationException(PersonalDatabaseException):
    """Authentication and authorization errors"""

class DataProcessingException(PersonalDatabaseException):
    """Data processing errors"""
```

### 2. Global Exception Handler
```python
@app.exception_handler(PersonalDatabaseException)
async def custom_exception_handler(request: Request, exc: PersonalDatabaseException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": exc.error_code,
                "message": str(exc)
            }
        }
    )
```

## Monitoring & Observability

### 1. Logging Strategy
```python
# Structured logging with correlation IDs
logger = logging.getLogger(__name__)
logger.info("Processing search query", extra={
    "request_id": request_id,
    "user_id": user_id,
    "query": query,
    "processing_time_ms": processing_time
})
```

### 2. Metrics Collection
- **Request latency:** Response time tracking
- **Error rates:** Exception monitoring
- **Resource usage:** Memory and CPU tracking
- **Business metrics:** Search success rates, user engagement

### 3. Health Checks
```python
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow(),
        "services": {
            "database": await check_database(),
            "vector_db": await check_vector_db(),
            "llm": await check_llm_service()
        }
    }
```

## Configuration Management

### 1. Environment Variables
```bash
# Database Configuration
DATABASE_URL=postgresql://user:pass@localhost/db
REDIS_URL=redis://localhost:6379

# External Services
PINECONE_API_KEY=your_key
OPENROUTER_API_KEY=your_key
SUPABASE_URL=your_url
SUPABASE_KEY=your_key

# Security
SECRET_KEY=your_secret_key
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

### 2. Configuration Classes
```python
class Settings(BaseSettings):
    database_url: str
    redis_url: str
    pinecone_api_key: str
    openrouter_api_key: str
    
    class Config:
        env_file = ".env"
```

## Testing Strategy

### 1. Unit Tests
- Business logic validation
- Service layer testing
- Utility function testing

### 2. Integration Tests
- API endpoint testing
- Database integration
- External service mocking

### 3. Performance Tests
- Load testing for search endpoints
- Stress testing for ingestion
- Memory usage profiling

## Deployment Considerations

### 1. Containerization
```dockerfile
FROM python:3.14-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "app.api:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 2. Orchestration
- **Kubernetes:** Container orchestration
- **Helm Charts:** Deployment configuration
- **Auto-scaling:** Horizontal pod autoscaling

### 3. CI/CD Pipeline
- **GitHub Actions:** Automated testing and deployment
- **Docker Registry:** Container image management
- **Rolling Updates:** Zero-downtime deployments

---

*This documentation is proprietary and confidential. All rights reserved.*
