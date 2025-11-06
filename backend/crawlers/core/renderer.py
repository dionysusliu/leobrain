"""Renderer interface for browser rendering"""
from abc import ABC, abstractmethod
from typing import Optional
import logging

from crawlers.core.types import Request, Response

logger = logging.getLogger(__name__)


class IRenderer(ABC):
    """Renderer interface"""

    @abstractmethod
    async def render(self, req: Request) -> Optional[Response]:
        """Render page using browser"""
        pass

    
class NoopRenderer(IRenderer):
    """No-op renderer (for static content)"""
    
    async def render(self, req: Request) -> Optional[Response]:
        """Returns None - no rendering"""
        return None

        
        
from playwright.async_api import async_playwright

class PlaywrightRenderer(IRenderer):
    """Playwright-based rendered"""
    
    def __init__(self, headless: bool = True, browser_type: str = "chromium"):
        self.headless = headless
        self.browser_type = browser_type
        self.browser = None
        self.context = None

    async def start(self):
        """Start browser"""
        self.playwright = await async_playwright().start()
        browser_class = getattr(self.playwright, self.browser_type)
        self.browser = await browser_class.launch(headless=self.headless)
        self.context = await self.browser.new_context()

    async def close(self):
        """Close browser"""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if hasattr(self, 'playwright'):
            await self.playwright.stop()
            
    async def render(self, req: Request) -> Optional[Response]:
        """Render page using Playwright"""
        if not self.browser:
            await self.start()
        
        try:
            page = await self.context.new_page()
            await page.goto(req.url, wait_until="networkidle")
            
            # Get content
            body = await page.content()
            body_bytes = body.encode('utf-8')
            
            # Get status
            status = page.url  # Simplified
            
            return Response(
                url=req.url,
                status=200,  # Simplified
                body=body_bytes,
                headers={},
                request=req,
                elapsed=0.0
            )
        except Exception as e:
            logger.error(f"Error rendering {req.url}: {e}")
            return None