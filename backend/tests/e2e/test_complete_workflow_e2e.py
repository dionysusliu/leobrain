"""Complete workflow E2E tests"""
import pytest
import asyncio
from sqlmodel import select
from common.models import Content
from common.storage import get_storage_service
from crawlers.core.engine import CrawlerEngine
from crawlers.spiders.rss_spider import RSSSpider
from crawlers.core.pipelines import StoragePipeline
from tests.utils import load_fixture


@pytest.mark.e2e
class TestCompleteWorkflowE2E:
    """Complete workflow tests: API -> Crawl -> DB -> MinIO -> API"""
    
    @pytest.mark.asyncio
    async def test_complete_workflow(
        self,
        async_client,
        e2e_db_session,
        e2e_storage_service,
        mock_fetcher_for_e2e
    ):
        """Test complete workflow: trigger crawl -> verify DB -> verify MinIO -> query via API"""
        # Step 1: Trigger crawl (if scheduler is available)
        # For now, we'll directly test the crawl flow
        rss_content = load_fixture("bbc_technology_rss.xml")
        
        # Step 2: Run crawl directly
        spider = RSSSpider(
            source_name="workflow_test",
            feed_url="http://feeds.bbci.co.uk/news/technology/rss.xml",
            max_items=3
        )
        
        pipeline = StoragePipeline(session=e2e_db_session)
        pipeline.storage = e2e_storage_service
        
        engine = CrawlerEngine(pipeline=pipeline)
        engine.fetcher.fetch = mock_fetcher_for_e2e
        
        count = await engine.crawl_spider(spider, {
            "source_name": "workflow_test",
            "qps": 1.0
        })
        
        assert count > 0
        
        # Step 3: Verify in database
        statement = select(Content).where(Content.source == "workflow_test")
        contents = e2e_db_session.exec(statement).all()
        assert len(contents) == count
        
        # Step 4: Verify in MinIO
        for content in contents:
            assert e2e_storage_service.object_exists(content.body_ref)
            downloaded = e2e_storage_service.download_content(content.body_ref)
            assert len(downloaded) > 0
        
        # Step 5: Query via API
        response = await async_client.get("/api/v1/contents/?source=workflow_test")
        assert response.status_code == 200
        api_contents = response.json()
        assert len(api_contents) == count
        
        # Step 6: Verify API data matches DB data
        api_urls = {item["url"] for item in api_contents}
        db_urls = {content.url for content in contents}
        assert api_urls == db_urls
        
        # Step 7: Get individual content via API
        if contents:
            first_content = contents[0]
            response = await async_client.get(f"/api/v1/contents/{first_content.id}")
            assert response.status_code == 200
            api_content = response.json()
            assert api_content["id"] == first_content.id
            assert api_content["url"] == first_content.url
            assert api_content["body_ref"] == first_content.body_ref
        
        await engine.close()
    
    @pytest.mark.asyncio
    async def test_data_consistency_across_services(
        self,
        e2e_db_session,
        e2e_storage_service,
        mock_fetcher_for_e2e
    ):
        """Test data consistency across database and MinIO"""
        from crawlers.core.engine import CrawlerEngine
        from crawlers.spiders.rss_spider import RSSSpider
        from crawlers.core.pipelines import StoragePipeline
        
        spider = RSSSpider(
            source_name="consistency_test",
            feed_url="http://feeds.bbci.co.uk/news/technology/rss.xml",
            max_items=2
        )
        
        pipeline = StoragePipeline(session=e2e_db_session)
        pipeline.storage = e2e_storage_service
        
        engine = CrawlerEngine(pipeline=pipeline)
        engine.fetcher.fetch = mock_fetcher_for_e2e
        
        count = await engine.crawl_spider(spider, {
            "source_name": "consistency_test",
            "qps": 1.0
        })
        
        assert count > 0
        
        # Verify consistency
        statement = select(Content).where(Content.source == "consistency_test")
        contents = e2e_db_session.exec(statement).all()
        
        for content in contents:
            # DB should have UUID
            assert content.content_uuid is not None
            
            # MinIO object should exist
            assert e2e_storage_service.object_exists(content.body_ref)
            
            # UUID should be in object name
            assert content.content_uuid in content.body_ref
            
            # Download and verify content is not empty
            downloaded = e2e_storage_service.download_content(content.body_ref)
            assert downloaded is not None
            assert len(downloaded) > 0
        
        await engine.close()

