import pytest
from unittest.mock import patch, Mock, AsyncMock
import subprocess
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from services.apple_services import fetch_apple_notes, fetch_apple_calendar, fetch_apple_music_data


class TestAppleServices:
    """Test class for Apple services integration"""

    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch('subprocess.run')
    async def test_fetch_apple_notes_success(self, mock_subprocess):
        """Test successful Apple Notes fetch"""
        # Mock subprocess responses
        mock_count_result = Mock()
        mock_count_result.stdout = "5"
        mock_count_result.returncode = 0
        
        mock_note_result = Mock()
        mock_note_result.stdout = "Test Note\n---SEPARATOR---\nThis is test content\n---SEPARATOR---\n2024-01-15 10:00:00\n---SEPARATOR---\n2024-01-15 11:00:00"
        mock_note_result.returncode = 0
        
        # Configure subprocess to return different responses for different calls
        mock_subprocess.side_effect = [
            mock_count_result,  # First call: count notes
            mock_note_result,   # Second call: fetch first note
            mock_note_result,   # Third call: fetch second note
            mock_note_result,   # Fourth call: fetch third note
            mock_note_result,   # Fifth call: fetch fourth note
            mock_note_result    # Sixth call: fetch fifth note
        ]
        
        result = await fetch_apple_notes()
        
        assert len(result) == 5
        assert result[0]["name"] == "Test Note"
        assert result[0]["body"] == "This is test content"
        assert result[0]["created"] == "2024-01-15 10:00:00"
        assert result[0]["modified"] == "2024-01-15 11:00:00"

    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch('subprocess.run')
    async def test_fetch_apple_notes_no_notes(self, mock_subprocess):
        """Test Apple Notes fetch with no notes"""
        mock_count_result = Mock()
        mock_count_result.stdout = "0"
        mock_count_result.returncode = 0
        
        mock_subprocess.return_value = mock_count_result
        
        result = await fetch_apple_notes()
        
        assert result == []
        mock_subprocess.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch('subprocess.run')
    async def test_fetch_apple_notes_subprocess_error(self, mock_subprocess):
        """Test Apple Notes fetch with subprocess error"""
        mock_subprocess.side_effect = subprocess.CalledProcessError(
            1, 'osascript', 'AppleScript execution failed'
        )
        
        with pytest.raises(Exception) as exc_info:
            await fetch_apple_notes()
        
        assert "Error fetching Apple Notes" in str(exc_info.value)

    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch('subprocess.run')
    async def test_fetch_apple_notes_large_dataset(self, mock_subprocess):
        """Test Apple Notes fetch with large dataset (should be limited to 50)"""
        # Mock 60 notes, but function should limit to 50
        mock_count_result = Mock()
        mock_count_result.stdout = "60"
        mock_count_result.returncode = 0
        
        mock_note_result = Mock()
        mock_note_result.stdout = "Note\n---SEPARATOR---\nContent\n---SEPARATOR---\n2024-01-15 10:00:00\n---SEPARATOR---\n2024-01-15 11:00:00"
        mock_note_result.returncode = 0
        
        # Configure subprocess: count call + 50 note calls
        mock_subprocess.side_effect = [mock_count_result] + [mock_note_result] * 50
        
        result = await fetch_apple_notes()
        
        # Should be limited to 50 notes
        assert len(result) == 50
        assert mock_subprocess.call_count == 51  # 1 count + 50 note fetches

    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch('subprocess.run')
    async def test_fetch_apple_calendar_success(self, mock_subprocess):
        """Test successful Apple Calendar fetch"""
        mock_result = Mock()
        mock_result.stdout = '''{"calendars": [
            {
                "name": "Work",
                "events": [
                    {
                        "summary": "Team Meeting",
                        "startDate": "2024-01-15 10:00:00",
                        "endDate": "2024-01-15 11:00:00",
                        "location": "Conference Room",
                        "notes": "Weekly sync"
                    }
                ]
            }
        ]}'''
        mock_result.returncode = 0
        
        mock_subprocess.return_value = mock_result
        
        result = await fetch_apple_calendar()
        
        assert len(result) == 1
        assert result[0]["calendar"] == "Work"
        assert result[0]["summary"] == "Team Meeting"
        assert result[0]["start_date"] == "2024-01-15 10:00:00"
        assert result[0]["end_date"] == "2024-01-15 11:00:00"

    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch('subprocess.run')
    async def test_fetch_apple_calendar_no_events(self, mock_subprocess):
        """Test Apple Calendar fetch with no events"""
        mock_result = Mock()
        mock_result.stdout = '''{"calendars": []}'''
        mock_result.returncode = 0
        
        mock_subprocess.return_value = mock_result
        
        result = await fetch_apple_calendar()
        
        assert result == []

    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch('subprocess.run')
    async def test_fetch_apple_calendar_subprocess_error(self, mock_subprocess):
        """Test Apple Calendar fetch with subprocess error"""
        mock_subprocess.side_effect = subprocess.CalledProcessError(
            1, 'osascript', 'Calendar access denied'
        )
        
        with pytest.raises(Exception) as exc_info:
            await fetch_apple_calendar()
        
        assert "Error fetching Apple Calendar" in str(exc_info.value)

    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch('subprocess.run')
    async def test_fetch_apple_music_success(self, mock_subprocess):
        """Test successful Apple Music fetch"""
        mock_result = Mock()
        mock_result.stdout = '''{
            "results": {
                "songs": {
                    "data": [
                        {
                            "attributes": {
                                "name": "Test Song",
                                "artistName": "Test Artist",
                                "albumName": "Test Album",
                                "genreNames": ["Pop"],
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
                                "genreNames": ["Rock"],
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
        }'''
        mock_result.returncode = 0
        
        mock_subprocess.return_value = mock_result
        
        result = await fetch_apple_music()
        
        assert "results" in result
        assert "songs" in result["results"]
        assert "albums" in result["results"]
        assert "artists" in result["results"]
        
        songs = result["results"]["songs"]["data"]
        assert len(songs) == 1
        assert songs[0]["attributes"]["name"] == "Test Song"
        assert songs[0]["attributes"]["artistName"] == "Test Artist"

    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch('subprocess.run')
    async def test_fetch_apple_music_no_data(self, mock_subprocess):
        """Test Apple Music fetch with no data"""
        mock_result = Mock()
        mock_result.stdout = '''{"results": {"songs": {"data": []}, "albums": {"data": []}, "artists": {"data": []}}}'''
        mock_result.returncode = 0
        
        mock_subprocess.return_value = mock_result
        
        result = await fetch_apple_music()
        
        songs = result["results"]["songs"]["data"]
        albums = result["results"]["albums"]["data"]
        artists = result["results"]["artists"]["data"]
        
        assert len(songs) == 0
        assert len(albums) == 0
        assert len(artists) == 0

    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch('subprocess.run')
    async def test_fetch_apple_music_invalid_json(self, mock_subprocess):
        """Test Apple Music fetch with invalid JSON response"""
        mock_result = Mock()
        mock_result.stdout = "Invalid JSON response"
        mock_result.returncode = 0
        
        mock_subprocess.return_value = mock_result
        
        with pytest.raises(Exception) as exc_info:
            await fetch_apple_music()
        
        assert "Error fetching Apple Music" in str(exc_info.value)

    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch('subprocess.run')
    async def test_fetch_apple_notes_malformed_data(self, mock_subprocess):
        """Test Apple Notes fetch with malformed note data"""
        mock_count_result = Mock()
        mock_count_result.stdout = "1"
        mock_count_result.returncode = 0
        
        # Mock note data missing separators
        mock_note_result = Mock()
        mock_note_result.stdout = "Test Note\nMissing separators"
        mock_note_result.returncode = 0
        
        mock_subprocess.side_effect = [mock_count_result, mock_note_result]
        
        result = await fetch_apple_notes()
        
        # Should handle malformed data gracefully
        assert len(result) == 1
        # The note might have empty fields due to parsing issues
        assert "name" in result[0] or "body" in result[0]

    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch('subprocess.run')
    async def test_fetch_apple_calendar_malformed_json(self, mock_subprocess):
        """Test Apple Calendar fetch with malformed JSON"""
        mock_result = Mock()
        mock_result.stdout = '{"calendars": [{"name": "Work", "events": [invalid json}]'
        mock_result.returncode = 0
        
        mock_subprocess.return_value = mock_result
        
        with pytest.raises(Exception) as exc_info:
            await fetch_apple_calendar()
        
        assert "Error fetching Apple Calendar" in str(exc_info.value)

    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch('subprocess.run')
    async def test_fetch_apple_music_partial_data(self, mock_subprocess):
        """Test Apple Music fetch with partial data (some sections missing)"""
        mock_result = Mock()
        mock_result.stdout = '''{
            "results": {
                "songs": {
                    "data": [
                        {
                            "attributes": {
                                "name": "Test Song",
                                "artistName": "Test Artist"
                            }
                        }
                    ]
                }
            }
        }'''
        mock_result.returncode = 0
        
        mock_subprocess.return_value = mock_result
        
        result = await fetch_apple_music()
        
        # Should handle missing sections gracefully
        assert "results" in result
        assert "songs" in result["results"]
        assert len(result["results"]["songs"]["data"]) == 1
        
        # Missing sections should be handled gracefully
        albums = result["results"].get("albums", {}).get("data", [])
        artists = result["results"].get("artists", {}).get("data", [])
        
        # Should not crash even if sections are missing
        assert isinstance(albums, list)
        assert isinstance(artists, list)
