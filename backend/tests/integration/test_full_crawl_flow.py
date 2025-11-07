"""Integration tests for full crawl flow"""
import pytest
from crawlers.core.engine import CrawlerEngine
from crawlers.spiders.rss_spider import RSSSpider
from crawlers.core.pipelines import StoragePipeline
from tests.utils import load_fixture
from common.models import Content


@pytest.mark.integration
class TestFullCrawlFlow:
    """Test complete crawl flow from RSS to database"""
    
    @pytest.mark.asyncio
    async def test_full_crawl_bbc(self, test_session, mock_storage_service):
        """Test full crawl flow with BBC RSS"""
        from crawlers.core.types import Response, Request
        
        # Setup
        rss_content = load_fixture("bbc_technology_rss.xml")
        spider = RSSSpider(
            source_name="bbc",
            feed_url="http://feeds.bbci.co.uk/news/technology/rss.xml",
            max_items=5
        )
        
        # Create pipeline with test session
        pipeline = StoragePipeline(session=test_session)
        pipeline.storage = mock_storage_service
        
        # Create engine
        engine = CrawlerEngine(pipeline=pipeline)
        
        # Mock fetcher
        async def mock_fetch(req):
            return Response(
                url=req.url,
                status=200,
                body=rss_content.encode('utf-8'),
                headers={},
                request=req
            )
        
        engine.fetcher.fetch = mock_fetch
        
        # Run crawl
        count = await engine.crawl_spider(spider, {
            "source_name": "bbc",
            "qps": 1.0,
            "delay": 0.1
        })
        
        # Verify
        assert count > 0, "Should process at least one item"
        
        # Check database - use session.exec
        from sqlmodel import select
        statement = select(Content).where(Content.source == "bbc")
        contents = test_session.exec(statement).all()
        assert len(contents) == count
        
        # Verify content properties
        for content in contents:
            assert content.url
            assert content.title
            assert content.body_ref  # Should have MinIO reference
            assert content.content_uuid  # Should have UUID
        
        await engine.close()
    
    @pytest.mark.asyncio
    async def test_full_crawl_hackernews(self, test_session, mock_storage_service):
        """Test full crawl flow with Hacker News RSS"""
        from crawlers.core.types import Response
        
        rss_content = load_fixture("hackernews_rss.xml")
        spider = RSSSpider(
            source_name="hackernews",
            feed_url="https://hnrss.org/frontpage",
            max_items=5
        )
        
        pipeline = StoragePipeline(session=test_session)
        pipeline.storage = mock_storage_service
        
        engine = CrawlerEngine(pipeline=pipeline)
        
        async def mock_fetch(req):
            return Response(
                url=req.url,
                status=200,
                body=rss_content.encode('utf-8'),
                headers={},
                request=req
            )
        
        engine.fetcher.fetch = mock_fetch
        
        count = await engine.crawl_spider(spider, {
            "source_name": "hackernews",
            "qps": 1.0
        })
        
        assert count > 0
        
        from sqlmodel import select
        statement = select(Content).where(Content.source == "hackernews")
        contents = test_session.exec(statement).all()
        assert len(contents) == count
        
        await engine.close()
    
    @pytest.mark.asyncio
    async def test_full_crawl_with_duplicate_detection(self, test_session, mock_storage_service):
        """Test that duplicate URLs are not processed twice"""
        from crawlers.core.types import Response
        
        rss_content = load_fixture("bbc_technology_rss.xml")
        spider = RSSSpider(
            source_name="bbc",
            feed_url="http://feeds.bbci.co.uk/news/technology/rss.xml",
            max_items=5
        )
        
        pipeline = StoragePipeline(session=test_session)
        pipeline.storage = mock_storage_service
        
        engine = CrawlerEngine(pipeline=pipeline)
        
        async def mock_fetch(req):
            return Response(
                url=req.url,
                status=200,
                body=rss_content.encode('utf-8'),
                headers={},
                request=req
            )
        
        engine.fetcher.fetch = mock_fetch
        
        # First crawl
        count1 = await engine.crawl_spider(spider, {"source_name": "bbc"})
        
        # Second crawl (should detect duplicates)
        count2 = await engine.crawl_spider(spider, {"source_name": "bbc"})
        
        # Second crawl should process fewer items (duplicates skipped)
        assert count2 <= count1
        
        # Total unique items should equal first crawl
        from sqlmodel import select
        statement = select(Content).where(Content.source == "bbc")
        contents = test_session.exec(statement).all()
        assert len(contents) == count1
        
        await engine.close()
