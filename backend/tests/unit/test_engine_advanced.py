"""Advanced tests for CrawlerEngine"""
import pytest
from crawlers.core.engine import CrawlerEngine, load_site_configs
from crawlers.core.fetcher import HttpxFetcher
from crawlers.spiders.rss_spider import RSSSpider
from crawlers.core.types import Request, Response, Item
from crawlers.core.renderer import NoopRenderer, PlaywrightRenderer
from tests.utils import load_fixture


@pytest.mark.unit
class TestCrawlerEngineAdvanced:
    """Advanced tests for CrawlerEngine"""
    
    @pytest.mark.asyncio
    async def test_engine_with_renderer_request(self):
        """Test engine with use_render=True request"""
        from unittest.mock import Mock, AsyncMock
        
        # Create engine with PlaywrightRenderer
        renderer = Mock(spec=PlaywrightRenderer)
        renderer.render = AsyncMock(return_value=Response(
            url="http://example.com",
            status=200,
            body=b"<html>Rendered</html>",
            headers={},
            request=Request(url="http://example.com", use_render=True)
        ))
        
        engine = CrawlerEngine(renderer=renderer)
        
        # Create a spider that returns render request
        class TestSpider:
            name = "test"
            def seeds(self):
                return [Request(url="http://example.com", use_render=True)]
            def parse(self, resp):
                return [Item(url="http://example.com", title="Test", source="test", body="test")], []
        
        spider = TestSpider()
        
        # Mock pipeline
        pipeline = Mock()
        pipeline.process_items = AsyncMock(return_value=1)
        engine.pipeline = pipeline
        
        # Mock fetcher (should not be called)
        fetcher = Mock()
        fetcher.fetch = AsyncMock()
        engine.fetcher = fetcher
        
        count = await engine.crawl_spider(spider, {})
        
        # Should use renderer, not fetcher
        renderer.render.assert_called_once()
        fetcher.fetch.assert_not_called()
        assert count == 1
        
        await engine.close()
    
    @pytest.mark.asyncio
    async def test_engine_fetch_failure(self):
        """Test engine handling fetch failures"""
        from unittest.mock import Mock, AsyncMock
        
        engine = CrawlerEngine()
        
        # Mock fetcher to return None (failure)
        engine.fetcher.fetch = AsyncMock(return_value=None)
        
        class TestSpider:
            name = "test"
            def seeds(self):
                return [Request(url="http://example.com")]
            def parse(self, resp):
                return [], []
        
        spider = TestSpider()
        
        # Mock pipeline
        pipeline = Mock()
        pipeline.process_items = AsyncMock(return_value=0)
        engine.pipeline = pipeline
        
        count = await engine.crawl_spider(spider, {})
        
        # Should return 0 items (fetch failed)
        assert count == 0
        pipeline.process_items.assert_not_called()  # No items to process
        
        await engine.close()
    
    @pytest.mark.asyncio
    async def test_engine_with_parse_full_content(self):
        """Test engine calling parse_full_content"""
        from unittest.mock import Mock, AsyncMock
        
        engine = CrawlerEngine()
        
        # Mock fetcher
        engine.fetcher.fetch = AsyncMock(return_value=Response(
            url="http://example.com/article",
            status=200,
            body=b"<html>Full article</html>",
            headers={},
            request=Request(url="http://example.com/article", metadata={"fetch_full": True})
        ))
        
        class TestSpider:
            name = "test"
            def seeds(self):
                return [Request(url="http://example.com/feed")]
            def parse(self, resp):
                # Return items and follow-up request with fetch_full
                return [], [Request(url="http://example.com/article", metadata={"fetch_full": True})]
            def parse_full_content(self, resp):
                return [Item(url="http://example.com/article", title="Article", source="test", body="content")], []
        
        spider = TestSpider()
        
        # Mock pipeline
        pipeline = Mock()
        pipeline.process_items = AsyncMock(return_value=1)
        engine.pipeline = pipeline
        
        count = await engine.crawl_spider(spider, {})
        
        assert count == 1
        pipeline.process_items.assert_called_once()
        
        await engine.close()
    
    @pytest.mark.asyncio
    async def test_engine_no_items(self):
        """Test engine with no items parsed"""
        from unittest.mock import Mock, AsyncMock
        
        engine = CrawlerEngine()
        
        # Mock fetcher
        engine.fetcher.fetch = AsyncMock(return_value=Response(
            url="http://example.com",
            status=200,
            body=b"<html></html>",
            headers={},
            request=Request(url="http://example.com")
        ))
        
        class TestSpider:
            name = "test"
            def seeds(self):
                return [Request(url="http://example.com")]
            def parse(self, resp):
                return [], []  # No items
        
        spider = TestSpider()
        
        # Mock pipeline
        pipeline = Mock()
        pipeline.process_items = AsyncMock()
        engine.pipeline = pipeline
        
        count = await engine.crawl_spider(spider, {})
        
        # Should return 0, pipeline should not be called
        assert count == 0
        pipeline.process_items.assert_not_called()
        
        await engine.close()
    
    @pytest.mark.asyncio
    async def test_engine_with_anti_bot(self):
        """Test engine with anti-bot middleware"""
        from unittest.mock import Mock, AsyncMock
        
        engine = CrawlerEngine()
        
        # Mock fetcher
        engine.fetcher.fetch = AsyncMock(return_value=Response(
            url="http://example.com",
            status=200,
            body=b"<html></html>",
            headers={},
            request=Request(url="http://example.com")
        ))
        
        class TestSpider:
            name = "test"
            def seeds(self):
                return [Request(url="http://example.com")]
            def parse(self, resp):
                return [Item(url="http://example.com", title="Test", source="test", body="test")], []
        
        spider = TestSpider()
        
        # Mock pipeline
        pipeline = Mock()
        pipeline.process_items = AsyncMock(return_value=1)
        engine.pipeline = pipeline
        
        # Configure with anti-bot
        count = await engine.crawl_spider(spider, {"qps": 2.0, "delay": 0.1})
        
        # Should have anti-bot configured
        assert engine.anti_bot is not None
        assert count == 1
        
        await engine.close()
    
    @pytest.mark.asyncio
    async def test_engine_close(self):
        """Test engine close method"""
        from unittest.mock import Mock, AsyncMock
        
        # Test with HttpxFetcher
        real_fetcher = HttpxFetcher()
        real_fetcher.close = AsyncMock()
        engine = CrawlerEngine(fetcher=real_fetcher)
        
        await engine.close()
        real_fetcher.close.assert_called_once()
        
        # Test with PlaywrightRenderer
        renderer = Mock(spec=PlaywrightRenderer)
        renderer.close = AsyncMock()
        engine2 = CrawlerEngine(renderer=renderer)
        
        await engine2.close()
        renderer.close.assert_called_once()
    
    def test_load_site_configs(self):
        """Test load_site_configs function"""
        import tempfile
        import yaml
        from pathlib import Path
        
        # Create temporary config file
        config_data = {
            "bbc": {
                "spider": "rss",
                "feed_url": "http://example.com/feed",
                "cron": "*/10 * * * *"
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name
        
        try:
            configs = load_site_configs(temp_path)
            assert "bbc" in configs
            assert configs["bbc"]["spider"] == "rss"
        finally:
            Path(temp_path).unlink()
    
    def test_load_site_configs_default_path(self):
        """Test load_site_configs with default path"""
        # This will try to load from default location
        # If file doesn't exist, it will raise FileNotFoundError
        # We'll just test that the function exists and can be called
        try:
            configs = load_site_configs()
            assert isinstance(configs, dict)
        except FileNotFoundError:
            # Default config file doesn't exist, that's okay for testing
            pass

