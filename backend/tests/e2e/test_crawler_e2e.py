"""End-to-end tests for crawler system"""
import pytest
from crawlers.core.engine import CrawlerEngine, load_site_configs
from crawlers.spiders.rss_spider import RSSSpider
from tests.utils import load_fixture


@pytest.mark.e2e
class TestCrawlerE2E:
    """End-to-end tests"""
    
    @pytest.mark.asyncio
    async def test_e2e_bbc_crawl(self, test_session, mock_storage_service):
        """End-to-end test: BBC crawl from config to storage"""
        # Load real RSS
        rss_content = load_fixture("bbc_technology_rss.xml")
        
        # Create spider from config
        config = {
            "spider": "rss",
            "source_name": "bbc",
            "feed_url": "http://feeds.bbci.co.uk/news/technology/rss.xml",
            "max_items": 5,
            "fetch_full_content": False,
            "qps": 1.0
        }
        
        spider = RSSSpider(
            source_name=config["source_name"],
            feed_url=config["feed_url"],
            max_items=config["max_items"]
        )
        
        # Create engine with real pipeline
        from crawlers.core.pipelines import StoragePipeline
        pipeline = StoragePipeline(session=test_session)
        pipeline.storage = mock_storage_service
        
        engine = CrawlerEngine(pipeline=pipeline)
        
        # Mock HTTP fetch
        from crawlers.core.types import Response, Request
        async def mock_fetch(req):
            return Response(
                url=req.url,
                status=200,
                body=rss_content.encode('utf-8'),
                headers={},
                request=req
            )
        
        engine.fetcher.fetch = mock_fetch
        
        # Execute crawl
        count = await engine.crawl_spider(spider, config)
        
        # Verify results
        assert count > 0
        
        # Verify database
        from common.models import Content
        from sqlmodel import select
        statement = select(Content).where(Content.source == "bbc")
        contents = test_session.exec(statement).all()
        assert len(contents) == count
        
        # Verify storage was called
        assert mock_storage_service.upload_content.call_count == count
        
        # Verify each content has UUID and body_ref
        for content in contents:
            assert content.content_uuid
            assert content.body_ref
            # Verify UUID is in object name
            assert content.content_uuid in content.body_ref
        
        await engine.close()
    
    @pytest.mark.asyncio
    async def test_e2e_multiple_sources(self, test_session, mock_storage_service):
        """End-to-end test: Crawl multiple sources"""
        from crawlers.core.types import Response
        
        sources = [
            ("bbc_technology_rss.xml", "bbc"),
            ("hackernews_rss.xml", "hackernews"),
        ]
        
        from crawlers.core.pipelines import StoragePipeline
        pipeline = StoragePipeline(session=test_session)
        pipeline.storage = mock_storage_service
        
        engine = CrawlerEngine(pipeline=pipeline)
        
        total_count = 0
        
        for filename, source_name in sources:
            rss_content = load_fixture(filename)
            
            spider = RSSSpider(
                source_name=source_name,
                feed_url=f"http://example.com/{filename}",
                max_items=3
            )
            
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
                "source_name": source_name,
                "qps": 1.0
            })
            
            total_count += count
        
        # Verify all sources were processed
        assert total_count > 0
        
        from common.models import Content
        from sqlmodel import select
        bbc_statement = select(Content).where(Content.source == "bbc")
        bbc_contents = test_session.exec(bbc_statement).all()
        hn_statement = select(Content).where(Content.source == "hackernews")
        hn_contents = test_session.exec(hn_statement).all()
        
        assert len(bbc_contents) > 0
        assert len(hn_contents) > 0
        
        await engine.close()
