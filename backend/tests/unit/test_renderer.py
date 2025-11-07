"""Tests for renderer implementations"""
import pytest
from crawlers.core.renderer import NoopRenderer, IRenderer
from crawlers.core.types import Request


@pytest.mark.unit
class TestNoopRenderer:
    """Tests for NoopRenderer"""
    
    @pytest.mark.asyncio
    async def test_noop_renderer_returns_none(self):
        """Test that NoopRenderer returns None"""
        renderer = NoopRenderer()
        
        req = Request(url="http://example.com")
        result = await renderer.render(req)
        
        assert result is None
    
    def test_noop_renderer_is_irenderer(self):
        """Test that NoopRenderer implements IRenderer"""
        renderer = NoopRenderer()
        assert isinstance(renderer, IRenderer)


@pytest.mark.unit
@pytest.mark.skip(reason="Playwright requires browser installation")
class TestPlaywrightRenderer:
    """Tests for PlaywrightRenderer (requires Playwright)"""
    
    @pytest.mark.asyncio
    async def test_playwright_renderer_start(self):
        """Test PlaywrightRenderer start"""
        from crawlers.core.renderer import PlaywrightRenderer
        
        renderer = PlaywrightRenderer(headless=True)
        
        try:
            await renderer.start()
            assert renderer.browser is not None
            assert renderer.context is not None
        finally:
            await renderer.close()
    
    @pytest.mark.asyncio
    async def test_playwright_renderer_render(self):
        """Test PlaywrightRenderer render"""
        from crawlers.core.renderer import PlaywrightRenderer
        
        renderer = PlaywrightRenderer(headless=True)
        
        try:
            req = Request(url="http://example.com")
            resp = await renderer.render(req)
            
            assert resp is not None
            assert resp.url == req.url
            assert resp.status == 200
            assert len(resp.body) > 0
        finally:
            await renderer.close()
    
    @pytest.mark.asyncio
    async def test_playwright_renderer_close(self):
        """Test PlaywrightRenderer close"""
        from crawlers.core.renderer import PlaywrightRenderer
        
        renderer = PlaywrightRenderer(headless=True)
        
        await renderer.start()
        assert renderer.browser is not None
        
        await renderer.close()
        # Browser should be closed (we can't easily verify this without accessing internals)

