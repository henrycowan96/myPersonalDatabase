import pytest
from unittest.mock import patch, Mock, AsyncMock
import asyncio
import base64
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from data_processor import process_and_ingest_data


class TestDataProcessor:
    """Test class for data processing functions"""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_process_google_calendar_data(
        self, mock_pinecone, mock_embedding_model, sample_calendar_event
    ):
        """Test processing Google Calendar events"""
        _, mock_index = mock_pinecone
        mock_embedding_model.return_value.encode.return_value = [0.1, 0.2, 0.3] * 128
        
        data = [sample_calendar_event]
        result = await process_and_ingest_data("test-user", "google_calendar", data, "test-index")
        
        # Verify embedding model was called
        mock_embedding_model.return_value.encode.assert_called_once()
        
        # Verify Pinecone upsert was called
        assert mock_index.upsert.call_count == 1
        
        # Check the vector structure
        call_args = mock_index.upsert.call_args
        vectors = call_args[1]['vectors'] if 'vectors' in call_args[1] else call_args[0][0]
        
        assert len(vectors) == 1
        vector = vectors[0]
        assert 'id' in vector
        assert 'values' in vector
        assert 'metadata' in vector
        
        metadata = vector['metadata']
        assert metadata['source'] == 'google_calendar'
        assert metadata['type'] == 'calendar_event'
        assert metadata['calendar'] == 'Work Calendar'
        assert metadata['event_title'] == 'Team Meeting'
        assert 'Team Meeting' in metadata['text']
        assert 'Conference Room A' in metadata['text']
        
        assert result == 1  # Success count

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_process_gmail_data(self, mock_pinecone, mock_embedding_model, sample_email):
        """Test processing Gmail messages"""
        _, mock_index = mock_pinecone
        mock_embedding_model.return_value.encode.return_value = [0.1, 0.2, 0.3] * 128
        
        data = [sample_email]
        result = await process_and_ingest_data("test-user", "gmail", data, "test-index")
        
        # Verify embedding model was called
        mock_embedding_model.return_value.encode.assert_called_once()
        
        # Verify Pinecone upsert was called
        assert mock_index.upsert.call_count == 1
        
        # Check the vector structure
        call_args = mock_index.upsert.call_args
        vectors = call_args[1]['vectors'] if 'vectors' in call_args[1] else call_args[0][0]
        
        assert len(vectors) == 1
        vector = vectors[0]
        metadata = vector['metadata']
        
        assert metadata['source'] == 'gmail'
        assert metadata['type'] == 'email'
        assert metadata['subject'] == 'Project Update'
        assert metadata['sender'] == 'john.doe@example.com'
        assert 'Hello World' in metadata['text']  # Decoded base64 content
        
        assert result == 1

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_process_google_drive_data(
        self, mock_pinecone, mock_embedding_model, sample_drive_file
    ):
        """Test processing Google Drive files"""
        _, mock_index = mock_pinecone
        mock_embedding_model.return_value.encode.return_value = [0.1, 0.2, 0.3] * 128
        
        data = [sample_drive_file]
        result = await process_and_ingest_data("test-user", "google_drive", data, "test-index")
        
        # Verify embedding model was called
        mock_embedding_model.return_value.encode.assert_called_once()
        
        # Verify Pinecone upsert was called
        assert mock_index.upsert.call_count == 1
        
        # Check the vector structure
        call_args = mock_index.upsert.call_args
        vectors = call_args[1]['vectors'] if 'vectors' in call_args[1] else call_args[0][0]
        
        assert len(vectors) == 1
        vector = vectors[0]
        metadata = vector['metadata']
        
        assert metadata['source'] == 'google_drive'
        assert metadata['type'] == 'file'
        assert metadata['title'] == 'Project Document'
        assert metadata['mime_type'] == 'application/pdf'
        assert 'This is the content of the PDF file' in metadata['text']
        
        assert result == 1

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_process_apple_notes_data(
        self, mock_pinecone, mock_embedding_model, sample_apple_note
    ):
        """Test processing Apple Notes"""
        _, mock_index = mock_pinecone
        mock_embedding_model.return_value.encode.return_value = [0.1, 0.2, 0.3] * 128
        
        data = [sample_apple_note]
        result = await process_and_ingest_data("test-user", "apple_notes", data, "test-index")
        
        # Verify embedding model was called
        mock_embedding_model.return_value.encode.assert_called_once()
        
        # Verify Pinecone upsert was called
        assert mock_index.upsert.call_count == 1
        
        # Check the vector structure
        call_args = mock_index.upsert.call_args
        vectors = call_args[1]['vectors'] if 'vectors' in call_args[1] else call_args[0][0]
        
        assert len(vectors) == 1
        vector = vectors[0]
        metadata = vector['metadata']
        
        assert metadata['source'] == 'apple_notes'
        assert metadata['type'] == 'note'
        assert metadata['note_name'] == 'Meeting Notes'
        assert 'Discussed project timeline' in metadata['text']
        
        assert result == 1

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_process_apple_calendar_data(
        self, mock_pinecone, mock_embedding_model, sample_calendar_event
    ):
        """Test processing Apple Calendar events"""
        _, mock_index = mock_pinecone
        mock_embedding_model.return_value.encode.return_value = [0.1, 0.2, 0.3] * 128
        
        # Convert to Apple Calendar format
        apple_event = {
            "calendar": "Work Calendar",
            "summary": "Team Meeting",
            "location": "Conference Room A",
            "notes": "Weekly team sync",
            "start_date": "2024-01-15T10:00:00Z",
            "end_date": "2024-01-15T11:00:00Z"
        }
        
        data = [apple_event]
        result = await process_and_ingest_data("test-user", "apple_calendar", data, "test-index")
        
        # Verify embedding model was called
        mock_embedding_model.return_value.encode.assert_called_once()
        
        # Verify Pinecone upsert was called
        assert mock_index.upsert.call_count == 1
        
        # Check the vector structure
        call_args = mock_index.upsert.call_args
        vectors = call_args[1]['vectors'] if 'vectors' in call_args[1] else call_args[0][0]
        
        assert len(vectors) == 1
        vector = vectors[0]
        metadata = vector['metadata']
        
        assert metadata['source'] == 'apple_calendar'
        assert metadata['type'] == 'calendar_event'
        assert metadata['calendar'] == 'Work Calendar'
        assert metadata['event_title'] == 'Team Meeting'
        
        assert result == 1

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_process_apple_music_data(
        self, mock_pinecone, mock_embedding_model, sample_apple_music_data
    ):
        """Test processing Apple Music data"""
        _, mock_index = mock_pinecone
        mock_embedding_model.return_value.encode.return_value = [0.1, 0.2, 0.3] * 128
        
        data = sample_apple_music_data
        result = await process_and_ingest_data("test-user", "apple_music", data, "test-index")
        
        # Should process songs, albums, and artists
        total_items = (
            len(data["results"]["songs"]["data"]) +
            len(data["results"]["albums"]["data"]) +
            len(data["results"]["artists"]["data"])
        )
        
        # Verify embedding model was called correct number of times
        assert mock_embedding_model.return_value.encode.call_count == total_items
        
        # Verify Pinecone upsert was called for each item
        assert mock_index.upsert.call_count == total_items
        
        assert result == total_items

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_content_truncation(self, mock_pinecone, mock_embedding_model):
        """Test that long content is properly truncated"""
        _, mock_index = mock_pinecone
        mock_embedding_model.return_value.encode.return_value = [0.1, 0.2, 0.3] * 128
        
        # Create a note with very long content
        long_note = {
            "name": "Long Note",
            "body": "x" * 5000,  # Very long content
            "created": "2024-01-15T07:00:00Z",
            "modified": "2024-01-15T08:00:00Z"
        }
        
        data = [long_note]
        await process_and_ingest_data("test-user", "apple_notes", data, "test-index")
        
        # Check that content was truncated
        call_args = mock_index.upsert.call_args
        vectors = call_args[1]['vectors'] if 'vectors' in call_args[1] else call_args[0][0]
        
        vector = vectors[0]
        text = vector['metadata']['text']
        assert len(text) < 5000  # Should be truncated
        assert "truncated" in text  # Should contain truncation indicator

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_error_handling_in_upsert(self, mock_pinecone, mock_embedding_model):
        """Test error handling when Pinecone upsert fails"""
        _, mock_index = mock_pinecone
        mock_embedding_model.return_value.encode.return_value = [0.1, 0.2, 0.3] * 128
        
        # Make upsert fail
        mock_index.upsert.side_effect = Exception("Pinecone error")
        
        note = {
            "name": "Test Note",
            "body": "Test content",
            "created": "2024-01-15T07:00:00Z",
            "modified": "2024-01-15T08:00:00Z"
        }
        
        data = [note]
        result = await process_and_ingest_data("test-user", "apple_notes", data, "test-index")
        
        # Should return 0 due to error
        assert result == 0

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_empty_data_handling(self, mock_pinecone, mock_embedding_model):
        """Test handling of empty data arrays"""
        data = []
        result = await process_and_ingest_data("test-user", "apple_notes", data, "test-index")
        
        # Should return 0 for empty data
        assert result == 0
        
        # Embedding model should not be called
        mock_embedding_model.return_value.encode.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_missing_optional_fields(
        self, mock_pinecone, mock_embedding_model
    ):
        """Test handling of missing optional fields in data"""
        _, mock_index = mock_pinecone
        mock_embedding_model.return_value.encode.return_value = [0.1, 0.2, 0.3] * 128
        
        # Note with missing optional fields
        minimal_note = {
            "name": "Minimal Note"
            # Missing body, created, modified
        }
        
        data = [minimal_note]
        result = await process_and_ingest_data("test-user", "apple_notes", data, "test-index")
        
        # Should still process successfully
        assert result == 1
        
        # Check the vector structure
        call_args = mock_index.upsert.call_args
        vectors = call_args[1]['vectors'] if 'vectors' in call_args[1] else call_args[0][0]
        
        vector = vectors[0]
        metadata = vector['metadata']
        
        assert metadata['note_name'] == "Minimal Note"
        assert metadata['created_date'] == ''
        assert metadata['modified_date'] == ''

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_batch_processing_progress(
        self, mock_pinecone, mock_embedding_model
    ):
        """Test that batch processing shows progress for large datasets"""
        _, mock_index = mock_pinecone
        mock_embedding_model.return_value.encode.return_value = [0.1, 0.2, 0.3] * 128
        
        # Create 25 calendar events to test progress reporting
        events = []
        for i in range(25):
            event = {
                "summary": f"Event {i}",
                "start": {"dateTime": "2024-01-15T10:00:00Z"},
                "end": {"dateTime": "2024-01-15T11:00:00Z"},
                "calendar": "Work Calendar"
            }
            events.append(event)
        
        result = await process_and_ingest_data("test-user", "google_calendar", events, "test-index")
        
        # Should process all events
        assert result == 25
        assert mock_embedding_model.return_value.encode.call_count == 25
        assert mock_index.upsert.call_count == 25
