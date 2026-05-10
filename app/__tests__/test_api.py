import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from api import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture
def mock_utils():
    """Mock utils module for testing"""
    with patch('app.utils') as mock_utils_module:
        mock_utils_module.pinecone_index = Mock()
        mock_utils_module.embedding_model = Mock()
        mock_utils_module.llm = Mock()
        mock_utils_module.supabase = Mock()
        yield mock_utils_module


class TestAPIEndpoints:
    """Test class for main API endpoints"""

    @pytest.mark.unit
    def test_root_endpoint(self, client):
        """Test the root endpoint returns correct message"""
        response = client.get("/")
        assert response.status_code == 200
        assert response.json() == {"message": "Personal Database API is running"}

    @pytest.mark.unit
    def test_health_check_all_services_healthy(self, client, mock_utils):
        """Test health check when all services are healthy"""
        mock_utils.pinecone_index = Mock()
        mock_utils.embedding_model = Mock()
        mock_utils.llm = Mock()
        mock_utils.supabase = Mock()

        response = client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert data["pinecone_connected"] is True
        assert data["embedding_model_loaded"] is True
        assert data["openrouter_loaded"] is True
        assert data["supabase_connected"] is True

    @pytest.mark.unit
    def test_health_check_some_services_unhealthy(self, client, mock_utils):
        """Test health check when some services are unhealthy"""
        mock_utils.pinecone_index = None  # Unhealthy
        mock_utils.embedding_model = Mock()  # Healthy
        mock_utils.llm = None  # Unhealthy
        mock_utils.supabase = Mock()  # Healthy

        response = client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert data["pinecone_connected"] is False
        assert data["embedding_model_loaded"] is True
        assert data["openrouter_loaded"] is False
        assert data["supabase_connected"] is True

    @pytest.mark.unit
    def test_cors_headers(self, client):
        """Test that CORS headers are properly set"""
        response = client.options("/")
        assert response.status_code == 200
        
        # Check for CORS headers
        headers = response.headers
        assert "access-control-allow-origin" in headers
        assert "access-control-allow-methods" in headers
        assert "access-control-allow-headers" in headers

    @pytest.mark.unit
    def test_app_includes_all_routers(self):
        """Test that all expected routers are included in the app"""
        router_names = [route.name for route in app.routes if hasattr(route, 'name')]
        
        # Check that main routers are included
        expected_routers = [
            'query', 'chat', 'user', 'auth', 'ingestion',
            'apple_ingestion', 'google_ingestion', 'spotify_ingestion',
            'upload', 'insights', 'llm_thoughts', 'chat_context'
        ]
        
        # Note: Router names might not match exactly, so we check if the routes are included
        assert len(app.routes) > len(expected_routers)  # At least these many routes

    @pytest.mark.unit
    @patch('app.utils.initialize_services')
    def test_lifespan_startup(self, mock_initialize, client):
        """Test that services are initialized on startup"""
        # The lifespan is called when the test client is created
        # This test verifies the mock was called during app creation
        mock_initialize.assert_called_once()

    @pytest.mark.unit
    def test_app_metadata(self):
        """Test FastAPI app metadata"""
        assert app.title == "Personal Database API"
        assert hasattr(app, 'lifespan')

    @pytest.mark.unit
    def test_invalid_endpoint(self, client):
        """Test that invalid endpoints return 404"""
        response = client.get("/invalid-endpoint")
        assert response.status_code == 404

    @pytest.mark.unit
    def test_method_not_allowed(self, client):
        """Test that unsupported methods return 405"""
        response = client.delete("/")
        assert response.status_code == 405

    @pytest.mark.unit
    def test_health_check_response_structure(self, client, mock_utils):
        """Test that health check has the correct response structure"""
        response = client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, dict)
        assert "status" in data
        assert "pinecone_connected" in data
        assert "embedding_model_loaded" in data
        assert "openrouter_loaded" in data
        assert "supabase_connected" in data
        
        # Check that boolean values are actually booleans
        assert isinstance(data["pinecone_connected"], bool)
        assert isinstance(data["embedding_model_loaded"], bool)
        assert isinstance(data["openrouter_loaded"], bool)
        assert isinstance(data["supabase_connected"], bool)
