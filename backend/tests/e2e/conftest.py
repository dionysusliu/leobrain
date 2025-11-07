"""E2E test configuration and fixtures"""
import pytest
import os
import sys
from pathlib import Path
import httpx
from contextlib import asynccontextmanager
import asyncio
import time

# Add backend to path
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from fastapi import FastAPI
from app.main import app
from common.database import get_session, init_db, DATABASE_URL
from common.storage import StorageService, get_storage_service
from sqlmodel import create_engine, SQLModel, Session, select
from unittest.mock import patch, AsyncMock
from crawlers.core.types import Request, Response


# ==================== Docker Services Management ====================

def check_docker_services():
    """Check if docker services are running"""
    import subprocess
    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=leobrain-", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            timeout=5
        )
        running_services = result.stdout.strip().split('\n')
        running_services = [s for s in running_services if s]
        return running_services
    except Exception:
        return []


@pytest.fixture(scope="session")
def docker_services_required():
    """Check if docker services are required and available"""
    required_services = ["leobrain-postgres", "leobrain-minio"]
    running_services = check_docker_services()
    
    missing_services = [s for s in required_services if s not in running_services]
    
    if missing_services:
        pytest.skip(
            f"Docker services not running: {missing_services}. "
            f"Please start them with: docker compose up -d"
        )
    
    return running_services


@pytest.fixture(scope="session")
def prefect_api_url():
    """Get Prefect API URL from environment or use default"""
    return os.getenv("PREFECT_API_URL", "http://localhost:4200/api")


@pytest.fixture(scope="session")
def prefect_server_required(prefect_api_url):
    """Check if Prefect server is available (optional for some tests)"""
    import subprocess
    
    # Check if Prefect server container is running
    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=leobrain-prefect-server", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if "leobrain-prefect-server" not in result.stdout:
            pytest.skip("Prefect server container is not running. Start it with: docker compose up -d prefect-server")
    except Exception:
        pytest.skip("Cannot check Prefect server status")
    
    # Check if Prefect API is accessible
    try:
        response = httpx.get(f"{prefect_api_url}/health", timeout=5)
        if response.status_code != 200:
            pytest.skip(f"Prefect server is not healthy (status: {response.status_code})")
    except Exception as e:
        pytest.skip(f"Cannot connect to Prefect server at {prefect_api_url}: {e}")


# ==================== Database Fixtures ====================

@pytest.fixture(scope="function")
def e2e_db_session(docker_services_required):
    """Create database session for E2E tests using real PostgreSQL"""
    # Use test database URL (should point to test database)
    test_db_url = os.getenv("TEST_DATABASE_URL", DATABASE_URL)
    
    # Create engine
    engine = create_engine(test_db_url, echo=False)
    
    # Create tables
    SQLModel.metadata.create_all(engine)
    
    # Create session
    with Session(engine) as session:
        yield session
        # Cleanup: rollback any uncommitted changes
        session.rollback()
        # Clean up ALL test data to ensure test isolation
        from common.models import Content
        try:
            # Delete all test contents by URL pattern or source
            # This ensures complete test isolation
            test_url_patterns = [
                "http://example.com/",
                "http://test.example.com/",
            ]
            test_sources = [
                "test", "test_source", "test_dup", "test_db", "test_query", 
                "test_update", "test_uuid", "dup_test", "pagination_test",
                "pagination_consistency", "large_dataset", "xss_test",
                "workflow_test", "consistency_test", "source_a", "source_b",
                "bbc", "hackernews", "hackernews_test"
            ]
            
            # Delete by URL patterns
            from sqlalchemy import func
            for pattern in test_url_patterns:
                # Use SQLAlchemy's like function
                statement = select(Content).where(func.lower(Content.url).like(f"{pattern.lower()}%"))
                test_contents = session.exec(statement).all()
                for content in test_contents:
                    session.delete(content)
            
            # Delete by source
            for source in test_sources:
                statement = select(Content).where(Content.source == source)
                test_contents = session.exec(statement).all()
                for content in test_contents:
                    session.delete(content)
            
            session.commit()
        except Exception as e:
            session.rollback()
            # Don't fail test on cleanup errors, but log them
            import logging
            logging.warning("Failed to clean up test data: %s", e)


# ==================== Storage Fixtures ====================

@pytest.fixture(scope="function")
def e2e_storage_service(docker_services_required):
    """Create real MinIO storage service for E2E tests"""
    service = StorageService(
        endpoint=os.getenv("TEST_MINIO_ENDPOINT", "localhost:9000"),
        access_key=os.getenv("TEST_MINIO_ACCESS_KEY", "minioadmin"),
        secret_key=os.getenv("TEST_MINIO_SECRET_KEY", "minioadmin"),
        bucket_name=os.getenv("TEST_MINIO_BUCKET", "leobrain-content-test"),
        secure=False
    )
    
    yield service
    
    # Cleanup: optionally delete test objects
    # This would require listing and deleting objects created during test


# ==================== FastAPI App Fixtures ====================

@pytest.fixture(scope="function")
def test_app():
    """Create FastAPI app instance for testing"""
    # Use the actual app but with test database
    return app


@pytest.fixture(scope="function")
async def async_client(test_app):
    """Create async HTTP client for testing FastAPI app"""
    transport = httpx.ASGITransport(app=test_app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver"
    ) as client:
        yield client


@pytest.fixture(scope="function")
def sync_client(test_app):
    """Create sync HTTP client for testing FastAPI app"""
    from fastapi.testclient import TestClient
    return TestClient(test_app)


# ==================== Test Data Fixtures ====================

@pytest.fixture
def sample_test_contents(e2e_db_session):
    """Create sample test contents for API testing with unique URLs"""
    from common.models import Content
    import uuid
    
    # Use UUID in URLs to ensure uniqueness across test runs
    test_id = str(uuid.uuid4())[:8]
    
    contents = []
    # Create BBC contents
    for i in range(3):
        content = Content(
            source="bbc",
            url=f"http://example.com/bbc-{test_id}-{i}",
            title=f"BBC Article {i}",
            body=f"Test body for BBC article {i}"
        )
        contents.append(content)
    
    # Create HackerNews contents
    for i in range(3):
        content = Content(
            source="hackernews",
            url=f"http://example.com/hn-{test_id}-{i}",
            title=f"HN Article {i}",
            body=f"Test body for HN article {i}"
        )
        contents.append(content)
    
    # Add to database
    for content in contents:
        e2e_db_session.add(content)
    e2e_db_session.commit()
    
    # Refresh to get IDs
    for content in contents:
        e2e_db_session.refresh(content)
    
    return contents


# ==================== Mock Fetcher for E2E ====================

@pytest.fixture
def mock_fetcher_for_e2e():
    """Mock fetcher that returns real RSS feed data"""
    from tests.utils import load_fixture
    
    async def mock_fetch(req: Request) -> Response:
        """Mock fetch that returns fixture data based on URL"""
        # Map URLs to fixture files
        url_to_fixture = {
            "http://feeds.bbci.co.uk/news/technology/rss.xml": "bbc_technology_rss.xml",
            "http://feeds.bbci.co.uk/news/rss.xml": "bbc_technology_rss.xml",  # Add main BBC feed
            "https://hnrss.org/frontpage": "hackernews_rss.xml",
            "https://www.reutersagency.com/feed/": "reuters_rss.xml",
        }
        
        # Check if URL matches any known feed
        for url_pattern, fixture_name in url_to_fixture.items():
            if url_pattern in req.url or req.url.endswith(fixture_name):
                try:
                    content = load_fixture(fixture_name)
                    return Response(
                        url=req.url,
                        status=200,
                        body=content.encode('utf-8'),
                        headers={"Content-Type": "application/rss+xml"},
                        request=req
                    )
                except FileNotFoundError:
                    pass
        
        # Default: return empty response
        return Response(
            url=req.url,
            status=200,
            body=b"<html>Test</html>",
            headers={},
            request=req
        )
    
    return mock_fetch


# ==================== Wait for Services ====================

@pytest.fixture(scope="session", autouse=True)
def wait_for_services(docker_services_required):
    """Wait for docker services to be ready"""
    import subprocess
    
    # Wait for PostgreSQL
    max_retries = 30
    for i in range(max_retries):
        try:
            result = subprocess.run(
                ["docker", "exec", "leobrain-postgres", "pg_isready", "-U", "leobrain"],
                capture_output=True,
                timeout=5
            )
            if result.returncode == 0:
                break
        except Exception:
            pass
        time.sleep(1)
    else:
        pytest.fail("PostgreSQL service not ready after 30 seconds")
    
    # Wait for MinIO
    import httpx as sync_httpx
    for i in range(max_retries):
        try:
            response = sync_httpx.get("http://localhost:9000/minio/health/live", timeout=2)
            if response.status_code == 200:
                break
        except Exception:
            pass
        time.sleep(1)
    else:
        pytest.fail("MinIO service not ready after 30 seconds")
    
    yield

