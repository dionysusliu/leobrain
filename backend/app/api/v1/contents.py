from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select
from typing import List
from common.database import get_session
from common.models import Content, ContentBase
from sqlalchemy.exc import IntegrityError


router = APIRouter()

@router.get("/", response_model=List[Content])
def get_contents(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    source: str = None,
    session: Session = Depends(get_session)
):
    """Get all contents with optional filtering"""
    statement = select(Content)
    if source:
        statement = statement.where(Content.source == source)
    statement = statement.offset(skip).limit(limit)
    contents = session.exec(statement).all()
    
    return contents


@router.get("/{content_id}", response_model=Content)
def get_content(content_id: int, session: Session = Depends(get_session)):
    """Get specific content by ID"""
    content = session.get(Content, content_id)
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    
    return content


@router.post("/", response_model=Content)
def create_content(content: ContentBase, session: Session = Depends(get_session)):
    """Create a new content entry"""
    db_content = Content(**content.model_dump())
    session.add(db_content)
    try:
        session.commit()
        session.refresh(db_content)
        return db_content
    except IntegrityError as e:
        session.rollback()
        # Check if it's a duplicate URL error
        if "url" in str(e.orig).lower() or "ix_contents_url" in str(e.orig):
            raise HTTPException(
                status_code=409,
                detail=f"Content with URL '{content.url}' already exists"
            )
        raise HTTPException(status_code=400, detail=str(e))
