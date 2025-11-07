"""Tests for storage service"""
import pytest
from unittest.mock import Mock, patch
from common.storage import StorageService, get_storage_service


@pytest.mark.unit
class TestStorageService:
    """Tests for StorageService"""
    
    @pytest.fixture
    def mock_minio_client(self):
        """Create mock MinIO client"""
        mock_client = Mock()
        mock_client.bucket_exists.return_value = True
        mock_client.make_bucket.return_value = None
        mock_client.put_object.return_value = None
        mock_client.get_object.return_value = Mock()
        mock_client.stat_object.return_value = Mock()
        mock_client.remove_object.return_value = None
        mock_client.list_objects.return_value = []
        return mock_client
    
    @pytest.fixture
    def storage_service(self, mock_minio_client):
        """Create storage service with mocked MinIO client"""
        with patch('common.storage.Minio', return_value=mock_minio_client):
            service = StorageService(
                endpoint="localhost:9000",
                access_key="test",
                secret_key="test",
                bucket_name="test-bucket",
                secure=False
            )
            service.client = mock_minio_client
            return service
    
    def test_storage_service_init(self, mock_minio_client):
        """Test storage service initialization"""
        with patch('common.storage.Minio', return_value=mock_minio_client):
            service = StorageService(
                endpoint="localhost:9000",
                access_key="test",
                secret_key="test",
                bucket_name="test-bucket"
            )
            
            assert service.endpoint == "localhost:9000"
            assert service.access_key == "test"
            assert service.bucket_name == "test-bucket"
    
    def test_storage_service_ensure_bucket_exists(self, storage_service, mock_minio_client):
        """Test ensuring bucket when it already exists"""
        mock_minio_client.bucket_exists.return_value = True
        
        # Should not call make_bucket
        storage_service._ensure_bucket()
        mock_minio_client.make_bucket.assert_not_called()
    
    def test_storage_service_ensure_bucket_create(self, storage_service, mock_minio_client):
        """Test creating bucket when it doesn't exist"""
        mock_minio_client.bucket_exists.return_value = False
        
        storage_service._ensure_bucket()
        mock_minio_client.make_bucket.assert_called_once_with("test-bucket")
    
    def test_storage_service_upload_content(self, storage_service, mock_minio_client):
        """Test uploading content"""
        from io import BytesIO
        
        content_uuid = "test-uuid-123"
        content_body = b"test content"
        
        result = storage_service.upload_content(
            content_uuid=content_uuid,
            content_body=content_body,
            content_type="text/plain",
            source="test_source"
        )
        
        # Should return object name
        assert "test-uuid-123" in result
        assert "test_source" in result
        
        # Should call put_object
        mock_minio_client.put_object.assert_called_once()
        call_args = mock_minio_client.put_object.call_args
        # Check positional or keyword arguments
        if call_args[0]:
            assert call_args[0][0] == "test-bucket"
            assert call_args[0][1] == result
        else:
            assert call_args[1]["bucket_name"] == "test-bucket"
            assert call_args[1]["object_name"] == result
    
    def test_storage_service_download_content(self, storage_service, mock_minio_client):
        """Test downloading content"""
        from io import BytesIO
        
        # Mock get_object to return BytesIO with read method
        mock_stream = BytesIO(b"test content")
        # Add release_conn method that MinIO objects have
        mock_stream.release_conn = Mock()
        mock_minio_client.get_object.return_value = mock_stream
        
        result = storage_service.download_content("test/source/uuid-123.txt")
        
        assert result == b"test content"
        mock_minio_client.get_object.assert_called_once()
    
    def test_storage_service_delete_content(self, storage_service, mock_minio_client):
        """Test deleting content"""
        storage_service.delete_content("test/source/uuid-123.txt")
        
        # Check if called with positional or keyword args
        call_args = mock_minio_client.remove_object.call_args
        assert call_args is not None
        # Verify bucket and object_name are in the call
        # remove_object is called with (bucket_name, object_name) as positional args
        if len(call_args[0]) >= 2:
            assert call_args[0][0] == "test-bucket"
            assert call_args[0][1] == "test/source/uuid-123.txt"
        elif "bucket_name" in call_args[1]:
            assert call_args[1]["bucket_name"] == "test-bucket"
            assert call_args[1]["object_name"] == "test/source/uuid-123.txt"
        else:
            # Just verify it was called
            assert mock_minio_client.remove_object.called
    
    def test_storage_service_object_exists(self, storage_service, mock_minio_client):
        """Test checking if object exists"""
        mock_minio_client.stat_object.return_value = Mock()
        
        result = storage_service.object_exists("test/source/uuid-123.txt")
        
        assert result is True
        mock_minio_client.stat_object.assert_called_once()
    
    def test_storage_service_object_not_exists(self, storage_service, mock_minio_client):
        """Test checking if object doesn't exist"""
        from minio.error import S3Error
        
        # Mock S3Error for non-existent object
        mock_minio_client.stat_object.side_effect = S3Error(
            code="NoSuchKey",
            message="Object not found",
            resource="test-bucket/test/source/uuid-123.txt",
            request_id="test",
            host_id="test",
            response=Mock(status_code=404)
        )
        
        result = storage_service.object_exists("test/source/uuid-123.txt")
        
        assert result is False
    
    def test_storage_service_list_objects(self, storage_service, mock_minio_client):
        """Test listing objects"""
        from minio.commonconfig import Tags
        
        # Mock list_objects to return iterator
        mock_objects = [
            Mock(object_name="test/source/uuid-1.txt"),
            Mock(object_name="test/source/uuid-2.txt"),
        ]
        mock_minio_client.list_objects.return_value = mock_objects
        
        result = storage_service.list_objects(prefix="test/source/")
        
        assert len(result) == 2
        assert "test/source/uuid-1.txt" in result
        assert "test/source/uuid-2.txt" in result
    
    def test_get_storage_service(self):
        """Test get_storage_service function"""
        with patch.dict('os.environ', {
            'MINIO_ENDPOINT': 'localhost:9000',
            'MINIO_ACCESS_KEY': 'test',
            'MINIO_SECRET_KEY': 'test',
            'MINIO_BUCKET_NAME': 'test-bucket'
        }):
            with patch('common.storage.Minio') as mock_minio:
                service = get_storage_service()
                assert service is not None
                assert isinstance(service, StorageService)

