"""Pytest configuration and shared fixtures"""
import pytest
import sys
from pathlib import Path
from typing import Generator
import asyncio
from unittest.mock import Mock, AsyncMock
import tempfile
import shutil

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlmodel import SQLModel, create_engine, Session
from crawlers.core.types import Request, Response, Item
from crawlers.core.fetcher import HttpxFetcher
from crawlers.core.pipelines import StoragePipeline
from common.models import Content
from common.storage import StorageService


# ==================== Database Fixtures ====================

@pytest.fixture(scope="session")
def test_db_url():
    """Test database URL - use SQLite in-memory for fast tests"""
    return "sqlite:///:memory:"


@pytest.fixture(scope="function")
def test_engine(test_db_url):
    """Create test database engine"""
    engine = create_engine(test_db_url, echo=False)
    SQLModel.metadata.create_all(engine)
    yield engine
    SQLModel.metadata.drop_all(engine)


@pytest.fixture(scope="function")
def test_session(test_engine):
    """Create test database session"""
    with Session(test_engine) as session:
        yield session
        session.rollback()


@pytest.fixture(scope="function")
def mock_get_session(test_session):
    """Mock get_session function"""
    def _get_session():
        yield test_session
    return _get_session


# ==================== Storage Fixtures ====================

@pytest.fixture(scope="function")
def temp_minio_dir():
    """Create temporary directory for MinIO testing"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture(scope="function")
def mock_storage_service(monkeypatch):
    """Mock storage service for testing"""
    mock_storage = Mock(spec=StorageService)
    
    # Make upload_content use the actual content_uuid passed to it
    def upload_content_side_effect(content_uuid, content_body, content_type="text/plain", source=None):
        if source:
            return f"{source}/{content_uuid}.txt"
        else:
            return f"content/{content_uuid}.txt"
    
    mock_storage.upload_content = Mock(side_effect=upload_content_side_effect)
    mock_storage.download_content = Mock(return_value=b"test content")
    mock_storage.delete_content = Mock()
    mock_storage.object_exists = Mock(return_value=False)
    mock_storage.list_objects = Mock(return_value=[])
    
    # Monkey patch get_storage_service
    from common import storage
    original_get = storage.get_storage_service
    monkeypatch.setattr(storage, "get_storage_service", lambda: mock_storage)
    
    yield mock_storage
    
    # Restore original
    monkeypatch.setattr(storage, "get_storage_service", original_get)


# ==================== HTTP Fixtures ====================

@pytest.fixture(scope="function")
def mock_httpx_response():
    """Create mock HTTP response"""
    def _create_response(
        url: str = "http://example.com",
        status: int = 200,
        content: bytes = b"<html>Test</html>",
        headers: dict = None
    ):
        response = Mock()
        response.url = url
        response.status_code = status
        response.content = content
        response.text = content.decode('utf-8', errors='ignore')
        response.headers = headers or {}
        response.raise_for_status = Mock()
        return response
    return _create_response


@pytest.fixture(scope="function")
def mock_fetcher(monkeypatch):
    """Mock HTTP fetcher"""
    async def mock_fetch(req):
        # Return a mock response
        response = Response(
            url=req.url,
            status=200,
            body=b"<html>Test</html>",
            headers={},
            request=req
        )
        return response
    
    fetcher = Mock(spec=HttpxFetcher)
    fetcher.fetch = AsyncMock(side_effect=mock_fetch)
    fetcher.close = AsyncMock()
    
    return fetcher


# ==================== RSS Fixtures ====================

@pytest.fixture
def sample_rss_feed():
    """Sample RSS feed XML"""
    return """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
    <channel>
        <title>Test Feed</title>
        <link>http://example.com</link>
        <description>Test RSS Feed</description>
        <item>
            <title>Test Article 1</title>
            <link>http://example.com/article1</link>
            <description>This is the first test article description.</description>
            <pubDate>Mon, 01 Jan 2024 12:00:00 GMT</pubDate>
            <author>Test Author</author>
        </item>
        <item>
            <title>Test Article 2</title>
            <link>http://example.com/article2</link>
            <description>This is the second test article description.</description>
            <pubDate>Tue, 02 Jan 2024 12:00:00 GMT</pubDate>
            <author>Another Author</author>
        </item>
    </channel>
</rss>"""


@pytest.fixture
def sample_rss_response(sample_rss_feed):
    """Create Response object from sample RSS feed"""
    return Response(
        url="http://example.com/feed.xml",
        status=200,
        body=sample_rss_feed.encode('utf-8'),
        headers={"Content-Type": "application/rss+xml"},
        request=Request(url="http://example.com/feed.xml", metadata={"is_feed": True})
    )


# ==================== HTML Fixtures ====================

@pytest.fixture
def sample_html():
    """Sample HTML content"""
    return """<!DOCTYPE html>
<html>
<head>
    <title>Test Article</title>
</head>
<body>
    <article>
        <h1>Test Article Title</h1>
        <div class="author">John Doe</div>
        <time datetime="2024-01-01T12:00:00Z">January 1, 2024</time>
        <div class="content">
            <p>This is the first paragraph of the article.</p>
            <p>This is the second paragraph with more content.</p>
        </div>
    </article>
    <script>console.log('test');</script>
    <style>.hidden { display: none; }</style>
</body>
</html>"""


@pytest.fixture
def sample_html_response(sample_html):
    """Create Response object from sample HTML"""
    return Response(
        url="http://example.com/article",
        status=200,
        body=sample_html.encode('utf-8'),
        headers={"Content-Type": "text/html"},
        request=Request(url="http://example.com/article", metadata={"fetch_full": True})
    )


# ==================== Item Fixtures ====================

@pytest.fixture
def sample_item():
    """Sample crawled item"""
    from datetime import datetime
    return Item(
        url="http://example.com/article",
        title="Test Article",
        body="This is a test article body with some content.",
        source="test_source",
        author="Test Author",
        published_at=datetime(2024, 1, 1, 12, 0, 0),
        metadata={"test": True}
    )


@pytest.fixture
def sample_items():
    """Multiple sample items"""
    from datetime import datetime
    return [
        Item(
            url=f"http://example.com/article{i}",
            title=f"Article {i}",
            body=f"Content for article {i}",
            source="test_source",
            published_at=datetime(2024, 1, i, 12, 0, 0)
        )
        for i in range(1, 4)
    ]


# ==================== Spider Fixtures ====================

@pytest.fixture
def rss_spider():
    """Create RSS spider instance for testing"""
    from crawlers.spiders.rss_spider import RSSSpider
    return RSSSpider(
        source_name="test_source",
        feed_url="http://example.com/feed.xml",
        max_items=10,
        fetch_full_content=False
    )


# ==================== Engine Fixtures ====================

@pytest.fixture
def crawler_engine(mock_fetcher, mock_storage_service):
    """Create crawler engine with mocked dependencies"""
    from crawlers.core.engine import CrawlerEngine
    from crawlers.core.pipelines import StoragePipeline
    
    # Create pipeline with mocked storage
    pipeline = StoragePipeline()
    pipeline.storage = mock_storage_service
    
    engine = CrawlerEngine(
        fetcher=mock_fetcher,
        pipeline=pipeline
    )
    return engine


# ==================== Async Fixtures ====================

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ==================== Config Fixtures ====================

@pytest.fixture
def test_site_config():
    """Test site configuration"""
    return {
        "spider": "rss",
        "source_name": "test_source",
        "feed_url": "http://example.com/feed.xml",
        "cron": "*/10 * * * *",
        "qps": 1.0,
        "concurrency": 2,
        "max_items": 10,
        "fetch_full_content": False,
        "headers": {
            "User-Agent": "TestBot/1.0"
        },
        "use_render": False
    }


# ==================== Utility Functions ====================

@pytest.fixture
def cleanup_db(test_session):
    """Cleanup database after test"""
    yield
    # Clean up all content
    test_session.query(Content).delete()
    test_session.commit()


@pytest.fixture
def real_bbc_rss():
    """Load real BBC RSS feed if available"""
    try:
        from tests.utils import load_fixture
        return load_fixture("bbc_technology_rss.xml")
    except FileNotFoundError:
        pytest.skip("Real BBC RSS feed not found. Run download_real_data.py first")


@pytest.fixture
def real_article_html():
    """Load real article HTML if available"""
    try:
        from tests.utils import load_fixture
        return load_fixture("real_article_1.html")
    except FileNotFoundError:
        pytest.skip("Real article HTML not found. Run download_real_data.py first")

@pytest.fixture
def hackernews_rss_content():
    """Load Hacker News RSS feed content"""
    from tests.utils import load_fixture
    try:
        return load_fixture("hackernews_rss.xml")
    except FileNotFoundError:
        pytest.skip("Hacker News RSS feed not found")


@pytest.fixture
def reuters_rss_content():
    """Load Reuters RSS feed content"""
    from tests.utils import load_fixture
    try:
        return load_fixture("reuters_rss.xml")
    except FileNotFoundError:
        pytest.skip("Reuters RSS feed not found")
