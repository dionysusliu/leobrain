"""Core data types for crawler framework"""
from dataclasses import dataclass, field
from decimal import DefaultContext
from optparse import Option
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


class RequestMethod(str, Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    

@dataclass
class Request:
    """HTTP request representation"""
    url: str
    method: RequestMethod = RequestMethod.GET
    headers: Optional[Dict[str, str]] = None
    params: Optional[Dict[str, str]] = None
    data: Optional[Any] = None 
    json: Optional[Dict[str, Any]] = None
    use_render: bool = False # Whether use browser rendering 
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Response:
    """HTTP response representation"""
    url: str
    status: str
    body: bytes
    headers: Dict[str, str]
    request: Request 
    elapsed: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property 
    def text(self) -> str:
        """Get response body as text"""
        return self.body.decode('utf-8', errors='ignore')

    @property
    def json(self) -> Any:
        """Parse response body as JSON"""
        import json
        return json.load(self.text)

@dataclass
class Item:
    """Crawled item (standardized output)"""
    url: str
    title: str
    body: str
    source: str
    author: Optional[str] = None
    published_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary""" 
        return {
            'url': self.url,
            'title': self.title,
            'body': self.body,
            'source': self.source,
            'author': self.author,
            'published_at': self.published_at.isoformat() if self.published_at else None,
            'metadata': self.metadata
        }