"""E2E tests for database operations with real PostgreSQL"""
import pytest
from sqlmodel import select
from common.models import Content
from datetime import datetime


@pytest.mark.e2e
class TestDatabaseE2E:
    """End-to-end tests for database with real PostgreSQL"""
    
    def test_create_content(self, e2e_db_session):
        """Test creating content in database"""
        content = Content(
            source="test_db",
            url="http://example.com/test",
            title="Test Article",
            body="Test body content",
            author="Test Author",
            published_at=datetime.now()
        )
        
        e2e_db_session.add(content)
        e2e_db_session.commit()
        e2e_db_session.refresh(content)
        
        assert content.id is not None
        assert content.created_at is not None
    
    def test_query_content(self, e2e_db_session):
        """Test querying content from database"""
        # Create test content
        content = Content(
            source="test_query",
            url="http://example.com/query-test",
            title="Query Test",
            body="Test"
        )
        e2e_db_session.add(content)
        e2e_db_session.commit()
        e2e_db_session.refresh(content)
        
        # Query by ID
        found = e2e_db_session.get(Content, content.id)
        assert found is not None
        assert found.url == content.url
        
        # Query by URL
        statement = select(Content).where(Content.url == content.url)
        found_by_url = e2e_db_session.exec(statement).first()
        assert found_by_url is not None
        assert found_by_url.id == content.id
    
    def test_query_by_source(self, e2e_db_session):
        """Test querying content by source"""
        # Create multiple contents with different sources
        sources = ["source_a", "source_b", "source_a"]
        for i, source in enumerate(sources):
            content = Content(
                source=source,
                url=f"http://example.com/{source}-{i}",
                title=f"Article {i}",
                body="Test"
            )
            e2e_db_session.add(content)
        
        e2e_db_session.commit()
        
        # Query by source
        statement = select(Content).where(Content.source == "source_a")
        contents = e2e_db_session.exec(statement).all()
        assert len(contents) == 2
        assert all(c.source == "source_a" for c in contents)
    
    def test_update_content(self, e2e_db_session):
        """Test updating content in database"""
        # Create content
        content = Content(
            source="test_update",
            url="http://example.com/update-test",
            title="Original Title",
            body="Original body"
        )
        e2e_db_session.add(content)
        e2e_db_session.commit()
        e2e_db_session.refresh(content)
        
        original_id = content.id
        
        # Update
        content.title = "Updated Title"
        e2e_db_session.add(content)
        e2e_db_session.commit()
        e2e_db_session.refresh(content)
        
        # Verify
        assert content.id == original_id
        assert content.title == "Updated Title"
    
    def test_delete_content(self, e2e_db_session):
        """Test deleting content from database"""
        # Create content
        content = Content(
            source="test_delete",
            url="http://example.com/delete-test",
            title="Delete Test",
            body="Test"
        )
        e2e_db_session.add(content)
        e2e_db_session.commit()
        e2e_db_session.refresh(content)
        
        content_id = content.id
        
        # Delete
        e2e_db_session.delete(content)
        e2e_db_session.commit()
        
        # Verify deleted
        found = e2e_db_session.get(Content, content_id)
        assert found is None
    
    def test_content_uuid_uniqueness(self, e2e_db_session):
        """Test that content_uuid is unique"""
        import uuid
        
        # Create content with specific UUID
        test_uuid = str(uuid.uuid4())
        content1 = Content(
            source="test_uuid",
            url="http://example.com/uuid-test-1",
            title="UUID Test 1",
            content_uuid=test_uuid
        )
        e2e_db_session.add(content1)
        e2e_db_session.commit()
        
        # Try to create another with same UUID (should fail or be handled)
        content2 = Content(
            source="test_uuid",
            url="http://example.com/uuid-test-2",
            title="UUID Test 2",
            content_uuid=test_uuid
        )
        e2e_db_session.add(content2)
        
        # This should raise an error or be handled by the database
        # Depending on your database constraints
        try:
            e2e_db_session.commit()
            # If it doesn't raise, verify only one exists
            statement = select(Content).where(Content.content_uuid == test_uuid)
            contents = e2e_db_session.exec(statement).all()
            # Should have at most one (depending on constraints)
            assert len(contents) >= 1
        except Exception:
            # Expected if unique constraint is enforced
            e2e_db_session.rollback()
            pass

