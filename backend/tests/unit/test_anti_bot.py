"""Tests for anti-bot middleware"""
import pytest
import asyncio
from crawlers.core.anti_bot import RateLimiter, AntiBotMiddleware
from crawlers.core.types import Request, Response


@pytest.mark.unit
class TestRateLimiter:
    """Tests for RateLimiter"""
    
    @pytest.mark.asyncio
    async def test_rate_limiter_acquire(self):
        """Test rate limiter acquire"""
        limiter = RateLimiter(qps=10.0)
        
        # Should acquire without blocking at high QPS
        start = asyncio.get_event_loop().time()
        await limiter.acquire()
        elapsed = asyncio.get_event_loop().time() - start
        
        # Should be very fast at 10 QPS
        assert elapsed < 0.1
    
    @pytest.mark.asyncio
    async def test_rate_limiter_context_manager(self):
        """Test rate limiter as context manager"""
        limiter = RateLimiter(qps=10.0)
        
        async with limiter:
            # Should acquire on enter
            pass
        # Should exit cleanly
    
    @pytest.mark.asyncio
    async def test_rate_limiter_low_qps(self):
        """Test rate limiter with low QPS"""
        limiter = RateLimiter(qps=1.0)
        
        # First acquire should be fast
        await limiter.acquire()
        
        # Second acquire should be rate limited
        start = asyncio.get_event_loop().time()
        await limiter.acquire()
        elapsed = asyncio.get_event_loop().time() - start
        
        # Should take approximately 1 second
        assert 0.9 <= elapsed <= 1.2


@pytest.mark.unit
class TestAntiBotMiddleware:
    """Tests for AntiBotMiddleware"""
    
    @pytest.mark.asyncio
    async def test_anti_bot_with_qps(self):
        """Test anti-bot middleware with QPS limiting"""
        middleware = AntiBotMiddleware(qps=10.0, delay=0.0)
        
        req = Request(url="http://example.com")
        
        # Should not block significantly at high QPS
        start = asyncio.get_event_loop().time()
        await middleware.before_request(req)
        elapsed = asyncio.get_event_loop().time() - start
        
        assert elapsed < 0.1
    
    @pytest.mark.asyncio
    async def test_anti_bot_with_delay(self):
        """Test anti-bot middleware with delay"""
        middleware = AntiBotMiddleware(qps=None, delay=0.1, jitter=False)
        
        req = Request(url="http://example.com")
        
        start = asyncio.get_event_loop().time()
        await middleware.before_request(req)
        elapsed = asyncio.get_event_loop().time() - start
        
        # Should delay approximately 0.1 seconds
        assert 0.09 <= elapsed <= 0.15
    
    @pytest.mark.asyncio
    async def test_anti_bot_with_jitter(self):
        """Test anti-bot middleware with jitter"""
        middleware = AntiBotMiddleware(qps=None, delay=0.1, jitter=True)
        
        req = Request(url="http://example.com")
        
        start = asyncio.get_event_loop().time()
        await middleware.before_request(req)
        elapsed = asyncio.get_event_loop().time() - start
        
        # Should delay between 0.1 and 0.6 seconds (with jitter)
        assert 0.09 <= elapsed <= 0.7
    
    @pytest.mark.asyncio
    async def test_anti_bot_after_request(self):
        """Test anti-bot middleware after_request"""
        middleware = AntiBotMiddleware()
        
        req = Request(url="http://example.com")
        resp = Response(
            url="http://example.com",
            status=200,
            body=b"test",
            headers={},
            request=req
        )
        
        # Should not raise exception
        await middleware.after_request(resp, req)
    
    @pytest.mark.asyncio
    async def test_anti_bot_no_qps_no_delay(self):
        """Test anti-bot middleware with no QPS and no delay"""
        middleware = AntiBotMiddleware(qps=None, delay=0.0)
        
        req = Request(url="http://example.com")
        
        start = asyncio.get_event_loop().time()
        await middleware.before_request(req)
        elapsed = asyncio.get_event_loop().time() - start
        
        # Should be very fast
        assert elapsed < 0.05

