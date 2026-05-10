import pytest
from unittest.mock import patch, Mock, AsyncMock
import sys
from pathlib import Path
import os

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

import utils


class TestUtils:
    """Test class for utility functions"""

    @pytest.mark.unit
    def test_pinecone_initialization(self):
        """Test Pinecone client initialization"""
        with patch.dict(os.environ, {'PINECONE_API_KEY': 'test-key'}):
            with patch('pinecone.Pinecone') as mock_pinecone:
                mock_index = Mock()
                mock_pinecone.return_value.Index.return_value = mock_index
                
                index = utils.initialize_pinecone()
                
                assert index is not None
                mock_pinecone.assert_called_once()

    @pytest.mark.unit
    def test_embedding_model_initialization(self):
        """Test embedding model initialization"""
        with patch('sentence_transformers.SentenceTransformer') as mock_model:
            mock_encoder = Mock()
            mock_encoder.encode.return_value = [0.1, 0.2, 0.3]
            mock_model.return_value = mock_encoder
            
            model = utils.initialize_embedding_model()
            
            assert model is not None
            mock_model.assert_called_once()

    @pytest.mark.unit
    def test_llm_initialization(self):
        """Test LLM initialization"""
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'}):
            with patch('openai.OpenAI') as mock_openai:
                mock_client = Mock()
                mock_openai.return_value = mock_client
                
                client = utils.initialize_llm()
                
                assert client is not None
                mock_openai.assert_called_once()

    @pytest.mark.unit
    def test_supabase_initialization(self):
        """Test Supabase client initialization"""
        with patch.dict(os.environ, {
            'SUPABASE_URL': 'https://test.supabase.co',
            'SUPABASE_KEY': 'test-key'
        }):
            with patch('supabase.create_client') as mock_supabase:
                mock_client = Mock()
                mock_supabase.return_value = mock_client
                
                client = utils.initialize_supabase()
                
                assert client is not None
                mock_supabase.assert_called_once()

    @pytest.mark.unit
    def test_text_preprocessing(self):
        """Test text preprocessing functions"""
        test_cases = [
            ("  Hello World  ", "hello world"),
            ("Hello\nWorld\tTest", "hello world test"),
            ("Hello!!! World???", "hello world"),
            ("Hello's test", "hello s test"),
            ("café résumé", "cafe resume"),
            ("123 test 456", "123 test 456")
        ]
        
        for input_text, expected in test_cases:
            result = utils.preprocess_text(input_text)
            assert result == expected

    @pytest.mark.unit
    def test_text_truncation(self):
        """Test text truncation functionality"""
        long_text = "x" * 1000
        
        # Test with default limit
        truncated = utils.truncate_text(long_text)
        assert len(truncated) <= 500
        assert "truncated" in truncated.lower()
        
        # Test with custom limit
        truncated_custom = utils.truncate_text(long_text, max_length=200)
        assert len(truncated_custom) <= 200
        assert "truncated" in truncated_custom.lower()

    @pytest.mark.unit
    def test_data_validation(self):
        """Test data validation functions"""
        # Valid data
        valid_data = {
            "title": "Test Event",
            "date": "2024-01-15T10:00:00Z",
            "type": "calendar_event"
        }
        assert utils.validate_event_data(valid_data) is True
        
        # Missing required fields
        invalid_data = {
            "title": "Test Event"
            # Missing date and type
        }
        assert utils.validate_event_data(invalid_data) is False
        
        # Invalid date format
        invalid_date = {
            "title": "Test Event",
            "date": "invalid-date",
            "type": "calendar_event"
        }
        assert utils.validate_event_data(invalid_date) is False

    @pytest.mark.unit
    def test_error_handling(self):
        """Test error handling utilities"""
        # Test safe JSON parsing
        valid_json = '{"key": "value"}'
        result = utils.safe_json_parse(valid_json)
        assert result == {"key": "value"}
        
        invalid_json = '{"key": invalid}'
        result = utils.safe_json_parse(invalid_json)
        assert result is None
        
        # Test safe string conversion
        assert utils.safe_str(None) == ""
        assert utils.safe_str(123) == "123"
        assert utils.safe_str("test") == "test"

    @pytest.mark.unit
    def test_caching_mechanism(self):
        """Test caching utilities"""
        cache = utils.SimpleCache(max_size=2, ttl=60)
        
        # Test cache set and get
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"
        
        # Test cache miss
        assert cache.get("nonexistent") is None
        
        # Test cache eviction
        cache.set("key2", "value2")
        cache.set("key3", "value3")  # Should evict key1
        
        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"
        assert cache.get("key3") == "value3"

    @pytest.mark.unit
    def test_rate_limiter(self):
        """Test rate limiting functionality"""
        limiter = utils.RateLimiter(max_requests=3, time_window=60)
        
        # Should allow requests within limit
        assert limiter.is_allowed("user1") is True
        assert limiter.is_allowed("user1") is True
        assert limiter.is_allowed("user1") is True
        
        # Should block requests over limit
        assert limiter.is_allowed("user1") is False
        
        # Different users should have separate limits
        assert limiter.is_allowed("user2") is True

    @pytest.mark.unit
    def test_data_sanitization(self):
        """Test data sanitization"""
        test_cases = [
            ("<script>alert('xss')</script>", "scriptalert('xss')/script"),
            ("javascript:alert('xss')", "javascript:alert('xss')"),
            ("'; DROP TABLE users; --", "'; DROP TABLE users; --"),
            ("Hello <b>World</b>", "Hello World")
        ]
        
        for input_data, expected in test_cases:
            sanitized = utils.sanitize_input(input_data)
            assert sanitized == expected

    @pytest.mark.unit
    def test_date_parsing(self):
        """Test date parsing utilities"""
        test_dates = [
            ("2024-01-15T10:00:00Z", "2024-01-15 10:00:00"),
            ("2024-01-15", "2024-01-15 00:00:00"),
            ("Jan 15, 2024", "2024-01-15 00:00:00"),
            ("invalid-date", None)
        ]
        
        for input_date, expected in test_dates:
            result = utils.parse_date(input_date)
            if expected is None:
                assert result is None
            else:
                assert expected in str(result)

    @pytest.mark.unit
    def test_file_operations(self):
        """Test file operation utilities"""
        # Test safe file reading
        with patch('builtins.open', mock_open(read_data="test content")):
            content = utils.safe_read_file("test.txt")
            assert content == "test content"
        
        # Test safe file writing
        with patch('builtins.open', mock_open()) as mock_file:
            utils.safe_write_file("test.txt", "content")
            mock_file.assert_called_once()

    @pytest.mark.unit
    def test_environment_variable_handling(self):
        """Test environment variable utilities"""
        # Test with existing variable
        with patch.dict(os.environ, {'TEST_VAR': 'test_value'}):
            assert utils.get_env_var('TEST_VAR') == 'test_value'
            assert utils.get_env_var('TEST_VAR', 'default') == 'test_value'
        
        # Test with non-existing variable
        assert utils.get_env_var('NON_EXISTING') is None
        assert utils.get_env_var('NON_EXISTING', 'default') == 'default'

    @pytest.mark.unit
    def test_api_key_validation(self):
        """Test API key validation"""
        # Valid keys
        valid_keys = [
            "sk-1234567890abcdef",  # OpenAI format
            "pinecone-test-key",       # Pinecone format
            "eyJhbGciOiJIUzI1NiIs"   # JWT format
        ]
        
        for key in valid_keys:
            assert utils.validate_api_key(key) is True
        
        # Invalid keys
        invalid_keys = [
            "",
            "short",
            None,
            "invalid-key-format"
        ]
        
        for key in invalid_keys:
            assert utils.validate_api_key(key) is False

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_async_error_handling(self):
        """Test async error handling"""
        # Test async function with error
        async def failing_function():
            raise ValueError("Test error")
        
        result = await utils.safe_async_execute(failing_function)
        assert result is None
        
        # Test successful async function
        async def successful_function():
            return "success"
        
        result = await utils.safe_async_execute(successful_function)
        assert result == "success"

    @pytest.mark.unit
    def test_performance_monitoring(self):
        """Test performance monitoring utilities"""
        monitor = utils.PerformanceMonitor()
        
        # Test timing
        with monitor.time_operation("test_operation"):
            import time
            time.sleep(0.1)
        
        metrics = monitor.get_metrics()
        assert "test_operation" in metrics
        assert metrics["test_operation"]["count"] == 1
        assert metrics["test_operation"]["total_time"] >= 0.1

    @pytest.mark.unit
    def test_data_encryption(self):
        """Test data encryption utilities"""
        sensitive_data = "sensitive information"
        
        # Test encryption
        encrypted = utils.encrypt_data(sensitive_data)
        assert encrypted != sensitive_data
        assert len(encrypted) > 0
        
        # Test decryption
        decrypted = utils.decrypt_data(encrypted)
        assert decrypted == sensitive_data

    @pytest.mark.unit
    def test_batch_processing(self):
        """Test batch processing utilities"""
        data = list(range(100))
        batch_size = 25
        
        batches = list(utils.create_batches(data, batch_size))
        
        assert len(batches) == 4
        assert all(len(batch) == batch_size for batch in batches)
        
        # Flatten and verify all data is present
        flattened = [item for batch in batches for item in batch]
        assert flattened == data

    @pytest.mark.unit
    def test_data_deduplication(self):
        """Test data deduplication"""
        data_with_duplicates = [
            {"id": 1, "content": "test"},
            {"id": 2, "content": "test2"},
            {"id": 1, "content": "test"},  # Duplicate
            {"id": 3, "content": "test3"}
        ]
        
        deduplicated = utils.deduplicate_by_key(data_with_duplicates, "id")
        
        assert len(deduplicated) == 3
        ids = [item["id"] for item in deduplicated]
        assert ids == [1, 2, 3]

    @pytest.mark.unit
    def test_logging_configuration(self):
        """Test logging configuration"""
        logger = utils.setup_logger("test_logger", level="INFO")
        
        assert logger.name == "test_logger"
        assert logger.level == 20  # INFO level
        
        # Test logging
        with patch('logging.Logger.info') as mock_info:
            logger.info("Test message")
            mock_info.assert_called_once_with("Test message")


# Helper function for mocking file operations
def mock_open(read_data=""):
    from unittest.mock import mock_open as _mock_open
    return _mock_open(read_data=read_data)
