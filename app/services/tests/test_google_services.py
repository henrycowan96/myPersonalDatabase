import pytest
from unittest.mock import patch, Mock, AsyncMock
import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from services.google_services import fetch_calendar_data, fetch_gmail_data


class TestGoogleServices:
    """Test class for Google services integration"""

    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch('services.google_services.fetch_google_calendar_events')
    async def test_fetch_calendar_data_success(self, mock_fetch_events):
        """Test successful calendar data fetch"""
        # Mock the fetch_google_calendar_events function
        mock_events = [
            {
                "summary": "Team Meeting",
                "start": {"dateTime": "2024-01-15T10:00:00Z"},
                "end": {"dateTime": "2024-01-15T11:00:00Z"},
                "calendar": "Work Calendar"
            },
            {
                "summary": "Doctor Appointment",
                "start": {"dateTime": "2024-01-16T14:00:00Z"},
                "end": {"dateTime": "2024-01-16T15:00:00Z"},
                "calendar": "Personal Calendar"
            }
        ]
        mock_fetch_events.return_value = mock_events
        
        # Test credentials
        test_creds = {"token": "test-token", "refresh_token": "test-refresh"}
        
        result = await fetch_calendar_data("test-user", test_creds)
        
        assert len(result) == 2
        assert result[0]["summary"] == "Team Meeting"
        assert result[1]["summary"] == "Doctor Appointment"
        
        # Verify the mock was called with correct credentials
        mock_fetch_events.assert_called_once_with(credentials=test_creds)

    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch('services.google_services.fetch_google_calendar_events')
    async def test_fetch_calendar_data_empty_result(self, mock_fetch_events):
        """Test calendar data fetch with no events"""
        mock_fetch_events.return_value = []
        
        test_creds = {"token": "test-token"}
        
        result = await fetch_calendar_data("test-user", test_creds)
        
        assert result == []
        mock_fetch_events.assert_called_once_with(credentials=test_creds)

    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch('services.google_services.fetch_google_calendar_events')
    async def test_fetch_calendar_data_api_error(self, mock_fetch_events):
        """Test calendar data fetch with API error"""
        mock_fetch_events.side_effect = Exception("API Error: Invalid credentials")
        
        test_creds = {"token": "invalid-token"}
        
        with pytest.raises(Exception) as exc_info:
            await fetch_calendar_data("test-user", test_creds)
        
        assert "Error fetching calendar data" in str(exc_info.value)
        assert "API Error: Invalid credentials" in str(exc_info.value)

    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch('services.google_services.fetch_gmail_emails')
    async def test_fetch_gmail_data_success(self, mock_fetch_emails):
        """Test successful Gmail data fetch"""
        # Mock the fetch_gmail_emails function
        mock_emails = [
            {
                "subject": "Project Update",
                "sender": "john.doe@example.com",
                "date": "2024-01-15T09:00:00Z",
                "payload": {
                    "headers": [],
                    "body": {"data": "SGVsbG8gV29ybGQ="}
                }
            },
            {
                "subject": "Meeting Reminder",
                "sender": "jane.smith@example.com",
                "date": "2024-01-15T10:00:00Z",
                "payload": {
                    "headers": [],
                    "body": {"data": "TWVldGluZyBhdCAxMXBt"}
                }
            }
        ]
        mock_fetch_emails.return_value = mock_emails
        
        test_creds = {"token": "test-token", "refresh_token": "test-refresh"}
        
        result = await fetch_gmail_data("test-user", test_creds)
        
        assert len(result) == 2
        assert result[0]["subject"] == "Project Update"
        assert result[1]["subject"] == "Meeting Reminder"
        
        # Verify the mock was called with correct parameters
        mock_fetch_emails.assert_called_once_with(max_results=100, credentials=test_creds)

    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch('services.google_services.fetch_gmail_emails')
    async def test_fetch_gmail_data_empty_result(self, mock_fetch_emails):
        """Test Gmail data fetch with no emails"""
        mock_fetch_emails.return_value = []
        
        test_creds = {"token": "test-token"}
        
        result = await fetch_gmail_data("test-user", test_creds)
        
        assert result == []
        mock_fetch_emails.assert_called_once_with(max_results=100, credentials=test_creds)

    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch('services.google_services.fetch_gmail_emails')
    async def test_fetch_gmail_data_api_error(self, mock_fetch_emails):
        """Test Gmail data fetch with API error"""
        mock_fetch_emails.side_effect = Exception("Gmail API Error: Quota exceeded")
        
        test_creds = {"token": "test-token"}
        
        with pytest.raises(Exception) as exc_info:
            await fetch_gmail_data("test-user", test_creds)
        
        assert "Error fetching Gmail data" in str(exc_info.value)
        assert "Gmail API Error: Quota exceeded" in str(exc_info.value)

    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch('services.google_services.fetch_google_calendar_events')
    async def test_fetch_calendar_data_with_large_dataset(self, mock_fetch_events):
        """Test calendar data fetch with large dataset"""
        # Mock a large number of events
        mock_events = []
        for i in range(150):
            mock_events.append({
                "summary": f"Event {i}",
                "start": {"dateTime": f"2024-01-{(i % 30) + 1:02d}T10:00:00Z"},
                "end": {"dateTime": f"2024-01-{(i % 30) + 1:02d}T11:00:00Z"},
                "calendar": "Work Calendar"
            })
        
        mock_fetch_events.return_value = mock_events
        
        test_creds = {"token": "test-token"}
        
        result = await fetch_calendar_data("test-user", test_creds)
        
        assert len(result) == 150
        assert result[0]["summary"] == "Event 0"
        assert result[149]["summary"] == "Event 149"

    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch('services.google_services.fetch_gmail_emails')
    async def test_fetch_gmail_data_with_custom_limit(self, mock_fetch_emails):
        """Test Gmail data fetch with custom max_results"""
        mock_emails = [{"subject": f"Email {i}"} for i in range(50)]
        mock_fetch_emails.return_value = mock_emails
        
        test_creds = {"token": "test-token"}
        
        # Note: The function currently hardcodes max_results=100
        result = await fetch_gmail_data("test-user", test_creds)
        
        assert len(result) == 50
        mock_fetch_emails.assert_called_once_with(max_results=100, credentials=test_creds)

    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch('services.google_services.fetch_google_calendar_events')
    async def test_fetch_calendar_data_credentials_validation(self, mock_fetch_events):
        """Test that credentials are properly passed to the fetch function"""
        mock_fetch_events.return_value = []
        
        test_creds = {
            "token": "access-token-123",
            "refresh_token": "refresh-token-456",
            "client_id": "client-id-789",
            "client_secret": "client-secret-abc"
        }
        
        await fetch_calendar_data("test-user", test_creds)
        
        # Verify credentials are passed correctly
        mock_fetch_events.assert_called_once_with(credentials=test_creds)

    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch('services.google_services.fetch_gmail_emails')
    async def test_fetch_gmail_data_credentials_validation(self, mock_fetch_emails):
        """Test that credentials are properly passed to the fetch function"""
        mock_fetch_emails.return_value = []
        
        test_creds = {
            "token": "gmail-access-token",
            "refresh_token": "gmail-refresh-token"
        }
        
        await fetch_gmail_data("test-user", test_creds)
        
        # Verify credentials are passed correctly
        mock_fetch_emails.assert_called_once_with(max_results=100, credentials=test_creds)
