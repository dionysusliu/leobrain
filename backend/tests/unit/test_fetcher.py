"""Tests for fetcher"""
import pytest
from unittest.mock import AsyncMock, Mock, patch
import httpx

from crawlers.core.fetcher import HttpxFetcher
from crawlers.core.types import Request, RequestMethod


@pytest.mark.unit
class TestHttpxFetcher:
    """Test HTTP fetcher"""
    
    @pytest.fixture
    def fetcher(self):
        """Create fetcher instance"""
        return HttpxFetcher(
            timeout=10,
            max_retries=2,
            respect_robots=False  # Disable for testing
        )
    
    @pytest.mark.asyncio
    async def test_fetch_success(self, fetcher, mock_httpx_response):
        """Test successful fetch"""
        mock_response = mock_httpx_response(
            url="http://example.com",
            status=200,
            content=b"<html>Success</html>"
        )
        
        with patch.object(fetcher.client, 'request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            req = Request(url="http://example.com")
            result = await fetcher.fetch(req)
            
            assert result is not None
            assert result.status == 200
            assert result.url == "http://example.com"
            assert b"Success" in result.body
    
    @pytest.mark.asyncio
    async def test_fetch_404(self, fetcher, mock_httpx_response):
        """Test fetch with 404 error"""
        mock_response = mock_httpx_response(
            url="http://example.com",
            status=404,
            content=b"Not Found"
        )
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "404", request=Mock(), response=mock_response
        )
        
        with patch.object(fetcher.client, 'request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            req = Request(url="http://example.com")
            result = await fetcher.fetch(req)
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_fetch_retry_on_429(self, fetcher, mock_httpx_response):
        """Test retry on rate limit (429)"""
        import asyncio
        
        # First call returns 429, second returns 200
        mock_429 = mock_httpx_response(status=429)
        mock_429.raise_for_status.side_effect = httpx.HTTPStatusError(
            "429", request=Mock(), response=mock_429
        )
        
        mock_200 = mock_httpx_response(status=200, content=b"Success")
        
        with patch.object(fetcher.client, 'request', new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = [mock_429, mock_200]
            with patch('asyncio.sleep', new_callable=AsyncMock):
                req = Request(url="http://example.com")
                result = await fetcher.fetch(req)
                
                assert result is not None
                assert result.status == 200
                assert mock_request.call_count == 2
    
    @pytest.mark.asyncio
    async def test_fetch_retry_on_500(self, fetcher, mock_httpx_response):
        """Test retry on server error (500)"""
        mock_500 = mock_httpx_response(status=500)
        mock_500.raise_for_status.side_effect = httpx.HTTPStatusError(
            "500", request=Mock(), response=mock_500
        )
        
        mock_200 = mock_httpx_response(status=200, content=b"Success")
        
        with patch.object(fetcher.client, 'request', new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = [mock_500, mock_200]
            with patch('asyncio.sleep', new_callable=AsyncMock):
                req = Request(url="http://example.com")
                result = await fetcher.fetch(req)
                
                assert result is not None
                assert mock_request.call_count == 2
    
    @pytest.mark.asyncio
    async def test_fetch_max_retries_exceeded(self, fetcher, mock_httpx_response):
        """Test that fetch returns None after max retries"""
        mock_500 = mock_httpx_response(status=500)
        mock_500.raise_for_status.side_effect = httpx.HTTPStatusError(
            "500", request=Mock(), response=mock_500
        )
        
        with patch.object(fetcher.client, 'request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_500
            with patch('asyncio.sleep', new_callable=AsyncMock):
                req = Request(url="http://example.com")
                result = await fetcher.fetch(req)
                
                assert result is None
                # Should retry max_retries times
                assert mock_request.call_count == fetcher.max_retries
    
    @pytest.mark.asyncio
    async def test_fetch_with_custom_headers(self, fetcher, mock_httpx_response):
        """Test fetch with custom headers"""
        mock_response = mock_httpx_response(status=200)
        
        with patch.object(fetcher.client, 'request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            req = Request(
                url="http://example.com",
                headers={"Custom-Header": "value"}
            )
            await fetcher.fetch(req)
            
            # Check that custom headers were passed
            call_args = mock_request.call_args
            assert "Custom-Header" in call_args[1]["headers"]
    
    @pytest.mark.asyncio
    async def test_close(self, fetcher):
        """Test closing fetcher"""
        await fetcher.close()
        # Should not raise exception
        assert True
