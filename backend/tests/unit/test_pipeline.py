"""Tests for pipeline"""
import pytest
from unittest.mock import Mock, patch
import uuid

from crawlers.core.pipelines import StoragePipeline
from crawlers.core.types import Item
from common.models import Content
from tests.utils import assert_item_valid


@pytest.mark.unit
class TestStoragePipeline:
    """Test storage pipeline"""
    
    @pytest.fixture
    def pipeline(self, mock_storage_service, mock_get_session):
        """Create pipeline with mocked dependencies"""
        pipeline = StoragePipeline()
        pipeline.storage = mock_storage_service
        
        # Mock get_session
        with patch('crawlers.core.pipelines.get_session', mock_get_session):
            yield pipeline
    
    @pytest.fixture
    def sample_item(self):
        """Sample item for testing"""
        from datetime import datetime
        return Item(
            url="http://example.com/article1",
            title="Test Article",
            body="This is a test article body.",
            source="test_source",
            author="Test Author",
            published_at=datetime(2024, 1, 1, 12, 0, 0),
            metadata={"lang": "en"}
        )
    
    @pytest.mark.asyncio
    async def test_process_item_success(self, pipeline, sample_item, test_session):
        """Test successful item processing"""
        result = await pipeline.process_item(sample_item)
        
        assert result is True
        
        # Check database record - use session.exec instead of session.query
        from sqlmodel import select
        statement = select(Content).where(Content.url == sample_item.url)
        content = test_session.exec(statement).first()
        assert content is not None
        assert content.title == sample_item.title
        assert content.source == sample_item.source
        assert content.body_ref is not None
        
        # Check storage was called
        pipeline.storage.upload_content.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_item_duplicate_url(self, pipeline, sample_item, test_session):
        """Test that duplicate URLs are not processed"""
        # Process first time
        result1 = await pipeline.process_item(sample_item)
        assert result1 is True
        
        # Process second time (duplicate)
        result2 = await pipeline.process_item(sample_item)
        assert result2 is False
        
        # Should only have one record
        from sqlmodel import select
        statement = select(Content).where(Content.url == sample_item.url)
        contents = test_session.exec(statement).all()
        assert len(contents) == 1
    
    @pytest.mark.asyncio
    async def test_process_item_generates_uuid(self, pipeline, sample_item, test_session):
        """Test that UUID is generated and used consistently"""
        result = await pipeline.process_item(sample_item)
        assert result is True
        
        from sqlmodel import select
        statement = select(Content).where(Content.url == sample_item.url)
        content = test_session.exec(statement).first()
        assert content.content_uuid is not None
        
        # Check UUID format
        try:
            uuid.UUID(content.content_uuid)
        except ValueError:
            pytest.fail("content_uuid is not a valid UUID")
        
        # Check UUID is used in MinIO object name
        # The mock should have been called with the UUID
        upload_calls = pipeline.storage.upload_content.call_args_list
        assert len(upload_calls) > 0
        
        # Get the UUID that was passed
        # call_args is a call object, use .args for positional args or .kwargs for keyword args
        call_args = upload_calls[0]
        # Check both positional and keyword arguments
        if call_args.args:
            called_uuid = call_args.args[0]  # First positional argument (content_uuid)
        else:
            called_uuid = call_args.kwargs.get('content_uuid')  # Keyword argument
        
        assert called_uuid == content.content_uuid, f"UUID mismatch: {called_uuid} != {content.content_uuid}"
        
        # Check object name contains UUID
        # The mock returns the object name based on the UUID passed
        source = call_args.kwargs.get('source', 'content')
        object_name = f"{source}/{called_uuid}.txt"
        assert content.content_uuid in object_name
        assert content.body_ref == object_name
    
    @pytest.mark.asyncio
    async def test_process_items_batch(self, pipeline, sample_items, test_session):
        """Test processing multiple items"""
        count = await pipeline.process_items(sample_items)
        
        assert count == len(sample_items)
        
        # Check all items in database
        from sqlmodel import select
        for item in sample_items:
            statement = select(Content).where(Content.url == item.url)
            content = test_session.exec(statement).first()
            assert content is not None
    
    @pytest.mark.asyncio
    async def test_process_item_storage_failure(self, pipeline, sample_item, test_session):
        """Test handling of storage failure"""
        # Make storage upload fail
        pipeline.storage.upload_content.side_effect = Exception("Storage error")
        
        result = await pipeline.process_item(sample_item)
        
        assert result is False
        
        # Should not have database record (rollback)
        from sqlmodel import select
        statement = select(Content).where(Content.url == sample_item.url)
        content = test_session.exec(statement).first()
        assert content is None
