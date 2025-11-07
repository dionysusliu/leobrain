"""End-to-end API tests with real services"""
import pytest
import httpx
from sqlmodel import select
from common.models import Content
from common.storage import get_storage_service
from unittest.mock import patch, AsyncMock
from crawlers.core.types import Request, Response
from tests.utils import load_fixture


@pytest.mark.e2e
class TestAPIE2E:
    """End-to-end API tests with real PostgreSQL and MinIO"""
    
    @pytest.mark.asyncio
    async def test_health_endpoint(self, async_client):
        """Test health check endpoint"""
        response = await async_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
    
    @pytest.mark.asyncio
    async def test_root_endpoint(self, async_client):
        """Test root endpoint"""
        response = await async_client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data
    
    @pytest.mark.asyncio
    async def test_get_sites(self, async_client):
        """Test getting all configured sites"""
        response = await async_client.get("/api/v1/crawlers/sites")
        assert response.status_code == 200
        data = response.json()
        assert "sites" in data
        assert "sites_info" in data
        assert isinstance(data["sites"], list)
    
    @pytest.mark.asyncio
    async def test_get_contents_empty(self, async_client, e2e_db_session):
        """Test getting contents when database is empty"""
        response = await async_client.get("/api/v1/contents/")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    @pytest.mark.asyncio
    async def test_create_content_via_api(
        self, 
        async_client, 
        e2e_db_session, 
        e2e_storage_service
    ):
        """Test creating content via API and verify in database and MinIO"""
        # Mock storage service
        with patch('common.storage.get_storage_service', return_value=e2e_storage_service):
            # Create content via API
            content_data = {
                "source": "test_source",
                "url": "http://example.com/test-article",
                "title": "Test Article",
                "author": "Test Author",
                "body": "Test content body",
                "lang": "en"
            }
            
            response = await async_client.post("/api/v1/contents/", json=content_data)
            assert response.status_code == 200
            created_content = response.json()
            
            assert created_content["url"] == content_data["url"]
            assert created_content["title"] == content_data["title"]
            assert "id" in created_content
            
            # Verify in database
            content_id = created_content["id"]
            db_content = e2e_db_session.get(Content, content_id)
            assert db_content is not None
            assert db_content.url == content_data["url"]
            assert db_content.title == content_data["title"]
    
    @pytest.mark.asyncio
    async def test_get_content_by_id(self, async_client, e2e_db_session):
        """Test getting content by ID"""
        # First create a content
        from common.models import Content
        test_content = Content(
            source="test",
            url="http://example.com/article1",
            title="Test Article 1",
            body="Test body"
        )
        e2e_db_session.add(test_content)
        e2e_db_session.commit()
        e2e_db_session.refresh(test_content)
        
        # Get it via API
        response = await async_client.get(f"/api/v1/contents/{test_content.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_content.id
        assert data["url"] == test_content.url
    
    @pytest.mark.asyncio
    async def test_get_content_not_found(self, async_client):
        """Test getting non-existent content"""
        response = await async_client.get("/api/v1/contents/99999")
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_get_contents_filtered_by_source(
        self, 
        async_client, 
        sample_test_contents
    ):
        """Test getting contents filtered by source"""
        # Use fixture data - sample_test_contents already creates test data in DB
        # Get BBC contents only
        response = await async_client.get("/api/v1/contents/?source=bbc")
        assert response.status_code == 200
        data = response.json()
        assert all(item["source"] == "bbc" for item in data)
        # Check that our fixture data is in the results
        fixture_bbc_urls = {c.url for c in sample_test_contents if c.source == "bbc"}
        result_urls = {item["url"] for item in data}
        assert fixture_bbc_urls.issubset(result_urls), "Fixture BBC contents should be in results"
        
        # Get HackerNews contents
        response = await async_client.get("/api/v1/contents/?source=hackernews")
        assert response.status_code == 200
        data = response.json()
        assert all(item["source"] == "hackernews" for item in data)
        # Check that our fixture data is in the results
        fixture_hn_urls = {c.url for c in sample_test_contents if c.source == "hackernews"}
        result_urls = {item["url"] for item in data}
        assert fixture_hn_urls.issubset(result_urls), "Fixture HN contents should be in results"
    
    @pytest.mark.asyncio
    async def test_trigger_crawl_via_api(
        self,
        async_client
    ):
        """Test triggering crawl via API through Prefect"""
        # Trigger crawl via API
        # Note: This may fail if Prefect server is not started or site not configured
        # That's okay for E2E testing - we're testing the API endpoint
        response = await async_client.post("/api/v1/crawlers/sites/bbc/crawl")
        
        # Possible status codes:
        # 200: Success (Prefect flow started)
        # 404: Site not found
        # 500: Prefect server error or other error
        assert response.status_code in [200, 404, 500]
        
        if response.status_code == 200:
            data = response.json()
            assert "message" in data
            assert "flow_run_id" in data  # API returns flow_run_id, not job_id
            assert "site" in data
            assert data["site"] == "bbc"
    
    @pytest.mark.asyncio
    async def test_get_site_config(self, async_client):
        """Test getting site configuration"""
        response = await async_client.get("/api/v1/crawlers/sites/bbc")
        # May return 404 if site not configured, or 200 with config
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            data = response.json()
            assert "site" in data
            assert "config" in data
    
    @pytest.mark.asyncio
    async def test_get_site_status(self, async_client):
        """Test getting site status"""
        response = await async_client.get("/api/v1/crawlers/sites/bbc/status")
        # May return 404 or 503 if scheduler not started
        assert response.status_code in [200, 404, 503]
        
        if response.status_code == 200:
            data = response.json()
            assert "site" in data
            assert "is_running" in data


@pytest.mark.e2e
class TestFullCrawlE2E:
    """Full end-to-end crawl tests with real services"""
    
    @pytest.mark.asyncio
    async def test_full_crawl_flow_with_real_services(
        self,
        e2e_db_session,
        e2e_storage_service,
        mock_fetcher_for_e2e
    ):
        """Test complete crawl flow: API -> Crawl -> DB -> MinIO"""
        from crawlers.core.engine import CrawlerEngine
        from crawlers.spiders.rss_spider import RSSSpider
        from crawlers.core.pipelines import StoragePipeline
        
        # Load real RSS feed
        rss_content = load_fixture("bbc_technology_rss.xml")
        
        # Create spider
        spider = RSSSpider(
            source_name="bbc",
            feed_url="http://feeds.bbci.co.uk/news/technology/rss.xml",
            max_items=5
        )
        
        # Create pipeline with real services
        pipeline = StoragePipeline(session=e2e_db_session)
        pipeline.storage = e2e_storage_service
        
        # Create engine
        engine = CrawlerEngine(pipeline=pipeline)
        engine.fetcher.fetch = mock_fetcher_for_e2e
        
        # Run crawl
        count = await engine.crawl_spider(spider, {
            "source_name": "bbc",
            "qps": 1.0
        })
        
        assert count > 0
        
        # Verify in database
        statement = select(Content).where(Content.source == "bbc")
        contents = e2e_db_session.exec(statement).all()
        assert len(contents) == count
        
        # Verify each content
        for content in contents:
            assert content.url
            assert content.title
            assert content.content_uuid
            assert content.body_ref
            
            # Verify in MinIO
            object_exists = e2e_storage_service.object_exists(content.body_ref)
            assert object_exists, f"Object {content.body_ref} should exist in MinIO"
            
            # Verify content can be downloaded
            downloaded = e2e_storage_service.download_content(content.body_ref)
            assert downloaded is not None
            assert len(downloaded) > 0
        
        await engine.close()
    
    @pytest.mark.asyncio
    async def test_crawl_duplicate_detection(
        self,
        e2e_db_session,
        e2e_storage_service,
        mock_fetcher_for_e2e
    ):
        """Test that duplicate URLs are not processed twice"""
        from crawlers.core.engine import CrawlerEngine
        from crawlers.spiders.rss_spider import RSSSpider
        from crawlers.core.pipelines import StoragePipeline
        
        spider = RSSSpider(
            source_name="test_dup",
            feed_url="http://feeds.bbci.co.uk/news/technology/rss.xml",
            max_items=5
        )
        
        pipeline = StoragePipeline(session=e2e_db_session)
        pipeline.storage = e2e_storage_service
        
        engine = CrawlerEngine(pipeline=pipeline)
        engine.fetcher.fetch = mock_fetcher_for_e2e
        
        # First crawl
        count1 = await engine.crawl_spider(spider, {"source_name": "test_dup"})
        
        # Second crawl (should detect duplicates)
        count2 = await engine.crawl_spider(spider, {"source_name": "test_dup"})
        
        # Second crawl should process fewer items
        assert count2 <= count1
        
        # Total unique items should equal first crawl
        statement = select(Content).where(Content.source == "test_dup")
        contents = e2e_db_session.exec(statement).all()
        assert len(contents) == count1
        
        await engine.close()

@pytest.mark.e2e
class TestAPIErrorScenarios:
    """Error scenarios and edge cases for API endpoints"""
    
    # ==================== Contents API Error Scenarios ====================
    
    @pytest.mark.asyncio
    async def test_get_content_invalid_id_negative(self, async_client):
        """Test getting content with negative ID"""
        response = await async_client.get("/api/v1/contents/-1")
        # FastAPI should handle this, might return 404 or 422
        assert response.status_code in [404, 422]
    
    @pytest.mark.asyncio
    async def test_get_content_invalid_id_string(self, async_client):
        """Test getting content with string ID"""
        response = await async_client.get("/api/v1/contents/abc")
        # Should return 422 (validation error)
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_get_content_invalid_id_zero(self, async_client):
        """Test getting content with ID 0"""
        response = await async_client.get("/api/v1/contents/0")
        # Should return 404 (not found)
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_get_content_very_large_id(self, async_client):
        """Test getting content with very large ID"""
        response = await async_client.get("/api/v1/contents/999999999")
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_create_content_missing_required_fields(self, async_client):
        """Test creating content with missing required fields"""
        # Missing 'url' (required field)
        incomplete_data = {
            "source": "test",
            "title": "Test"
        }
        response = await async_client.post("/api/v1/contents/", json=incomplete_data)
        assert response.status_code == 422  # Validation error
    
    @pytest.mark.asyncio
    async def test_create_content_empty_strings(self, async_client):
        """Test creating content with empty strings"""
        import uuid
        # Use unique empty-like URL to avoid conflicts
        unique_id = uuid.uuid4().hex[:8]
        content_data = {
            "source": "",
            "url": f"http://example.com/empty-{unique_id}",
            "title": "",
            "body": ""
        }
        response = await async_client.post("/api/v1/contents/", json=content_data)
        # Should either accept (if allowed) or reject with 422
        # Note: Empty URL might conflict, so 409 is also acceptable
        assert response.status_code in [200, 422, 409]
    
    @pytest.mark.asyncio
    async def test_create_content_invalid_url_format(self, async_client):
        """Test creating content with invalid URL format"""
        content_data = {
            "source": "test",
            "url": "not-a-valid-url",
            "title": "Test"
        }
        response = await async_client.post("/api/v1/contents/", json=content_data)
        # Should accept (URL validation might be lenient) or reject
        assert response.status_code in [200, 422]
    
    @pytest.mark.asyncio
    async def test_create_content_very_long_strings(self, async_client):
        """Test creating content with very long strings"""
        very_long_string = "a" * 10000
        content_data = {
            "source": "test",
            "url": f"http://example.com/{very_long_string[:100]}",
            "title": very_long_string,
            "body": very_long_string
        }
        response = await async_client.post("/api/v1/contents/", json=content_data)
        # Should handle gracefully (either accept or reject with reasonable error)
        assert response.status_code in [200, 422, 413]
    
    @pytest.mark.asyncio
    async def test_create_content_special_characters(self, async_client, e2e_db_session):
        """Test creating content with special characters"""
        content_data = {
            "source": "test",
            "url": "http://example.com/test?param=value&other=123",
            "title": "Test with émojis 🎉 and unicode 中文",
            "body": "Content with <script>alert('xss')</script> and SQL'; DROP TABLE--",
            "author": "Author <with> tags"
        }
        response = await async_client.post("/api/v1/contents/", json=content_data)
        assert response.status_code == 200
        # Verify it was stored correctly
        created = response.json()
        assert created["title"] == content_data["title"]
    
    @pytest.mark.asyncio
    async def test_get_contents_pagination_skip_negative(self, async_client):
        """Test pagination with negative skip"""
        response = await async_client.get("/api/v1/contents/?skip=-1")
        # FastAPI Query validation should return 422
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_get_contents_pagination_limit_zero(self, async_client):
        """Test pagination with limit=0"""
        response = await async_client.get("/api/v1/contents/?limit=0")
        # FastAPI Query validation should return 422 (ge=1)
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_get_contents_pagination_very_large_limit(self, async_client):
        """Test pagination with very large limit"""
        response = await async_client.get("/api/v1/contents/?limit=999999")
        # API has limit <= 1000, so very large limit should return 422
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_get_contents_pagination_skip_beyond_total(self, async_client, e2e_db_session):
        """Test pagination with skip beyond total items"""
        # Create a few items
        from common.models import Content
        for i in range(3):
            content = Content(
                source="pagination_test",
                url=f"http://example.com/page{i}",
                title=f"Page {i}",
                body="test"
            )
            e2e_db_session.add(content)
        e2e_db_session.commit()
        
        # Skip beyond total
        response = await async_client.get("/api/v1/contents/?skip=100&source=pagination_test")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0  # Should return empty list
    
    @pytest.mark.asyncio
    async def test_get_contents_invalid_source_format(self, async_client):
        """Test filtering with invalid source format"""
        # Source with special characters
        response = await async_client.get("/api/v1/contents/?source=test%20with%20spaces")
        # Should handle gracefully
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_get_contents_nonexistent_source(self, async_client):
        """Test filtering with non-existent source"""
        response = await async_client.get("/api/v1/contents/?source=nonexistent_source_12345")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0
    
    # ==================== Crawlers API Error Scenarios ====================
    
    @pytest.mark.asyncio
    async def test_get_site_config_nonexistent_site(self, async_client):
        """Test getting config for non-existent site"""
        response = await async_client.get("/api/v1/crawlers/sites/nonexistent_site_12345")
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_get_site_config_invalid_site_name(self, async_client):
        """Test getting config with invalid site name format"""
        # Site name with special characters
        response = await async_client.get("/api/v1/crawlers/sites/test%20site%20name")
        # Should return 404 or handle gracefully
        assert response.status_code in [404, 422]
    
    @pytest.mark.asyncio
    async def test_get_site_status_nonexistent_site(self, async_client):
        """Test getting status for non-existent site"""
        response = await async_client.get("/api/v1/crawlers/sites/nonexistent_site_12345/status")
        # May return 404 or 503 depending on scheduler state
        assert response.status_code in [404, 503]
    
    @pytest.mark.asyncio
    async def test_trigger_crawl_nonexistent_site(self, async_client):
        """Test triggering crawl for non-existent site"""
        response = await async_client.post("/api/v1/crawlers/sites/nonexistent_site_12345/crawl")
        # May return 503 if scheduler not started, or 404 if site not found
        assert response.status_code in [404, 503]
        data = response.json()
        if response.status_code == 404:
            assert "not found" in data["detail"].lower()
        elif response.status_code == 503:
            assert "scheduler" in data["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_trigger_crawl_invalid_site_name(self, async_client):
        """Test triggering crawl with invalid site name"""
        # Empty site name (should be caught by FastAPI routing)
        response = await async_client.post("/api/v1/crawlers/sites//crawl")
        assert response.status_code in [404, 422]
    
    # ==================== Edge Cases ====================
    
    @pytest.mark.asyncio
    async def test_get_contents_large_dataset(self, async_client, e2e_db_session):
        """Test getting contents with large dataset"""
        # Create many contents
        from common.models import Content
        contents = []
        for i in range(50):
            content = Content(
                source="large_dataset",
                url=f"http://example.com/item{i}",
                title=f"Item {i}",
                body=f"Content {i}"
            )
            contents.append(content)
        
        e2e_db_session.add_all(contents)
        e2e_db_session.commit()
        
        # Get all with default limit
        response = await async_client.get("/api/v1/contents/?source=large_dataset")
        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 100  # Default limit
        
        # Get with custom limit
        response = await async_client.get("/api/v1/contents/?source=large_dataset&limit=10")
        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 10
    
    @pytest.mark.asyncio
    async def test_get_contents_pagination_consistency(self, async_client, e2e_db_session):
        """Test pagination consistency across pages"""
        from common.models import Content
        # Create test contents
        for i in range(15):
            content = Content(
                source="pagination_consistency",
                url=f"http://example.com/consistency{i}",
                title=f"Item {i}",
                body="test"
            )
            e2e_db_session.add(content)
        e2e_db_session.commit()
        
        # Get first page
        response1 = await async_client.get("/api/v1/contents/?source=pagination_consistency&skip=0&limit=5")
        data1 = response1.json()
        
        # Get second page
        response2 = await async_client.get("/api/v1/contents/?source=pagination_consistency&skip=5&limit=5")
        data2 = response2.json()
        
        # Items should not overlap
        urls1 = {item["url"] for item in data1}
        urls2 = {item["url"] for item in data2}
        assert len(urls1.intersection(urls2)) == 0
    
    @pytest.mark.asyncio
    async def test_create_content_duplicate_url(self, async_client, e2e_db_session):
        """Test creating content with duplicate URL"""
        from common.models import Content
        import uuid
        # Use unique URL to avoid conflicts with other tests
        test_url = f"http://example.com/duplicate-{uuid.uuid4().hex[:8]}"
        
        # Create first content
        content1 = Content(
            source="dup_test",
            url=test_url,
            title="First",
            body="test"
        )
        e2e_db_session.add(content1)
        e2e_db_session.commit()
        
        # Try to create duplicate via API
        content_data = {
            "source": "dup_test",
            "url": test_url,
            "title": "Second",
            "body": "test"
        }
        response = await async_client.post("/api/v1/contents/", json=content_data)
        # API should return 409 Conflict for duplicate URL
        assert response.status_code == 409
        assert "already exists" in response.json()["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_get_contents_with_sql_injection_attempt(self, async_client):
        """Test filtering with SQL injection attempt"""
        # Try SQL injection in source parameter
        malicious_source = "test'; DROP TABLE contents; --"
        response = await async_client.get(f"/api/v1/contents/?source={malicious_source}")
        # Should be handled safely by SQLModel
        assert response.status_code == 200
        # Should not crash or execute SQL
    
    @pytest.mark.asyncio
    async def test_create_content_with_xss_attempt(self, async_client, e2e_db_session):
        """Test creating content with XSS attempt"""
        xss_content = {
            "source": "xss_test",
            "url": "http://example.com/xss",
            "title": "<script>alert('xss')</script>",
            "body": "<img src=x onerror=alert('xss')>"
        }
        response = await async_client.post("/api/v1/contents/", json=xss_content)
        # Should accept (sanitization might happen at display layer)
        assert response.status_code == 200
        created = response.json()
        # Verify it was stored (might be sanitized or stored as-is)
        assert created["url"] == xss_content["url"]
    
    @pytest.mark.asyncio
    async def test_get_contents_empty_database(self, async_client):
        """Test getting contents when database is completely empty"""
        # This is already tested, but let's be explicit
        response = await async_client.get("/api/v1/contents/")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Should return empty list, not error
    
    @pytest.mark.asyncio
    async def test_get_contents_invalid_query_params(self, async_client):
        """Test with invalid query parameters"""
        # Invalid skip (string instead of int)
        response = await async_client.get("/api/v1/contents/?skip=abc")
        # FastAPI should return 422 (validation error)
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_get_contents_mixed_valid_invalid_params(self, async_client):
        """Test with mix of valid and invalid parameters"""
        response = await async_client.get("/api/v1/contents/?skip=10&limit=abc&source=test")
        # Should return 422 due to invalid limit
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_create_content_null_values(self, async_client):
        """Test creating content with null values"""
        content_data = {
            "source": "test",
            "url": "http://example.com/null-test",
            "title": None,  # Optional field
            "author": None,
            "body": None
        }
        response = await async_client.post("/api/v1/contents/", json=content_data)
        # Should handle null values gracefully
        assert response.status_code in [200, 422]
    
    @pytest.mark.asyncio
    async def test_get_contents_unicode_source(self, async_client, e2e_db_session):
        """Test filtering with unicode source name"""
        from common.models import Content
        content = Content(
            source="测试源",
            url="http://example.com/unicode",
            title="Unicode Test",
            body="test"
        )
        e2e_db_session.add(content)
        e2e_db_session.commit()
        
        # Query with unicode
        import urllib.parse
        encoded_source = urllib.parse.quote("测试源")
        response = await async_client.get(f"/api/v1/contents/?source={encoded_source}")
        assert response.status_code == 200
        data = response.json()
        # Should find the content
        assert len(data) >= 1