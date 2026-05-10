import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock, AsyncMock
import json
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from api import app
from models import QueryRequest, QueryResponse


class TestAPIClientIntegration:
    """Integration tests for API-client communication"""

    @pytest.fixture
    def client(self):
        """Create test client for FastAPI app"""
        return TestClient(app)

    @pytest.mark.integration
    def test_query_endpoint_success(self, client, mock_pinecone, mock_embedding_model, mock_supabase):
        """Test successful query endpoint with mocked services"""
        _, mock_index = mock_pinecone
        mock_embedding_model.return_value.encode.return_value = [0.1, 0.2, 0.3] * 128
        
        # Mock Pinecone query response
        mock_index.query.return_value = {
            "matches": [
                {
                    "id": "doc1",
                    "score": 0.9,
                    "metadata": {
                        "text": "Meeting notes from yesterday",
                        "source": "apple_notes",
                        "type": "note"
                    }
                },
                {
                    "id": "doc2", 
                    "score": 0.8,
                    "metadata": {
                        "text": "Calendar event for team meeting",
                        "source": "google_calendar",
                        "type": "calendar_event"
                    }
                }
            ]
        }

        query_request = {
            "question": "What meetings did I have yesterday?",
            "user_id": "test-user-123"
        }

        response = client.post("/query", json=query_request)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "answer" in data
        assert "sources" in data
        assert len(data["sources"]) == 2
        assert data["sources"][0]["score"] == 0.9
        assert data["sources"][1]["score"] == 0.8

    @pytest.mark.integration
    def test_query_endpoint_no_user_id(self, client, mock_pinecone, mock_embedding_model):
        """Test query endpoint without user_id uses default index"""
        _, mock_index = mock_pinecone
        mock_embedding_model.return_value.encode.return_value = [0.1, 0.2, 0.3] * 128
        
        mock_index.query.return_value = {
            "matches": [
                {
                    "id": "doc1",
                    "score": 0.9,
                    "metadata": {"text": "Test document", "source": "test"}
                }
            ]
        }

        query_request = {
            "question": "Test question"
        }

        response = client.post("/query", json=query_request)
        
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert "sources" in data

    @pytest.mark.integration
    def test_query_endpoint_services_not_initialized(self, client):
        """Test query endpoint when services are not initialized"""
        with patch('app.utils.embedding_model', None):
            query_request = {
                "question": "Test question",
                "user_id": "test-user"
            }

            response = client.post("/query", json=query_request)
            
            assert response.status_code == 503
            assert "Services not initialized" in response.json()["detail"]

    @pytest.mark.integration
    def test_query_endpoint_invalid_request(self, client):
        """Test query endpoint with invalid request data"""
        invalid_request = {
            "invalid_field": "test"
        }

        response = client.post("/query", json=invalid_request)
        
        assert response.status_code == 422  # Validation error

    @pytest.mark.integration
    def test_health_check_with_dependencies(self, client):
        """Test health check endpoint with all dependencies"""
        with patch('app.utils.pinecone_index', Mock()), \
             patch('app.utils.embedding_model', Mock()), \
             patch('app.utils.llm', Mock()), \
             patch('app.utils.supabase', Mock()):
            
            response = client.get("/health")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["pinecone_connected"] is True
            assert data["embedding_model_loaded"] is True
            assert data["openrouter_loaded"] is True
            assert data["supabase_connected"] is True

    @pytest.mark.integration
    def test_health_check_missing_dependencies(self, client):
        """Test health check endpoint with missing dependencies"""
        with patch('app.utils.pinecone_index', None), \
             patch('app.utils.embedding_model', None), \
             patch('app.utils.llm', None), \
             patch('app.utils.supabase', None):
            
            response = client.get("/health")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["pinecone_connected"] is False
            assert data["embedding_model_loaded"] is False
            assert data["openrouter_loaded"] is False
            assert data["supabase_connected"] is False

    @pytest.mark.integration
    def test_cors_headers_integration(self, client):
        """Test CORS headers are properly set"""
        response = client.options("/")
        
        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers
        assert "access-control-allow-methods" in response.headers
        assert "access-control-allow-headers" in response.headers

    @pytest.mark.integration
    @patch('app.utils.supabase')
    def test_user_specific_index_retrieval(self, mock_supabase_client, client, mock_pinecone, mock_embedding_model):
        """Test that user-specific Pinecone indexes are retrieved correctly"""
        _, mock_index = mock_pinecone
        mock_embedding_model.return_value.encode.return_value = [0.1, 0.2, 0.3] * 128
        
        # Mock Supabase response for user settings
        mock_table = Mock()
        mock_table.select.return_value.eq.return_value.execute.return_value = {
            "data": [{"pinecone_index": "user-specific-index"}],
            "error": None
        }
        mock_supabase_client.table.return_value = mock_table
        
        mock_index.query.return_value = {
            "matches": []
        }

        query_request = {
            "question": "Test question",
            "user_id": "test-user-123"
        }

        response = client.post("/query", json=query_request)
        
        assert response.status_code == 200
        # Verify Supabase was called with correct user_id
        mock_supabase_client.table.assert_called_with("user_settings")
        mock_table.select.assert_called_with("*")
        mock_table.eq.assert_called_with("user_id", "test-user-123")

    @pytest.mark.integration
    def test_concurrent_requests_handling(self, client, mock_pinecone, mock_embedding_model):
        """Test that the API handles concurrent requests correctly"""
        import threading
        import time
        
        _, mock_index = mock_pinecone
        mock_embedding_model.return_value.encode.return_value = [0.1, 0.2, 0.3] * 128
        
        mock_index.query.return_value = {
            "matches": [{"id": "doc1", "score": 0.9, "metadata": {"text": "Test"}}]
        }

        results = []
        errors = []

        def make_request():
            try:
                response = client.post("/query", json={"question": "Test question"})
                results.append(response.status_code)
            except Exception as e:
                errors.append(str(e))

        # Create multiple concurrent requests
        threads = []
        for i in range(5):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify all requests succeeded
        assert len(results) == 5
        assert all(status == 200 for status in results)
        assert len(errors) == 0

    @pytest.mark.integration
    def test_large_query_handling(self, client, mock_pinecone, mock_embedding_model):
        """Test handling of large queries"""
        _, mock_index = mock_pinecone
        mock_embedding_model.return_value.encode.return_value = [0.1, 0.2, 0.3] * 128
        
        # Mock a large response
        large_matches = []
        for i in range(50):
            large_matches.append({
                "id": f"doc{i}",
                "score": 0.9 - (i * 0.01),
                "metadata": {
                    "text": f"Document content {i} " * 100,  # Large text
                    "source": "test",
                    "type": "document"
                }
            })
        
        mock_index.query.return_value = {"matches": large_matches}

        query_request = {
            "question": "What is in all my documents?",
            "user_id": "test-user"
        }

        response = client.post("/query", json=query_request)
        
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert "sources" in data
        assert len(data["sources"]) == 50

    @pytest.mark.integration
    def test_error_propagation_from_services(self, client, mock_pinecone, mock_embedding_model):
        """Test that errors from external services are properly propagated"""
        _, mock_index = mock_pinecone
        mock_embedding_model.return_value.encode.return_value = [0.1, 0.2, 0.3] * 128
        
        # Mock Pinecone to raise an exception
        mock_index.query.side_effect = Exception("Pinecone connection failed")

        query_request = {
            "question": "Test question",
            "user_id": "test-user"
        }

        response = client.post("/query", json=query_request)
        
        assert response.status_code == 500

    @pytest.mark.integration
    def test_request_timeout_handling(self, client, mock_pinecone, mock_embedding_model):
        """Test handling of request timeouts"""
        import time
        
        _, mock_index = mock_pinecone
        mock_embedding_model.return_value.encode.return_value = [0.1, 0.2, 0.3] * 128
        
        # Mock a slow response
        def slow_query(*args, **kwargs):
            time.sleep(2)  # Simulate slow response
            return {"matches": []}
        
        mock_index.query.side_effect = slow_query

        query_request = {
            "question": "Test question",
            "user_id": "test-user"
        }

        start_time = time.time()
        response = client.post("/query", json=query_request, timeout=5.0)
        end_time = time.time()

        # Should complete within reasonable time
        assert end_time - start_time < 10.0
        assert response.status_code == 200

    @pytest.mark.integration
    def test_request_response_format_validation(self, client, mock_pinecone, mock_embedding_model):
        """Test that request and response formats are properly validated"""
        _, mock_index = mock_pinecone
        mock_embedding_model.return_value.encode.return_value = [0.1, 0.2, 0.3] * 128
        
        mock_index.query.return_value = {
            "matches": [
                {
                    "id": "doc1",
                    "score": 0.9,
                    "metadata": {"text": "Test", "source": "test", "type": "document"}
                }
            ]
        }

        # Test valid request
        valid_request = {
            "question": "Test question",
            "user_id": "test-user"
        }
        response = client.post("/query", json=valid_request)
        assert response.status_code == 200

        # Test missing required field
        invalid_request = {
            "user_id": "test-user"
            # Missing "question"
        }
        response = client.post("/query", json=invalid_request)
        assert response.status_code == 422

        # Test invalid JSON
        response = client.post("/query", data="invalid json", headers={"Content-Type": "application/json"})
        assert response.status_code == 422
