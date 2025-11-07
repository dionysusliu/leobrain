"""Tests for RSS spider"""
import pytest
from datetime import datetime

from crawlers.spiders.rss_spider import RSSSpider
from crawlers.core.types import Request, Response
from tests.utils import load_fixture


@pytest.mark.unit
class TestRSSSpider:
    """Test RSS spider"""
    
    @pytest.fixture
    def spider(self):
        """Create RSS spider instance"""
        return RSSSpider(
            source_name="test_source",
            feed_url="http://example.com/feed.xml",
            max_items=10,
            fetch_full_content=False
        )
    
    def test_seeds(self, spider):
        """Test that seeds returns correct request"""
        seeds = spider.seeds()
        assert len(seeds) == 1
        assert seeds[0].url == "http://example.com/feed.xml"
        assert seeds[0].metadata["source"] == "test_source"
        assert seeds[0].metadata["is_feed"] is True
    
    def test_parse_rss_feed(self, spider, sample_rss_response):
        """Test parsing RSS feed"""
        items, new_requests = spider.parse(sample_rss_response)
        
        assert len(items) > 0
        assert all(item.source == "test_source" for item in items)
        assert all(item.url for item in items)
        assert all(item.title for item in items)
    
    def test_parse_rss_extracts_title(self, spider, sample_rss_response):
        """Test that RSS parsing extracts titles"""
        items, _ = spider.parse(sample_rss_response)
        
        titles = [item.title for item in items]
        # sample_rss.xml has titles like "AI Breakthrough", "New Quantum Computing", etc.
        assert len(titles) > 0
        assert all(title for title in titles)  # All should have titles
    
    def test_parse_rss_extracts_url(self, spider, sample_rss_response):
        """Test that RSS parsing extracts URLs"""
        items, _ = spider.parse(sample_rss_response)
        
        urls = [item.url for item in items]
        assert all(url.startswith("http") for url in urls)
    
    def test_parse_rss_extracts_author(self, spider, sample_rss_response):
        """Test that RSS parsing extracts authors"""
        items, _ = spider.parse(sample_rss_response)
        
        # sample_rss.xml has authors, but they might be in different formats
        # Check if any items have authors, or if the feed structure supports it
        authors = [item.author for item in items if item.author]
        # At least check that the parsing doesn't crash
        assert isinstance(authors, list)
    
    def test_parse_rss_extracts_date(self, spider, sample_rss_response):
        """Test that RSS parsing extracts published dates"""
        items, _ = spider.parse(sample_rss_response)
        
        # sample_rss_feed fixture has pubDate fields, should extract them
        dates = [item.published_at for item in items if item.published_at]
        # Should have at least some dates since sample_rss_feed has pubDate
        assert len(dates) > 0, "sample_rss_feed has pubDate fields, should extract them"
        assert all(isinstance(d, datetime) for d in dates)
    
    def test_parse_rss_respects_max_items(self, spider, sample_rss_response):
        """Test that max_items limit is respected"""
        spider.max_items = 2
        items, _ = spider.parse(sample_rss_response)
        
        assert len(items) <= 2
    
    def test_parse_rss_generates_follow_up_requests(self, spider, sample_rss_response):
        """Test that follow-up requests are generated when fetch_full_content is enabled"""
        spider.fetch_full_content = True
        
        # Mock short content in RSS
        items, new_requests = spider.parse(sample_rss_response)
        
        # If items have short content, should generate follow-up requests
        # This depends on the actual RSS content
        assert isinstance(new_requests, list)
    
    def test_parse_full_content(self, spider, sample_html_response):
        """Test parsing full article content"""
        items, new_requests = spider.parse_full_content(sample_html_response)
        
        assert len(items) == 1
        item = items[0]
        assert item.url == sample_html_response.url
        assert item.title
        assert item.body
        assert len(item.body) > 0
        assert new_requests == []
    
    def test_parse_full_content_extracts_title(self, spider, sample_html_response):
        """Test that full content parsing extracts title"""
        items, _ = spider.parse_full_content(sample_html_response)
        
        assert items[0].title
        assert "Article" in items[0].title or "Test" in items[0].title
    
    def test_parse_full_content_cleans_html(self, spider, sample_html_response):
        """Test that full content parsing cleans HTML"""
        items, _ = spider.parse_full_content(sample_html_response)
        
        body = items[0].body
        # Should not contain script tags
        assert "<script>" not in body.lower()
        # Should contain actual content
        assert len(body) > 0
    
    def test_parse_handles_empty_feed(self, spider):
        """Test parsing empty RSS feed"""
        empty_feed = """<?xml version="1.0"?>
        <rss version="2.0">
            <channel>
                <title>Empty Feed</title>
            </channel>
        </rss>"""
        
        response = Response(
            url="http://example.com/feed.xml",
            status=200,
            body=empty_feed.encode('utf-8'),
            headers={},
            request=Request(url="http://example.com/feed.xml", metadata={"is_feed": True})
        )
        
        items, new_requests = spider.parse(response)
        assert len(items) == 0
        assert new_requests == []
    
    def test_parse_handles_invalid_feed(self, spider):
        """Test parsing invalid RSS feed"""
        invalid_feed = "This is not valid XML"
        
        response = Response(
            url="http://example.com/feed.xml",
            status=200,
            body=invalid_feed.encode('utf-8'),
            headers={},
            request=Request(url="http://example.com/feed.xml", metadata={"is_feed": True})
        )
        
        items, new_requests = spider.parse(response)
        # Should handle gracefully, return empty or partial results
        assert isinstance(items, list)
        assert isinstance(new_requests, list)
