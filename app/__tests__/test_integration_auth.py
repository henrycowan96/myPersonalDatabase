import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock, AsyncMock
import json
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from api import app
from oauth import oauth_states, get_oauth_config


class TestAuthenticationIntegration:
    """Integration tests for authentication flows"""

    @pytest.fixture
    def client(self):
        """Create test client for FastAPI app"""
        return TestClient(app)

    @pytest.mark.integration
    def test_oauth_callback_success(self, client):
        """Test successful OAuth callback flow"""
        # Mock OAuth state
        test_state = "test-state-123"
        test_service = "calendar"
        oauth_states[test_state] = {
            "service": test_service,
            "user_id": "test-user-123",
            "created_at": datetime.utcnow()
        }

        # Mock token exchange
        with patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = {
                "access_token": "test-access-token",
                "refresh_token": "test-refresh-token",
                "expires_in": 3600
            }
            mock_response.raise_for_status.return_value = None
            mock_post.return_value = mock_response

            # Mock Supabase storage
            with patch('utils.supabase') as mock_supabase:
                mock_table = Mock()
                mock_table.insert.return_value.execute.return_value = {
                    "data": [{"id": "token-id"}],
                    "error": None
                }
                mock_supabase.table.return_value = mock_table

                response = client.get(
                    "/auth/callback",
                    params={
                        "code": "test-auth-code",
                        "state": test_state,
                        "scope": "https://www.googleapis.com/auth/calendar.readonly"
                    }
                )

                assert response.status_code == 200
                assert "Authentication successful" in response.json()["message"]

    @pytest.mark.integration
    def test_oauth_callback_invalid_state(self, client):
        """Test OAuth callback with invalid state"""
        response = client.get(
            "/auth/callback",
            params={
                "code": "test-auth-code",
                "state": "invalid-state"
            }
        )

        assert response.status_code == 400
        assert "Invalid state parameter" in response.json()["detail"]

    @pytest.mark.integration
    def test_oauth_callback_missing_parameters(self, client):
        """Test OAuth callback with missing required parameters"""
        # Missing code
        response = client.get(
            "/auth/callback",
            params={
                "state": "test-state"
            }
        )
        assert response.status_code == 400

        # Missing state
        response = client.get(
            "/auth/callback",
            params={
                "code": "test-code"
            }
        )
        assert response.status_code == 400

    @pytest.mark.integration
    def test_oauth_callback_error_response(self, client):
        """Test OAuth callback when provider returns error"""
        response = client.get(
            "/auth/callback",
            params={
                "error": "access_denied",
                "state": "test-state"
            }
        )

        assert response.status_code == 400
        assert "access_denied" in response.json()["detail"]

    @pytest.mark.integration
    def test_oauth_initiation_flow(self, client):
        """Test OAuth initiation flow"""
        with patch('routes.auth.get_oauth_config') as mock_config:
            mock_config.return_value = {
                "client_id": "test-client-id",
                "client_secret": "test-client-secret",
                "redirect_uri": "http://localhost:8000/auth/callback"
            }

            response = client.get(
                "/auth/google",
                params={
                    "service": "calendar",
                    "user_id": "test-user-123"
                }
            )

            assert response.status_code == 302  # Redirect to Google
            assert "accounts.google.com" in response.headers["location"]

    @pytest.mark.integration
    def test_token_storage_and_retrieval(self, client):
        """Test that OAuth tokens are properly stored and retrieved"""
        test_state = "test-state-token-storage"
        oauth_states[test_state] = {
            "service": "gmail",
            "user_id": "test-user-token",
            "created_at": datetime.utcnow()
        }

        with patch('requests.post') as mock_post, \
             patch('utils.supabase') as mock_supabase:
            
            # Mock token exchange
            mock_response = Mock()
            mock_response.json.return_value = {
                "access_token": "stored-access-token",
                "refresh_token": "stored-refresh-token",
                "expires_in": 3600
            }
            mock_response.raise_for_status.return_value = None
            mock_post.return_value = mock_response

            # Mock Supabase storage
            mock_table = Mock()
            mock_table.insert.return_value.execute.return_value = {
                "data": [{"id": "stored-token-id"}],
                "error": None
            }
            mock_supabase.table.return_value = mock_table

            response = client.get(
                "/auth/callback",
                params={
                    "code": "test-code",
                    "state": test_state,
                    "scope": "https://www.googleapis.com/auth/gmail.readonly"
                }
            )

            assert response.status_code == 200
            
            # Verify token was stored
            mock_supabase.table.assert_called_with("oauth_tokens")
            mock_table.insert.assert_called_once()
            
            # Check the stored token data
            insert_call = mock_table.insert.call_args[0][0]
            assert insert_call["user_id"] == "test-user-token"
            assert insert_call["service"] == "gmail"
            assert insert_call["access_token"] == "stored-access-token"
            assert insert_call["refresh_token"] == "stored-refresh-token"

    @pytest.mark.integration
    def test_token_refresh_flow(self, client):
        """Test automatic token refresh flow"""
        with patch('utils.supabase') as mock_supabase, \
             patch('requests.post') as mock_post:
            
            # Mock existing expired token
            mock_table = Mock()
            mock_table.select.return_value.eq.return_value.execute.return_value = {
                "data": [{
                    "id": "token-id",
                    "access_token": "expired-token",
                    "refresh_token": "valid-refresh-token",
                    "expires_at": (datetime.utcnow() - timedelta(hours=1)).isoformat()
                }],
                "error": None
            }
            mock_supabase.table.return_value = mock_table

            # Mock token refresh response
            mock_refresh_response = Mock()
            mock_refresh_response.json.return_value = {
                "access_token": "new-access-token",
                "refresh_token": "new-refresh-token",
                "expires_in": 3600
            }
            mock_refresh_response.raise_for_status.return_value = None
            mock_post.return_value = mock_refresh_response

            # Mock token update
            mock_table.update.return_value.eq.return_value.execute.return_value = {
                "data": [{"id": "token-id"}],
                "error": None
            }

            # This would typically be called by a service that needs fresh tokens
            from routes.auth import get_valid_token
            token = get_valid_token("test-user", "gmail")

            assert token == "new-access-token"

    @pytest.mark.integration
    def test_multiple_service_authentication(self, client):
        """Test authentication for multiple services"""
        services = ["calendar", "gmail", "google_drive"]
        
        for service in services:
            test_state = f"test-state-{service}"
            oauth_states[test_state] = {
                "service": service,
                "user_id": "test-user-multi",
                "created_at": datetime.utcnow()
            }

            with patch('requests.post') as mock_post, \
                 patch('utils.supabase') as mock_supabase:
                
                # Mock token exchange
                mock_response = Mock()
                mock_response.json.return_value = {
                    "access_token": f"{service}-access-token",
                    "refresh_token": f"{service}-refresh-token",
                    "expires_in": 3600
                }
                mock_response.raise_for_status.return_value = None
                mock_post.return_value = mock_response

                # Mock Supabase storage
                mock_table = Mock()
                mock_table.insert.return_value.execute.return_value = {
                    "data": [{"id": f"{service}-token-id"}],
                    "error": None
                }
                mock_supabase.table.return_value = mock_table

                response = client.get(
                    "/auth/callback",
                    params={
                        "code": f"test-code-{service}",
                        "state": test_state,
                        "scope": f"https://www.googleapis.com/auth/{service}.readonly"
                    }
                )

                assert response.status_code == 200
                
                # Verify service-specific token was stored
                insert_call = mock_table.insert.call_args[0][0]
                assert insert_call["service"] == service
                assert insert_call["access_token"] == f"{service}-access-token"

    @pytest.mark.integration
    def test_authentication_error_handling(self, client):
        """Test error handling in authentication flow"""
        test_state = "test-state-error"
        oauth_states[test_state] = {
            "service": "calendar",
            "user_id": "test-user-error",
            "created_at": datetime.utcnow()
        }

        # Mock token exchange failure
        with patch('requests.post') as mock_post:
            mock_post.side_effect = Exception("Network error")

            response = client.get(
                "/auth/callback",
                params={
                    "code": "test-code",
                    "state": test_state,
                    "scope": "https://www.googleapis.com/auth/calendar.readonly"
                }
            )

            # Should handle error gracefully
            assert response.status_code in [400, 500]

    @pytest.mark.integration
    def test_session_management(self, client):
        """Test authentication session management"""
        test_state = "test-state-session"
        test_user_id = "test-user-session"
        oauth_states[test_state] = {
            "service": "calendar",
            "user_id": test_user_id,
            "created_at": datetime.utcnow()
        }

        with patch('requests.post') as mock_post, \
             patch('utils.supabase') as mock_supabase:
            
            # Mock successful authentication
            mock_response = Mock()
            mock_response.json.return_value = {
                "access_token": "session-access-token",
                "refresh_token": "session-refresh-token",
                "expires_in": 3600
            }
            mock_response.raise_for_status.return_value = None
            mock_post.return_value = mock_response

            mock_table = Mock()
            mock_table.insert.return_value.execute.return_value = {
                "data": [{"id": "session-token-id"}],
                "error": None
            }
            mock_supabase.table.return_value = mock_table

            # Authenticate
            auth_response = client.get(
                "/auth/callback",
                params={
                    "code": "test-code",
                    "state": test_state,
                    "scope": "https://www.googleapis.com/auth/calendar.readonly"
                }
            )

            assert auth_response.status_code == 200

            # Verify session state is cleaned up
            assert test_state not in oauth_states

    @pytest.mark.integration
    def test_security_validation(self, client):
        """Test security validations in authentication flow"""
        # Test state expiration
        expired_state = "expired-state"
        oauth_states[expired_state] = {
            "service": "calendar",
            "user_id": "test-user",
            "created_at": datetime.utcnow() - timedelta(minutes=15)  # Expired
        }

        response = client.get(
            "/auth/callback",
            params={
                "code": "test-code",
                "state": expired_state,
                "scope": "https://www.googleapis.com/auth/calendar.readonly"
            }
        )

        # Should reject expired state
        assert response.status_code == 400

    @pytest.mark.integration
    def test_concurrent_authentication_requests(self, client):
        """Test handling of concurrent authentication requests"""
        import threading
        import time

        # Create multiple states for the same user
        states = []
        for i in range(3):
            state = f"concurrent-state-{i}"
            oauth_states[state] = {
                "service": "calendar",
                "user_id": "test-user-concurrent",
                "created_at": datetime.utcnow()
            }
            states.append(state)

        results = []
        errors = []

        def authenticate_with_state(state):
            try:
                with patch('requests.post') as mock_post, \
                     patch('utils.supabase') as mock_supabase:
                    
                    mock_response = Mock()
                    mock_response.json.return_value = {
                        "access_token": f"token-{state}",
                        "refresh_token": f"refresh-{state}",
                        "expires_in": 3600
                    }
                    mock_response.raise_for_status.return_value = None
                    mock_post.return_value = mock_response

                    mock_table = Mock()
                    mock_table.insert.return_value.execute.return_value = {
                        "data": [{"id": f"id-{state}"}],
                        "error": None
                    }
                    mock_supabase.table.return_value = mock_table

                    response = client.get(
                        "/auth/callback",
                        params={
                            "code": f"code-{state}",
                            "state": state,
                            "scope": "https://www.googleapis.com/auth/calendar.readonly"
                        }
                    )
                    
                    results.append((state, response.status_code))
            except Exception as e:
                errors.append(str(e))

        # Run concurrent authentication requests
        threads = []
        for state in states:
            thread = threading.Thread(target=authenticate_with_state, args=(state,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify all requests succeeded
        assert len(results) == 3
        assert all(status == 200 for _, status in results)
        assert len(errors) == 0

    @pytest.mark.integration
    def test_authentication_with_invalid_scope(self, client):
        """Test authentication with invalid or insufficient scope"""
        test_state = "test-state-invalid-scope"
        oauth_states[test_state] = {
            "service": "calendar",
            "user_id": "test-user",
            "created_at": datetime.utcnow()
        }

        response = client.get(
            "/auth/callback",
            params={
                "code": "test-code",
                "state": test_state,
                "scope": "invalid-scope"
            }
        )

        # Should handle invalid scope gracefully
        assert response.status_code in [400, 200]  # Depending on implementation

    @pytest.mark.integration
    def test_user_authentication_isolation(self, client):
        """Test that user authentication data is properly isolated"""
        users = ["user1", "user2"]
        
        for i, user in enumerate(users):
            test_state = f"state-{user}"
            oauth_states[test_state] = {
                "service": "gmail",
                "user_id": user,
                "created_at": datetime.utcnow()
            }

            with patch('requests.post') as mock_post, \
                 patch('utils.supabase') as mock_supabase:
                
                mock_response = Mock()
                mock_response.json.return_value = {
                    "access_token": f"token-{user}",
                    "refresh_token": f"refresh-{user}",
                    "expires_in": 3600
                }
                mock_response.raise_for_status.return_value = None
                mock_post.return_value = mock_response

                mock_table = Mock()
                mock_table.insert.return_value.execute.return_value = {
                    "data": [{"id": f"id-{user}"}],
                    "error": None
                }
                mock_supabase.table.return_value = mock_table

                response = client.get(
                    "/auth/callback",
                    params={
                        "code": f"code-{user}",
                        "state": test_state,
                        "scope": "https://www.googleapis.com/auth/gmail.readonly"
                    }
                )

                assert response.status_code == 200
                
                # Verify user-specific token storage
                insert_call = mock_table.insert.call_args[0][0]
                assert insert_call["user_id"] == user
                assert insert_call["access_token"] == f"token-{user}"
