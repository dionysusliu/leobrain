"""Anti-bot measures and rate limiting"""
from typing import Optional
import asyncio
import random
from aiolimiter import AsyncLimiter
import logging

logger = logging.getLogger(__name__)


class RateLimiter:
    """Rate limiter using aiolimiter"""
    
    def __init__(self, qps: float = 1.0):
        """
        Initialize rate limiter
        
        Args:
            qps: Queries per second
        """
        self.qps = qps
        self.limiter = AsyncLimiter(max_rate=qps, time_period=1.0)
    
    async def acquire(self):
        """Acquire rate limit token"""
        await self.limiter.acquire()
    
    async def __aenter__(self):
        await self.acquire()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


class AntiBotMiddleware:
    """Anti-bot middleware with rate limiting and delays"""
    
    def __init__(
        self,
        qps: Optional[float] = None,
        delay: float = 1.0,
        jitter: bool = True
    ):
        self.qps = qps
        self.delay = delay
        self.jitter = jitter
        self.limiter = RateLimiter(qps) if qps else None
    
    async def before_request(self, req):
        """Called before making request"""
        if self.limiter:
            await self.limiter.acquire()
        
        if self.delay > 0:
            wait_time = self.delay
            if self.jitter:
                wait_time += random.uniform(0, 0.5)
            await asyncio.sleep(wait_time)
    
    async def after_request(self, resp, req):
        """Called after request"""
        pass
