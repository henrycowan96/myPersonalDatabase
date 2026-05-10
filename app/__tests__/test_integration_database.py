import pytest
from unittest.mock import patch, Mock, AsyncMock
import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from data_processor import process_and_ingest_data
import utils


class TestDatabaseIntegration:
    """Integration tests for database operations with mocked services"""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_full_ingestion_workflow(self, mock_pinecone, mock_supabase, mock_embedding_model):
        """Test complete data ingestion workflow from API to database"""
        _, mock_index = mock_pinecone
        mock_supabase_client, mock_table = mock_supabase
        mock_embedding_model.return_value.encode.return_value = [0.1, 0.2, 0.3] * 128
        
        # Sample data mimicking real API response
        calendar_data = [
            {
                "summary": "Team Meeting",
                "start": {"dateTime": "2024-01-15T10:00:00Z"},
                "end": {"dateTime": "2024-01-15T11:00:00Z"},
                "location": "Conference Room A",
                "description": "Weekly team sync",
                "calendar": "Work Calendar"
            }
        ]

        # Mock user settings retrieval
        mock_table.select.return_value.eq.return_value.execute.return_value = {
            "data": [{"pinecone_index": "user-test-index"}],
            "error": None
        }

        result = await process_and_ingest_data("test-user", "google_calendar", calendar_data, "user-test-index")
        
        # Verify data was processed and stored
        assert result == 1
        mock_embedding_model.return_value.encode.assert_called_once()
        mock_index.upsert.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_multiple_service_ingestion(self, mock_pinecone, mock_supabase, mock_embedding_model):
        """Test ingestion of data from multiple services"""
        _, mock_index = mock_pinecone
        mock_supabase_client, mock_table = mock_supabase
        mock_embedding_model.return_value.encode.return_value = [0.1, 0.2, 0.3] * 128
        
        services_data = {
            "google_calendar": [
                {"summary": "Meeting", "start": {"dateTime": "2024-01-15T10:00:00Z"}, "calendar": "Work"}
            ],
            "gmail": [
                {"subject": "Email", "sender": "test@example.com", "payload": {"body": {"data": "SGVsbG8="}}}
            ],
            "apple_notes": [
                {"name": "Note", "body": "Note content", "created": "2024-01-15T10:00:00Z"}
            ]
        }

        total_processed = 0
        for service, data in services_data.items():
            result = await process_and_ingest_data("test-user", service, data, "test-index")
            total_processed += result

        assert total_processed == 3
        assert mock_embedding_model.return_value.encode.call_count == 3
        assert mock_index.upsert.call_count == 3

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_user_isolation(self, mock_pinecone, mock_supabase, mock_embedding_model):
        """Test that user data is properly isolated"""
        _, mock_index = mock_pinecone
        mock_supabase_client, mock_table = mock_supabase
        mock_embedding_model.return_value.encode.return_value = [0.1, 0.2, 0.3] * 128
        
        # Mock different users with different indexes
        def mock_supabase_response(table_name):
            if table_name == "user_settings":
                return {
                    "data": [{"pinecone_index": f"user-{table_name}-index"}],
                    "error": None
                }
            return {"data": [], "error": None}

        mock_table.select.return_value.eq.return_value.execute.side_effect = lambda: mock_supabase_response("user_settings")

        # Process data for different users
        user1_data = [{"summary": "User1 Meeting", "calendar": "Work"}]
        user2_data = [{"summary": "User2 Meeting", "calendar": "Work"}]

        await process_and_ingest_data("user1", "google_calendar", user1_data, "user1-index")
        await process_and_ingest_data("user2", "google_calendar", user2_data, "user2-index")

        # Verify both users' data was processed
        assert mock_index.upsert.call_count == 2

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_database_connection_recovery(self, mock_pinecone, mock_supabase, mock_embedding_model):
        """Test database connection recovery after failure"""
        _, mock_index = mock_pinecone
        mock_supabase_client, mock_table = mock_supabase
        mock_embedding_model.return_value.encode.return_value = [0.1, 0.2, 0.3] * 128
        
        # Simulate connection failure then recovery
        call_count = 0
        def failing_upsert(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Connection failed")
            return {"upserted_count": 1}
        
        mock_index.upsert.side_effect = failing_upsert

        calendar_data = [
            {"summary": "Meeting", "start": {"dateTime": "2024-01-15T10:00:00Z"}, "calendar": "Work"}
        ]

        result = await process_and_ingest_data("test-user", "google_calendar", calendar_data, "test-index")
        
        # Should handle the failure gracefully
        assert result == 0  # First call failed

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_large_batch_processing(self, mock_pinecone, mock_supabase, mock_embedding_model):
        """Test processing of large data batches"""
        _, mock_index = mock_pinecone
        mock_supabase_client, mock_table = mock_supabase
        mock_embedding_model.return_value.encode.return_value = [0.1, 0.2, 0.3] * 128
        
        # Create large dataset
        large_dataset = []
        for i in range(100):
            large_dataset.append({
                "summary": f"Meeting {i}",
                "start": {"dateTime": f"2024-01-{(i % 28) + 1:02d}T10:00:00Z"},
                "calendar": "Work Calendar"
            })

        result = await process_and_ingest_data("test-user", "google_calendar", large_dataset, "test-index")
        
        assert result == 100
        assert mock_embedding_model.return_value.encode.call_count == 100
        assert mock_index.upsert.call_count == 100

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_concurrent_ingestion(self, mock_pinecone, mock_supabase, mock_embedding_model):
        """Test concurrent data ingestion from multiple services"""
        _, mock_index = mock_pinecone
        mock_supabase_client, mock_table = mock_supabase
        mock_embedding_model.return_value.encode.return_value = [0.1, 0.2, 0.3] * 128
        
        # Prepare data for concurrent processing
        tasks = []
        for i in range(5):
            data = [{"summary": f"Meeting {i}", "calendar": "Work"}]
            task = process_and_ingest_data(f"user{i}", "google_calendar", data, f"index{i}")
            tasks.append(task)

        # Run all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify all tasks completed successfully
        successful_results = [r for r in results if not isinstance(r, Exception)]
        assert len(successful_results) == 5
        assert all(r == 1 for r in successful_results)

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_data_integrity_validation(self, mock_pinecone, mock_supabase, mock_embedding_model):
        """Test that data integrity is maintained during ingestion"""
        _, mock_index = mock_pinecone
        mock_supabase_client, mock_table = mock_supabase
        mock_embedding_model.return_value.encode.return_value = [0.1, 0.2, 0.3] * 128
        
        # Test data with special characters and unicode
        special_data = [
            {
                "summary": "Meeting with émojis 🎉 and spëcial chars",
                "description": "Content with quotes ' and \" and newlines\nand tabs\t",
                "start": {"dateTime": "2024-01-15T10:00:00Z"},
                "calendar": "Wörk Calëndar"
            }
        ]

        result = await process_and_ingest_data("test-user", "google_calendar", special_data, "test-index")
        
        assert result == 1
        
        # Verify the data was stored correctly
        call_args = mock_index.upsert.call_args
        vectors = call_args[1]['vectors'] if 'vectors' in call_args[1] else call_args[0][0]
        
        stored_text = vectors[0]['metadata']['text']
        assert "Meeting with émojis 🎉" in stored_text
        assert "spëcial chars" in stored_text
        assert "Wörk Calëndar" in stored_text

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_error_handling_and_rollback(self, mock_pinecone, mock_supabase, mock_embedding_model):
        """Test error handling and rollback scenarios"""
        _, mock_index = mock_pinecone
        mock_supabase_client, mock_table = mock_supabase
        mock_embedding_model.return_value.encode.return_value = [0.1, 0.2, 0.3] * 128
        
        # Simulate partial failure
        failure_count = 0
        def failing_upsert(*args, **kwargs):
            nonlocal failure_count
            failure_count += 1
            if failure_count <= 2:  # First 2 calls fail
                raise Exception(f"Upsert failure {failure_count}")
            return {"upserted_count": 1}
        
        mock_index.upsert.side_effect = failing_upsert

        data = [
            {"summary": f"Meeting {i}", "calendar": "Work"}
            for i in range(5)
        ]

        result = await process_and_ingest_data("test-user", "google_calendar", data, "test-index")
        
        # Should handle partial failures gracefully
        assert result == 3  # Only 3 out of 5 succeeded
        assert mock_index.upsert.call_count == 5

    @pytest.mark.asyncio
    @pytest.mark.integration
    @patch('utils.supabase', None)
    async def test_operation_without_database(self, mock_pinecone, mock_embedding_model):
        """Test operations when database is not available"""
        _, mock_index = mock_pinecone
        mock_embedding_model.return_value.encode.return_value = [0.1, 0.2, 0.3] * 128
        
        data = [{"summary": "Meeting", "calendar": "Work"}]

        # Should still work with Pinecone even without Supabase
        result = await process_and_ingest_data("test-user", "google_calendar", data, "test-index")
        
        assert result == 1
        mock_index.upsert.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_metadata_preservation(self, mock_pinecone, mock_supabase, mock_embedding_model):
        """Test that metadata is properly preserved during ingestion"""
        _, mock_index = mock_pinecone
        mock_supabase_client, mock_table = mock_supabase
        mock_embedding_model.return_value.encode.return_value = [0.1, 0.2, 0.3] * 128
        
        # Complex data with various metadata fields
        complex_data = [
            {
                "summary": "Important Meeting",
                "description": "Quarterly review",
                "location": "Office Building A, Floor 5, Room 501",
                "start": {"dateTime": "2024-01-15T10:00:00Z"},
                "end": {"dateTime": "2024-01-15T12:00:00Z"},
                "calendar": "Executive Calendar",
                "attendees": ["john@example.com", "jane@example.com"],
                "priority": "high",
                "tags": ["business", "quarterly", "review"]
            }
        ]

        result = await process_and_ingest_data("test-user", "google_calendar", complex_data, "test-index")
        
        assert result == 1
        
        # Verify metadata preservation
        call_args = mock_index.upsert.call_args
        vectors = call_args[1]['vectors'] if 'vectors' in call_args[1] else call_args[0][0]
        
        metadata = vectors[0]['metadata']
        assert metadata['source'] == 'google_calendar'
        assert metadata['type'] == 'calendar_event'
        assert metadata['calendar'] == 'Executive Calendar'
        assert metadata['event_title'] == 'Important Meeting'
        assert 'Important Meeting' in metadata['text']
        assert 'Quarterly review' in metadata['text']
        assert 'Office Building A' in metadata['text']

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_performance_monitoring(self, mock_pinecone, mock_supabase, mock_embedding_model):
        """Test performance monitoring during ingestion"""
        import time
        
        _, mock_index = mock_pinecone
        mock_supabase_client, mock_table = mock_supabase
        mock_embedding_model.return_value.encode.return_value = [0.1, 0.2, 0.3] * 128
        
        # Measure performance
        start_time = time.time()
        
        data = [
            {"summary": f"Meeting {i}", "calendar": "Work"}
            for i in range(50)
        ]

        result = await process_and_ingest_data("test-user", "google_calendar", data, "test-index")
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        assert result == 50
        assert processing_time < 30.0  # Should complete within 30 seconds
        assert mock_embedding_model.return_value.encode.call_count == 50
        assert mock_index.upsert.call_count == 50
