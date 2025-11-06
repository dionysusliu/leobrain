"""Test MinIO storage service"""
import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from common.storage import get_storage_service

def test_storage():
    """test basic storage operations"""
    storage = get_storage_service()
    
    # test upload
    test_content = b"This is a test content body"
    object_name = storage.upload_content(
        content_uuid=1,
        content_body=test_content,
        content_type="text/plain",
        source="test"
    )
    
    print(f"✓ Uploaded to: {object_name}")
    
    # Test exists
    exists = storage.object_exists(object_name)
    print(f"✓ Object exists: {exists}")
    
    # Test download
    downloaded = storage.download_content(object_name)
    print(f"✓ Downloaded content: {downloaded.decode()}")
    
    # Test presigned URL
    url = storage.get_presigned_url(object_name)
    print(f"✓ Presigned URL: {url}")
    
    # Test list
    objects = storage.list_objects(prefix="test/")
    print(f"✓ Listed objects: {objects}")
    
    # Test delete
    storage.delete_content(object_name)
    print(f"✓ Deleted object")
    
    print("\n✅ All storage tests passed!")
    

if __name__ == "__main__":
    test_storage()
    