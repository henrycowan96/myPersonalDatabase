import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

# Mock environment variables for testing
os.environ["PINECONE_API_KEY"] = "test-pinecone-key"
os.environ["OPENAI_API_KEY"] = "test-openai-key"
os.environ["SUPABASE_URL"] = "https://test.supabase.co"
os.environ["SUPABASE_KEY"] = "test-supabase-key"


@pytest.fixture
def mock_pinecone():
    """Mock Pinecone client and index"""
    with patch('pinecone.Pinecone') as mock_pc:
        mock_index = Mock()
        mock_index.upsert = Mock(return_value={"upserted_count": 1})
        mock_index.query = Mock(return_value={
            "matches": [
                {
                    "id": "test-id",
                    "score": 0.9,
                    "metadata": {"text": "test text", "source": "test"}
                }
            ]
        })
        mock_pc.return_value.Index.return_value = mock_index
        yield mock_pc, mock_index


@pytest.fixture
def mock_supabase():
    """Mock Supabase client"""
    with patch('supabase.create_client') as mock_client:
        mock_table = Mock()
        mock_table.insert = Mock(return_value={"data": [{"id": "test-id"}], "error": None})
        mock_table.select = Mock(return_value=mock_table)
        mock_table.eq = Mock(return_value=mock_table)
        mock_table.execute = Mock(return_value={"data": [{"id": "test-id"}], "error": None})
        
        mock_client.return_value.table.return_value = mock_table
        yield mock_client, mock_table


@pytest.fixture
def mock_embedding_model():
    """Mock sentence transformer embedding model"""
    with patch('sentence_transformers.SentenceTransformer') as mock_model:
        mock_model.return_value.encode.return_value = [0.1, 0.2, 0.3] * 128  # Mock embedding
        yield mock_model


@pytest.fixture
def mock_openai():
    """Mock OpenAI client"""
    with patch('openai.OpenAI') as mock_client:
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="Test response"))]
        mock_client.return_value.chat.completions.create.return_value = mock_response
        yield mock_client


@pytest.fixture
def sample_calendar_event():
    """Sample Google Calendar event for testing"""
    return {
        "summary": "Team Meeting",
        "start": {"dateTime": "2024-01-15T10:00:00Z"},
        "end": {"dateTime": "2024-01-15T11:00:00Z"},
        "location": "Conference Room A",
        "description": "Weekly team sync",
        "calendar": "Work Calendar"
    }


@pytest.fixture
def sample_email():
    """Sample Gmail message for testing"""
    return {
        "subject": "Project Update",
        "sender": "john.doe@example.com",
        "date": "2024-01-15T09:00:00Z",
        "payload": {
            "headers": [],
            "body": {"data": "SGVsbG8gV29ybGQ="}  # Base64 encoded "Hello World"
        }
    }


@pytest.fixture
def sample_drive_file():
    """Sample Google Drive file for testing"""
    return {
        "name": "Project Document",
        "mime_type": "application/pdf",
        "content": "This is the content of the PDF file...",
        "modified_time": "2024-01-15T08:00:00Z"
    }


@pytest.fixture
def sample_apple_note():
    """Sample Apple Note for testing"""
    return {
        "name": "Meeting Notes",
        "body": "Discussed project timeline and deliverables...",
        "created": "2024-01-15T07:00:00Z",
        "modified": "2024-01-15T08:00:00Z"
    }


@pytest.fixture
def sample_apple_music_data():
    """Sample Apple Music data for testing"""
    return {
        "results": {
            "songs": {
                "data": [
                    {
                        "attributes": {
                            "name": "Test Song",
                            "artistName": "Test Artist",
                            "albumName": "Test Album",
                            "genreNames": ["Pop", "Rock"],
                            "durationInMillis": 180000
                        }
                    }
                ]
            },
            "albums": {
                "data": [
                    {
                        "attributes": {
                            "name": "Test Album",
                            "artistName": "Test Artist",
                            "genreNames": ["Pop"],
                            "releaseDate": "2024-01-01"
                        }
                    }
                ]
            },
            "artists": {
                "data": [
                    {
                        "attributes": {
                            "name": "Test Artist",
                            "genreNames": ["Pop", "Rock"]
                        }
                    }
                ]
            }
        }
    }


@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
