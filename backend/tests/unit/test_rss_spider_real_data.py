"""Tests for RSS spider with real RSS feeds"""
import pytest
from crawlers.spiders.rss_spider import RSSSpider
from crawlers.core.types import Request, Response
from tests.utils import load_fixture


@pytest.mark.unit
class TestRSSSpiderRealData:
    """Test RSS spider with real RSS feeds"""
    
    @pytest.fixture
    def bbc_rss_response(self):
        """BBC RSS feed response"""
        content = load_fixture("bbc_technology_rss.xml")
        return Response(
            url="http://feeds.bbci.co.uk/news/technology/rss.xml",
            status=200,
            body=content.encode('utf-8'),
            headers={"Content-Type": "application/rss+xml"},
            request=Request(url="http://feeds.bbci.co.uk/news/technology/rss.xml", metadata={"is_feed": True})
        )
    
    @pytest.fixture
    def hackernews_rss_response(self):
        """Hacker News RSS feed response"""
        content = load_fixture("hackernews_rss.xml")
        return Response(
            url="https://hnrss.org/frontpage",
            status=200,
            body=content.encode('utf-8'),
            headers={"Content-Type": "application/rss+xml"},
            request=Request(url="https://hnrss.org/frontpage", metadata={"is_feed": True})
        )
    
    @pytest.fixture
    def reuters_rss_response(self):
        """Reuters RSS feed response"""
        content = load_fixture("reuters_rss.xml")
        return Response(
            url="https://www.reutersagency.com/feed/",
            status=200,
            body=content.encode('utf-8'),
            headers={"Content-Type": "application/rss+xml"},
            request=Request(url="https://www.reutersagency.com/feed/", metadata={"is_feed": True})
        )
    
    def test_parse_bbc_rss(self, bbc_rss_response):
        """Test parsing BBC RSS feed"""
        spider = RSSSpider(
            source_name="bbc",
            feed_url="http://feeds.bbci.co.uk/news/technology/rss.xml",
            max_items=10
        )
        
        items, new_requests = spider.parse(bbc_rss_response)
        
        assert len(items) > 0, "Should parse at least one item from BBC feed"
        assert all(item.source == "bbc" for item in items)
        assert all(item.url for item in items), "All items should have URLs"
        assert all(item.title for item in items), "All items should have titles"
        assert all(len(item.body) >= 0 for item in items), "All items should have body (even if empty)"
    
    def test_parse_hackernews_rss(self, hackernews_rss_response):
        """Test parsing Hacker News RSS feed"""
        spider = RSSSpider(
            source_name="hackernews",
            feed_url="https://hnrss.org/frontpage",
            max_items=10
        )
        
        items, new_requests = spider.parse(hackernews_rss_response)
        
        assert len(items) > 0, "Should parse at least one item from Hacker News feed"
        assert all(item.source == "hackernews" for item in items)
        # Hacker News items might not have authors
        assert all(item.url for item in items)
        assert all(item.title for item in items)
    
    def test_parse_reuters_rss(self, reuters_rss_response):
        """Test parsing Reuters RSS feed"""
        spider = RSSSpider(
            source_name="reuters",
            feed_url="https://www.reutersagency.com/feed/",
            max_items=10
        )
        
        items, new_requests = spider.parse(reuters_rss_response)
        
        assert len(items) > 0, "Should parse at least one item from Reuters feed"
        assert all(item.source == "reuters" for item in items)
        assert all(item.url for item in items)
        assert all(item.title for item in items)
    
    def test_parse_real_rss_extracts_dates(self, bbc_rss_response):
        """Test that real RSS feeds have parseable dates"""
        spider = RSSSpider(
            source_name="bbc",
            feed_url="http://feeds.bbci.co.uk/news/technology/rss.xml"
        )
        
        items, _ = spider.parse(bbc_rss_response)
        
        # At least some items should have dates
        items_with_dates = [item for item in items if item.published_at]
        assert len(items_with_dates) > 0, "Should have at least some items with dates"
        
        # All dates should be datetime objects
        assert all(isinstance(item.published_at, type(items_with_dates[0].published_at)) 
                  for item in items_with_dates if item.published_at)
    
    def test_parse_real_rss_respects_max_items(self, bbc_rss_response):
        """Test that max_items works with real RSS feeds"""
        spider = RSSSpider(
            source_name="bbc",
            feed_url="http://feeds.bbci.co.uk/news/technology/rss.xml",
            max_items=5
        )
        
        items, _ = spider.parse(bbc_rss_response)
        
        assert len(items) <= 5, f"Should respect max_items limit, got {len(items)} items"
    
    def test_parse_real_rss_handles_various_formats(self):
        """Test that spider handles different RSS feed formats"""
        feeds = [
            ("bbc_technology_rss.xml", "bbc"),
            ("hackernews_rss.xml", "hackernews"),
            ("reuters_rss.xml", "reuters"),
        ]
        
        for filename, source_name in feeds:
            content = load_fixture(filename)
            response = Response(
                url=f"http://example.com/{filename}",
                status=200,
                body=content.encode('utf-8'),
                headers={},
                request=Request(url=f"http://example.com/{filename}", metadata={"is_feed": True})
            )
            
            spider = RSSSpider(
                source_name=source_name,
                feed_url=f"http://example.com/{filename}",
                max_items=10
            )
            
            items, _ = spider.parse(response)
            assert len(items) > 0, f"Should parse items from {filename}"
            assert all(item.source == source_name for item in items)
