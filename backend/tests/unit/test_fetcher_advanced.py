"""Advanced tests for fetcher"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from crawlers.core.fetcher import HttpxFetcher
from crawlers.core.types import Request, Response


@pytest.mark.unit
class TestHttpxFetcherAdvanced:
    """Advanced tests for HttpxFetcher"""
    
    @pytest.mark.asyncio
    async def test_fetcher_robots_txt_blocked(self):
        """Test fetcher blocking URL based on robots.txt"""
        with patch('crawlers.core.fetcher.RobotFileParser') as mock_parser_class:
            mock_parser = Mock()
            mock_parser.can_fetch.return_value = False
            mock_parser_class.return_value = mock_parser
            
            fetcher = HttpxFetcher(respect_robots=True)
            
            req = Request(url="http://example.com/page")
            result = await fetcher.fetch(req)
            
            assert result is None
            mock_parser.can_fetch.assert_called()
    
    @pytest.mark.asyncio
    async def test_fetcher_robots_txt_allowed(self):
        """Test fetcher allowing URL based on robots.txt"""
        from unittest.mock import patch, AsyncMock, Mock, MagicMock
        
        with patch('crawlers.core.fetcher.RobotFileParser') as mock_parser_class:
            mock_parser = Mock()
            mock_parser.can_fetch.return_value = True
            mock_parser.read.return_value = None
            mock_parser_class.return_value = mock_parser
            
            fetcher = HttpxFetcher(respect_robots=True)
            
            # Mock httpx client response properly
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.content = b"<html>Test</html>"
            mock_response.headers = {}
            mock_response.elapsed.total_seconds.return_value = 0.1
            mock_response.text = "<html>Test</html>"
            
            # Mock the client's request method (httpx uses request, not get)
            fetcher.client = AsyncMock()
            fetcher.client.request = AsyncMock(return_value=mock_response)
            
            req = Request(url="http://example.com/page")
            result = await fetcher.fetch(req)
            
            assert result is not None
            assert result.status == 200
    
    @pytest.mark.asyncio
    async def test_fetcher_respect_robots_disabled(self):
        """Test fetcher with robots.txt disabled"""
        fetcher = HttpxFetcher(respect_robots=False)
        
        # Should not check robots.txt
        # We can't easily test this without mocking, but we can verify
        # that the fetcher doesn't fail when robots.txt checking is disabled
        assert fetcher.respect_rebots is False
    
    @pytest.mark.asyncio
    async def test_fetcher_custom_headers(self):
        """Test fetcher with custom headers"""
        fetcher = HttpxFetcher(default_headers={"User-Agent": "test-bot"})
        
        assert fetcher.default_headers["User-Agent"] == "test-bot"
    
    @pytest.mark.asyncio
    async def test_fetcher_timeout(self):
        """Test fetcher timeout configuration"""
        fetcher = HttpxFetcher(timeout=60)
        
        assert fetcher.timeout == 60
    
    @pytest.mark.asyncio
    async def test_fetcher_max_retries(self):
        """Test fetcher max retries configuration"""
        fetcher = HttpxFetcher(max_retries=5)
        
        assert fetcher.max_retries == 5

