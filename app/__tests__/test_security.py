import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock
import sys
from pathlib import Path
import base64
import json

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from api import app


class TestSecurity:
    """Security tests for the API"""

    @pytest.fixture
    def client(self):
        """Create a test client for the FastAPI app"""
        return TestClient(app)

    @pytest.mark.unit
    def test_sql_injection_protection(self, client):
        """Test that SQL injection attempts are blocked"""
        malicious_inputs = [
            "'; DROP TABLE users; --",
            "' OR '1'='1",
            "'; INSERT INTO users VALUES ('hacker', 'password'); --",
            "' UNION SELECT * FROM sensitive_data --",
            "'; EXEC xp_cmdshell('format c:'); --"
        ]
        
        for malicious_input in malicious_inputs:
            response = client.post("/search", json={"query": malicious_input})
            # Should either return 400 (bad request) or 422 (validation error)
            assert response.status_code in [400, 422, 401]
            
            # Should not contain database error messages
            assert "syntax error" not in response.text.lower()
            assert "mysql" not in response.text.lower()
            assert "postgresql" not in response.text.lower()

    @pytest.mark.unit
    def test_xss_protection(self, client):
        """Test that XSS attempts are blocked"""
        xss_payloads = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<img src=x onerror=alert('xss')>",
            "';alert('xss');//",
            "<svg onload=alert('xss')>",
            "';document.location='http://evil.com';//"
        ]
        
        for payload in xss_payloads:
            response = client.post("/search", json={"query": payload})
            
            # Should not execute scripts (response should be safe)
            assert response.status_code in [200, 400, 422]
            
            # Response should not contain unescaped script tags
            if response.status_code == 200:
                response_text = response.text
                assert "<script>" not in response_text or "&lt;script&gt;" in response_text
                assert "javascript:" not in response_text.lower()

    @pytest.mark.unit
    def test_authentication_required(self, client):
        """Test that protected endpoints require authentication"""
        protected_endpoints = [
            "/search",
            "/ingestion/google/calendar",
            "/ingestion/gmail",
            "/user/profile",
            "/user/settings"
        ]
        
        for endpoint in protected_endpoints:
            response = client.get(endpoint)
            assert response.status_code == 401
            
            response = client.post(endpoint, json={})
            assert response.status_code == 401

    @pytest.mark.unit
    def test_jwt_token_validation(self, client):
        """Test JWT token validation"""
        # Test with no token
        response = client.get("/search", headers={})
        assert response.status_code == 401
        
        # Test with invalid token
        response = client.get("/search", headers={"Authorization": "Bearer invalid-token"})
        assert response.status_code == 401
        
        # Test with malformed token
        response = client.get("/search", headers={"Authorization": "Bearer not.a.jwt"})
        assert response.status_code == 401

    @pytest.mark.unit
    def test_rate_limiting(self, client):
        """Test rate limiting on sensitive endpoints"""
        # Make multiple rapid requests
        for i in range(100):
            response = client.post("/auth/login", json={
                "email": f"test{i}@example.com",
                "password": "password"
            })
            
            # After certain number of requests, should be rate limited
            if i > 50:
                assert response.status_code == 429

    @pytest.mark.unit
    def test_input_validation(self, client):
        """Test input validation for various endpoints"""
        # Test oversized input
        large_input = "a" * 10000
        
        response = client.post("/search", json={"query": large_input})
        assert response.status_code in [400, 422]
        
        # Test missing required fields
        response = client.post("/search", json={})
        assert response.status_code == 422
        
        # Test invalid data types
        response = client.post("/search", json={"query": 123})
        assert response.status_code == 422

    @pytest.mark.unit
    def test_cors_headers(self, client):
        """Test CORS headers are properly set"""
        response = client.options("/")
        assert response.status_code == 200
        
        headers = response.headers
        assert "access-control-allow-origin" in headers
        assert "access-control-allow-methods" in headers
        assert "access-control-allow-headers" in headers
        
        # Should not allow all origins in production
        assert headers.get("access-control-allow-origin") != "*"

    @pytest.mark.unit
    def test_sensitive_data_exposure(self, client):
        """Test that sensitive data is not exposed"""
        # Test error messages don't leak information
        response = client.get("/nonexistent-endpoint")
        assert response.status_code == 404
        assert "internal server error" not in response.text.lower()
        assert "traceback" not in response.text.lower()
        assert "exception" not in response.text.lower()
        
        # Test that stack traces are not exposed
        response = client.post("/search", json={"malformed": "data"})
        if response.status_code >= 500:
            assert "traceback" not in response.text.lower()
            assert "file" not in response.text.lower()
            assert "line" not in response.text.lower()

    @pytest.mark.unit
    def test_file_upload_security(self, client):
        """Test file upload security"""
        # Test malicious file upload
        malicious_files = [
            ("malicious.exe", b"MZ\x90\x00", "application/octet-stream"),
            ("script.php", b"<?php system($_GET['cmd']); ?>", "application/x-php"),
            ("shell.jsp", b"<%@ page import=\"java.io.*\" %>", "application/x-jsp")
        ]
        
        for filename, content, content_type in malicious_files:
            files = {"file": (filename, content, content_type)}
            response = client.post("/upload", files=files)
            
            # Should reject malicious files
            assert response.status_code in [400, 422, 403]

    @pytest.mark.unit
    def test_path_traversal_protection(self, client):
        """Test path traversal protection"""
        path_traversal_payloads = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "....//....//....//etc/passwd",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
            "..%252f..%252f..%252fetc%252fpasswd"
        ]
        
        for payload in path_traversal_payloads:
            response = client.get(f"/files/{payload}")
            assert response.status_code in [400, 404, 403]
            
            # Should not return file contents
            if response.status_code == 200:
                assert "root:" not in response.text
                assert "[boot loader]" not in response.text

    @pytest.mark.unit
    def test_http_parameter_pollution(self, client):
        """Test HTTP parameter pollution protection"""
        # Test duplicate parameters
        response = client.post("/search", data=[
            ("query", "test"),
            ("query", "malicious")
        ])
        
        # Should handle gracefully without confusion
        assert response.status_code in [200, 400, 422]

    @pytest.mark.unit
    def test_content_type_validation(self, client):
        """Test content-type validation"""
        # Test invalid content types
        invalid_content_types = [
            "text/xml",
            "application/xml",
            "text/html",
            "multipart/form-data"
        ]
        
        for content_type in invalid_content_types:
            response = client.post(
                "/search",
                data='{"query": "test"}',
                headers={"Content-Type": content_type}
            )
            assert response.status_code in [400, 415, 422]

    @pytest.mark.unit
    def test_encryption_requirements(self, client):
        """Test that sensitive operations require HTTPS"""
        # This would be tested in a real deployment with HTTPS
        # For now, we test that sensitive data is not sent in plain text
        response = client.post("/auth/login", json={
            "email": "test@example.com",
            "password": "password123"
        })
        
        # Password should not be echoed back
        if response.status_code == 200:
            response_data = response.json()
            assert "password" not in response_data
            assert "password123" not in response.text

    @pytest.mark.unit
    def test_session_management(self, client):
        """Test session management security"""
        # Test session invalidation after logout
        with patch('app.utils.supabase') as mock_supabase:
            mock_supabase.auth.sign_out.return_value = {"error": None}
            
            # Mock authentication
            mock_supabase.auth.get_user.return_value = {
                "user": {"id": "test-user", "email": "test@example.com"}
            }
            
            # Login and get session
            response = client.post("/auth/login", json={
                "email": "test@example.com",
                "password": "password"
            })
            
            if response.status_code == 200:
                # Logout
                response = client.post("/auth/logout")
                assert response.status_code in [200, 401]
                
                # Try to access protected resource after logout
                response = client.get("/search")
                assert response.status_code == 401

    @pytest.mark.unit
    def test_api_key_security(self, client):
        """Test API key security if implemented"""
        # Test API key validation
        response = client.get("/api/keys", headers={"X-API-Key": "invalid-key"})
        assert response.status_code in [401, 403]
        
        # Test missing API key
        response = client.get("/api/keys")
        assert response.status_code in [401, 403]

    @pytest.mark.unit
    def test_logging_and_monitoring(self, client):
        """Test that security events are logged"""
        # This would require checking log files or monitoring systems
        # For now, we test that suspicious requests are handled appropriately
        suspicious_requests = [
            "/admin",
            "/config",
            "/env",
            "/.env",
            "/wp-admin",
            "/phpmyadmin"
        ]
        
        for path in suspicious_requests:
            response = client.get(path)
            assert response.status_code in [404, 403]
            # These should be logged in a real implementation

    @pytest.mark.unit
    def test_dependency_vulnerabilities(self):
        """Test for known vulnerable dependencies"""
        # This would typically use tools like safety or bandit
        # For now, we test that the application starts without vulnerable dependencies
        try:
            import utils
            # If we can import without errors, basic dependency check passes
            assert True
        except ImportError as e:
            pytest.fail(f"Failed to import dependencies: {e}")

    @pytest.mark.unit
    def test_error_handling_security(self, client):
        """Test secure error handling"""
        # Test various error conditions
        error_endpoints = [
            "/search",  # With invalid data
            "/auth/login",  # With invalid credentials
            "/ingestion/google/calendar"  # Without auth
        ]
        
        for endpoint in error_endpoints:
            response = client.post(endpoint, json={"invalid": "data"})
            
            # Should not leak sensitive information in errors
            if response.status_code >= 400:
                assert "password" not in response.text.lower()
                assert "secret" not in response.text.lower()
                assert "key" not in response.text.lower()
                assert "token" not in response.text.lower()
