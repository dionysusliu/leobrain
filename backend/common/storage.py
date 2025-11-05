from minio import Minio
from minio.error import S3Error
from typing import Optional, BinaryIO
import os
from dotenv import load_dotenv
import logging
from datetime import timedelta


load_dotenv()

logger = logging.getLogger(__name__)


class StorageService:
    """MinIO storage service for storing content bodies"""
    
    def __init__(
        self,
        endpoint: Optional[str] = None,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        bucket_name: Optional[str] = None,
        secure: bool = False  
    ):
        """Initialize MinIO client

        Args:
            endpoint: MinIO server endpoint (e.g., 'localhost:9000')
            access_key: MinIO access key
            secret_key: MinIO secret key
            bucket_name: Default bucket name for content storage
            secure: Use HTTPS (False for local development)
        """
        self.endpoint = endpoint or os.getenv("MINIO_ENDPOINT", "localhost:9000")
        self.access_key = access_key or os.getenv("MINIO_ACCESS_KEY", "minioadmin")
        self.secret_key = secret_key or os.getenv("MINIO_SECRET_KEY", "minioadmin")
        self.bucket_name = bucket_name or os.getenv("MINIO_BUCKET_NAME", "leobrain-content")
        self.secure = secure if secure else os.getenv("MINIO_SECURE", "false").lower() == "true"
        
        # init the client
        self.client = Minio(
            self.endpoint,
            access_key=self.access_key,
            secret_key=self.secret_key,
            secure=self.secure
        )
        
        # ensure bucket exist
        self._ensure_bucket()
        
    
    def _ensure_bucket(self) -> None:
        """Create bucket if doesn't exist"""
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
                logger.info(f"Created bucket: {self.bucket_name}")
            else:
                logger.debug(f"Bucket {self.bucket_name} already exist")
        except S3Error as e:
            logger.error(f"Error ensuring bucket exist: {e}")
            raise
        
    
    def upload_content(
        self,
        content_id: int,
        content_body: bytes,
        content_type: str = "text/plain",
        source: Optional[str] = None
    ) -> str:
        """Upload content body to MinIO"""
        # generate object path
        if source:
            object_name = f"{source}/{content_id}.txt"
        else:
            object_name = f"content/{content_id}.txt"
            
        try:
            from io import BytesIO
            data = BytesIO(content_body)
            length = len(content_body)
            
            self.client.put_object(
                self.bucket_name,
                object_name,
                data,
                length,
                content_type=content_type
            )
            
            logger.info(f"Uploaded content {content_id} to {object_name}")
            return object_name
        
        except S3Error as e:
            logger.error(f"Error uploading content {content_id}: {e}")
            raise
        
    
    def download_content(self, object_name: str) -> bytes:
        """Download contents from MinIO"""
        try:
            response = self.client.get_object(self.bucket_name, object_name=object_name)
            content = response.read()
            response.close()
            response.release_conn()
            
            logger.info(f"Downloaded content from {object_name}")
            return content
        
        except S3Error as e:
            logger.error(f"Error downloading content {object_name}: {e}")
            raise
        
    
    def delete_content(self, object_name: str) -> None:
        """Delete content from MinIO"""
        try:
            self.client.remove_object(self.bucket_name, object_name=object_name)
            logger.info(f"Deleted content {object_name}")\
                
        except S3Error as e:
            logger.error(f"Error deleting content {object_name}: {e}")
            raise
        
    
    def get_presigned_url(
        self,
        object_name: str,
        expires: timedelta = timedelta(hours=1)
    ) -> str:
        """Generate a presigned URL for temporary access"""
        try:
            url = self.client.presigned_get_object(
                self.bucket_name,
                object_name=object_name,
                expires=expires
            )
            return url
        
        except S3Error as e:
            logger.error(f"Error generating presigned URL for {object_name}: {e}")
            raise
        
        
    def object_exists(self, object_name: str) -> bool:
        """Check if an object exists"""
        try:
            self.client.stat_object(self.bucket_name, object_name)
            return True
        except S3Error:
            return False
        
    
    def list_objects(self, prefix: Optional[str] = None) -> list:
        """List all objects in bucket"""
        try:
            objects = self.client.list_objects(
                self.bucket_name,
                prefix=prefix,
                recursive=True
            )
            return [obj.object_name for obj in objects]

        except S3Error as e:
            logger.error(f"Error listing objects with prefix {prefix}: {e}")
            return []
        

# Singleton Instance
_storage_service: Optional[StorageService] = None

def get_storage_service() -> StorageService:
    """Access Singleton storage service instance"""
    global _storage_service
    if _storage_service is None:
        _storage_service = StorageService()
    return _storage_service