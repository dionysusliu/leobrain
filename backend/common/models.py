from datetime import datetime, timezone
from inspect import CO_ASYNC_GENERATOR
from typing import Optional
from pydantic import EmailStr
from sqlmodel import SQLModel, Field, Relationship, JSON, Column
import uuid


class ContentBase(SQLModel):
    ''' Contents scraped from Internet
    '''
    source: str = Field(index=True)
    url: str=Field(unique=True, index=True)
    title: str
    author: Optional[str] = None
    published_at: Optional[datetime] = None
    body_ref: Optional[str] = None
    lang: str = Field(default="en")
    content_uuid: str = Field(default_factory=lambda: str(uuid.uuid4()), unique=True, index=True) # UUID as object id
    

class Content(ContentBase, table=True):
    __tablename__ = "contents"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # relationships
    analysis_results: list["AnalysisResult"] = Relationship(back_populates="content")
    
    
class AnalysisResultBase(SQLModel):
    ''' ML analysis results of a content
    '''
    content_id: int = Field(foreign_key="contents.id")
    plugin: str = Field(index=True)
    version: str
    result_type: str
    payload: dict = Field(default={}, sa_column=Column(JSON))
    

class AnalysisResult(AnalysisResultBase, table=True):
    __tablename__ = "analysis_results"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Relationships
    content: Content = Relationship(back_populates="analysis_results")
    
    
class JobRunBase(SQLModel):
    ''' Job records
    '''
    job_name: str = Field(index=True)
    status: str = Field(default="pending")
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    error_log: Optional[str] = None
    

class JobRun(JobRunBase, table=True):
    __tablename__ = "job_runs"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))