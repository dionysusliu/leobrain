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
            metadata={"source": self.source_name, "is_feed": True}
        )]
    
    def parse(self, resp: Response) -> Tuple[List[Item], List[Request]]:
        """Parse RSS feed response"""
        items = []
        new_requests = []
        
        # Check if this is actually a feed or a full article page
        # If metadata says it's a feed, parse as feed; otherwise parse as article
        is_feed = resp.request.metadata.get('is_feed', False)
        
        if not is_feed:
            # This is a full article page, use parse_full_content logic
            return self.parse_full_content(resp)
        
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
                            metadata={
                                "source": self.source_name,
                                "fetch_full": True,
                                "original_item_url": url  # Keep reference to original item
                            }
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
        """
        Parse full article content (for follow-up requests)
        
        This method is called when fetch_full_content=True and we're fetching
        the actual article page to get the full content.
        """
        try:
            # Extract main content from HTML
            body = self.parser.clean_text(resp.text)
            
            # Extract title - try multiple selectors
            selector = self.parser.parse_selector(resp.text)
            title = (
                self.parser.extract_text(selector, "h1") or
                self.parser.extract_text(selector, "title") or
                self.parser.extract_text(selector, ".article-title") or
                "No title"
            )
            
            # Try to extract article content specifically (not entire page)
            # Common article selectors
            article_body = (
                self.parser.extract_all_text(selector, "article") or
                self.parser.extract_all_text(selector, ".article-content") or
                self.parser.extract_all_text(selector, ".post-content") or
                self.parser.extract_all_text(selector, "main")
            )
            
            if article_body:
                body = " ".join(article_body)
            else:
                # Fallback to cleaned full page text
                body = self.parser.clean_text(resp.text)
            
            # Extract author if possible
            author = (
                self.parser.extract_text(selector, ".author") or
                self.parser.extract_text(selector, "[rel='author']") or
                self.parser.extract_text(selector, ".byline")
            )
            
            # Extract published date if possible
            published_at = None
            date_str = (
                self.parser.extract_text(selector, "time[datetime]") or
                self.parser.extract_text(selector, ".published-date") or
                self.parser.extract_text(selector, "[itemprop='datePublished']")
            )
            if date_str:
                published_at = self.parser.parse_date(date_str)
            
            item = Item(
                url=resp.url,
                title=title,
                body=body,
                source=self.source_name,
                author=author,
                published_at=published_at,
                metadata={
                    "fetched_full": True,
                    "original_url": resp.request.metadata.get("original_item_url", resp.url)
                }
            )
            
            logger.debug(f"Fetched full content for: {title[:50]}...")
            return [item], []
            
        except Exception as e:
            logger.error(f"Error parsing full content from {resp.url}: {e}")
            return [], []
