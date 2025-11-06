"""Pipelines for processing items"""
import uuid
from abc import ABC, abstractmethod
from typing import List
import logging
from sqlmodel import Session, select
from datetime import datetime, timezone

from crawlers.core.types import Item
from common.models import Content
from common.database import get_session
from common.storage import get_storage_service

logger = logging.getLogger(__name__)


class IPipeline(ABC):
    """Pipeline interface"""

    @abstractmethod
    async def process_item(self, item: Item) -> bool:
        """Process a single item"""
        pass

    @abstractmethod
    async def process_items(self, items: List[Item]) -> int:
        """Process multiple items"""
        pass


class StoragePipeline(IPipeline):
    """Pipeline that stores items to DB and MinIO"""

    def __init__(self):
        self.storage = get_storage_service()

    
    async def process_item(self, item: Item) -> bool:
        """Process and store a single item"""
        try:
            # get database session 
            session_gen = get_session()
            session = next(session_gen)

            try:
                # check if content already exists 
                statement = select(Content).where(Content.url == item.url) 
                existing = session.exec(statement).first()

                if existing:
                    logger.debug(f"Content already exist: {item.url}")
                    return False
                
                # generate uuid for object
                content_uuid = str(uuid.uuid4())
                
                # Upload body to MinIO
                body_bytes = item.body.encode('utf-8')
                object_name = self.storage.upload_content(
                    content_uuid=content_uuid, # be updated after DB insertion
                    content_body=body_bytes,
                    content_type="text/plain",
                    source=item.source
                )

                # Create content record in DB with uuid and body_ref
                content = Content(
                    source=item.source,
                    url=item.url,
                    title=item.title,
                    author=item.author,
                    published_at=item.published_at,
                    body_ref=object_name,
                    content_uuid=content_uuid,  # Set the UUID
                    lang=item.metadata.get('lang', 'en')
                )
                session.add(content)
                session.commit()
                session.refresh(content)

                logger.info(f"Stored item: {item.title[:50]}... (UUID: {content_uuid}, DB ID: {content.id})")
                return True
            
            except Exception as e:
                # rollback on error
                session.rollback()
                logger.error(f"Error processing item {item.url}: {e}")
                return False

            finally:
                session.close()
        except Exception as e:
            logger.error(f"Error processing item {item.url}: {e}")
            return False

    
    async def process_items(self, items: List[Item]) -> int:
        """Process multiple items"""
        success_count = 0
        for item in items:
            if await self.process_item(item):
                success_count += 1
        return success_count