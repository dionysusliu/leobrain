"""Test utility functions"""
from pathlib import Path
from typing import Optional
import json


def load_fixture(filename: str) -> str:
    """Load a fixture file"""
    fixture_path = Path(__file__).parent / "fixtures" / filename
    with open(fixture_path, 'r', encoding='utf-8') as f:
        return f.read()


def create_mock_response(
    url: str,
    content: str,
    status: int = 200,
    content_type: str = "text/html"
) -> dict:
    """Create a mock HTTP response dict"""
    return {
        "url": url,
        "status": status,
        "content": content.encode('utf-8'),
        "headers": {
            "Content-Type": content_type,
            "Content-Length": str(len(content.encode('utf-8')))
        }
    }


def assert_item_valid(item, source: Optional[str] = None):
    """Assert that an item has all required fields"""
    assert item.url, "Item must have URL"
    assert item.title, "Item must have title"
    assert item.body, "Item must have body"
    assert item.source, "Item must have source"
    if source:
        assert item.source == source, f"Item source should be {source}"
