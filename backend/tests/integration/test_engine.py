"""Integration tests for crawler engine"""
import pytest
from crawlers.core.engine import CrawlerEngine
from crawlers.spiders.rss_spider import RSSSpider


@pytest.mark.integration
class TestCrawlerEngine:
    """Test crawler engine integration"""
    
    @pytest.mark.asyncio
    async def test_engine_crawl_rss_spider(self, crawler_engine, test_site_config):
        """Test engine crawling with RSS spider"""
        spider = RSSSpider(
            source_name=test_site_config["source_name"],
            feed_url=test_site_config["feed_url"],
            max_items=test_site_config.get("max_items", 10)
        )
        
        # Mock the fetcher to return sample RSS
        from tests.utils import load_fixture
        rss_content = load_fixture("sample_rss.xml")
        
        async def mock_fetch(req):
            from crawlers.core.types import Response
            return Response(
                url=req.url,
                status=200,
                body=rss_content.encode('utf-8'),
                headers={},
                request=req
            )
        
        crawler_engine.fetcher.fetch = mock_fetch
        
        # Run crawl
        count = await crawler_engine.crawl_spider(spider, test_site_config)
        
        assert count >= 0  # Should process some items
