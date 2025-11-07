"""E2E tests for storage service with real MinIO"""
import pytest
from common.storage import StorageService
from common.models import Content
from sqlmodel import select


@pytest.mark.e2e
class TestStorageE2E:
    """End-to-end tests for storage service with real MinIO"""
    
    @pytest.mark.asyncio
    async def test_upload_and_download_content(self, e2e_storage_service):
        """Test uploading and downloading content from MinIO"""
        content_uuid = "test-uuid-e2e-123"
        content_body = b"This is test content for E2E testing"
        
        # Upload
        object_name = e2e_storage_service.upload_content(
            content_uuid=content_uuid,
            content_body=content_body,
            content_type="text/plain",
            source="test_source"
        )
        
        assert object_name is not None
        assert content_uuid in object_name
        
        # Verify object exists
        exists = e2e_storage_service.object_exists(object_name)
        assert exists is True
        
        # Download
        downloaded = e2e_storage_service.download_content(object_name)
        assert downloaded == content_body
        
        # Cleanup
        e2e_storage_service.delete_content(object_name)
        
        # Verify deleted
        exists_after = e2e_storage_service.object_exists(object_name)
        assert exists_after is False
    
    @pytest.mark.asyncio
    async def test_list_objects(self, e2e_storage_service):
        """Test listing objects in MinIO"""
        # Upload a few test objects
        test_objects = []
        for i in range(3):
            content_uuid = f"test-uuid-{i}"
            object_name = e2e_storage_service.upload_content(
                content_uuid=content_uuid,
                content_body=f"Test content {i}".encode(),
                source="test_list"
            )
            test_objects.append(object_name)
        
        # List objects
        objects = e2e_storage_service.list_objects(prefix="test_list/")
        assert len(objects) >= 3
        
        # Cleanup
        for obj_name in test_objects:
            e2e_storage_service.delete_content(obj_name)
    
    @pytest.mark.asyncio
    async def test_storage_with_database_integration(
        self,
        e2e_db_session,
        e2e_storage_service
    ):
        """Test storage integration with database"""
        from crawlers.core.pipelines import StoragePipeline
        from crawlers.core.types import Item
        from datetime import datetime
        
        # Create pipeline with real services
        pipeline = StoragePipeline(session=e2e_db_session)
        pipeline.storage = e2e_storage_service
        
        # Create test item
        test_item = Item(
            source="test_storage_db",
            url="http://example.com/storage-test",
            title="Storage DB Test",
            body="Test content for storage and DB integration",
            author="Test Author",
            published_at=datetime.now()
        )
        
        # Process item
        result = await pipeline.process_item(test_item)
        assert result is True
        
        # Verify in database
        statement = select(Content).where(Content.url == test_item.url)
        content = e2e_db_session.exec(statement).first()
        assert content is not None
        assert content.title == test_item.title
        assert content.body_ref is not None
        
        # Verify in MinIO
        exists = e2e_storage_service.object_exists(content.body_ref)
        assert exists is True
        
        # Download and verify content
        downloaded = e2e_storage_service.download_content(content.body_ref)
        assert test_item.body.encode('utf-8') in downloaded or test_item.body in downloaded.decode('utf-8')

