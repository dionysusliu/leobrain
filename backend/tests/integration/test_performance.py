"""Performance tests"""
import pytest
import time
from crawlers.core.engine import CrawlerEngine
from crawlers.spiders.rss_spider import RSSSpider
from crawlers.core.pipelines import StoragePipeline
from tests.utils import load_fixture


@pytest.mark.integration
@pytest.mark.slow
class TestPerformance:
    """Performance and load tests"""
    
    @pytest.mark.asyncio
    async def test_crawl_performance(self, test_session, mock_storage_service, test_site_config):
        """Test crawl performance with real RSS feed"""
        from crawlers.core.types import Response
        
        rss_content = load_fixture("bbc_technology_rss.xml")
        spider = RSSSpider(
            source_name="bbc",
            feed_url="http://feeds.bbci.co.uk/news/technology/rss.xml",
            max_items=20
        )
        
        # Create pipeline with test session
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
        
        start_time = time.time()
        count = await engine.crawl_spider(spider, test_site_config)
        elapsed = time.time() - start_time
        
        assert count > 0
        # Should process items reasonably fast
        # Adjust threshold based on your requirements
        assert elapsed < 10.0, f"Crawl took {elapsed:.2f}s, expected < 10s"
        
        # Calculate items per second
        items_per_sec = count / elapsed if elapsed > 0 else 0
        print(f"Processed {count} items in {elapsed:.2f}s ({items_per_sec:.2f} items/sec)")
        
        await engine.close()
    
    @pytest.mark.asyncio
    async def test_concurrent_crawls(self, test_session, mock_storage_service):
        """Test concurrent crawling of multiple sources"""
        import asyncio
        from crawlers.core.types import Response
        
        sources = [
            ("bbc_technology_rss.xml", "bbc"),
            ("hackernews_rss.xml", "hackernews"),
            ("reuters_rss.xml", "reuters"),
        ]
        
        async def crawl_source(filename, source_name):
            rss_content = load_fixture(filename)
            spider = RSSSpider(
                source_name=source_name,
                feed_url=f"http://example.com/{filename}",
                max_items=5
            )
            
            # Create pipeline with test session for each crawl
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
                "source_name": source_name,
                "qps": 1.0
            })
            
            await engine.close()
            return count
        
        start_time = time.time()
        results = await asyncio.gather(*[
            crawl_source(filename, source_name)
            for filename, source_name in sources
        ])
        elapsed = time.time() - start_time
        
        total_items = sum(results)
        assert total_items > 0
        print(f"Processed {total_items} items from {len(sources)} sources in {elapsed:.2f}s")
