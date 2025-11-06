"""RSS feed spider"""
from typing import List, Tuple
from datetime import datetime
import feedparser
from selectolax.parser import HTMLParser
import logging

from crawlers.core.base_spider import ISpider
from crawlers.core.types import Request, Response, Item
from crawlers.core.parser import Parser

logger = logging.getLogger(__name__)


class RSSSpider(ISpider):
    """RSS feed spider"""
    
    name = "rss"
    
    def __init__(
        self,
        source_name: str,
        feed_url: str,
        max_items: int = None,
        fetch_full_content: bool = False
    ):
        """
        Initialize RSS spider
        
        Args:
            source_name: Name of the source
            feed_url: URL of the RSS feed
            max_items: Maximum items to crawl (None for all)
            fetch_full_content: Whether to fetch full article content
        """
        self.source_name = source_name
        self.feed_url = feed_url
        self.max_items = max_items
        self.fetch_full_content = fetch_full_content
        self.parser = Parser()
    
    def seeds(self) -> List[Request]:
        """Generate initial request for RSS feed"""
        return [Request(
            url=self.feed_url,
            method="GET",
            metadata={"source": self.source_name}
        )]
    
    def parse(self, resp: Response) -> Tuple[List[Item], List[Request]]:
        """Parse RSS feed response"""
        items = []
        new_requests = []
        
        try:
            # Parse RSS feed
            feed = feedparser.parse(resp.text)
            
            if feed.bozo:
                logger.warning(f"Feed parsing warnings: {feed.bozo_exception}")
            
            entries = feed.entries[:self.max_items] if self.max_items else feed.entries
            
            for entry in entries:
                try:
                    url = entry.get('link', '')
                    title = entry.get('title', 'No title')
                    
                    # Extract content
                    body = self._extract_content(entry)
                    if body:
                        body = self.parser.clean_text(body)
                    
                    # Parse date
                    published_at = None
                    if hasattr(entry, 'published'):
                        published_at = self.parser.parse_date(entry.published)
                    elif hasattr(entry, 'updated'):
                        published_at = self.parser.parse_date(entry.updated)
                    
                    # Get author
                    author = None
                    if hasattr(entry, 'author'):
                        author = entry.author
                    elif hasattr(entry, 'author_detail') and hasattr(entry.author_detail, 'name'):
                        author = entry.author_detail.name
                    
                    item = Item(
                        url=url,
                        title=title,
                        body=body,
                        source=self.source_name,
                        author=author,
                        published_at=published_at,
                        metadata={
                            'feed_title': feed.feed.get('title', ''),
                            'feed_link': feed.feed.get('link', ''),
                        }
                    )
                    
                    items.append(item)
                    
                    # If fetch_full_content is enabled and body is short, add follow-up request
                    if self.fetch_full_content and url and len(body) < 500:
                        new_requests.append(Request(
                            url=url,
                            method="GET",
                            metadata={"source": self.source_name, "fetch_full": True}
                        ))
                    
                except Exception as e:
                    logger.error(f"Error processing entry: {e}")
                    continue
            
            logger.info(f"Parsed {len(items)} items from RSS feed")
            
        except Exception as e:
            logger.error(f"Error parsing RSS feed: {e}")
        
        return items, new_requests
    
    def _extract_content(self, entry) -> str:
        """Extract content from RSS entry"""
        # Try content first
        if hasattr(entry, 'content') and entry.content:
            for content_item in entry.content:
                if hasattr(content_item, 'value'):
                    return content_item.value
        
        # Try summary
        if hasattr(entry, 'summary'):
            return entry.summary
        
        # Try description
        if hasattr(entry, 'description'):
            return entry.description
        
        return ""
    
    def parse_full_content(self, resp: Response) -> Tuple[List[Item], List[Request]]:
        """Parse full article content (for follow-up requests)"""
        # This would be called for follow-up requests
        # For now, just extract the main content
        body = self.parser.clean_text(resp.text)
        
        # Extract title
        selector = self.parser.parse_selector(resp.text)
        title = self.parser.extract_text(selector, "h1") or "No title"
        
        item = Item(
            url=resp.url,
            title=title,
            body=body,
            source=self.source_name,
            metadata={"fetched_full": True}
        )
        
        return [item], []
