"""Edge case tests for RSS spider"""
import pytest
from crawlers.spiders.rss_spider import RSSSpider
from crawlers.core.types import Request, Response


@pytest.mark.unit
class TestRSSSpiderEdgeCases:
    """Test edge cases and error handling"""
    
    @pytest.fixture
    def spider(self):
        return RSSSpider(
            source_name="test",
            feed_url="http://example.com/feed.xml"
        )
    
    def test_parse_malformed_xml(self, spider):
        """Test handling of malformed XML"""
        malformed_xml = "This is not XML at all <xml>"
        response = Response(
            url="http://example.com/feed.xml",
            status=200,
            body=malformed_xml.encode('utf-8'),
            headers={},
            request=Request(url="http://example.com/feed.xml", metadata={"is_feed": True})
        )
        
        items, new_requests = spider.parse(response)
        # Should handle gracefully
        assert isinstance(items, list)
        assert isinstance(new_requests, list)
    
    def test_parse_empty_items(self, spider):
        """Test parsing feed with no items"""
        empty_feed = """<?xml version="1.0"?>
        <rss version="2.0">
            <channel>
                <title>Empty Channel</title>
                <link>http://example.com</link>
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
    
    def test_parse_item_without_title(self, spider):
        """Test parsing item without title"""
        feed_no_title = """<?xml version="1.0"?>
        <rss version="2.0">
            <channel>
                <item>
                    <link>http://example.com/article</link>
                    <description>Content without title</description>
                </item>
            </channel>
        </rss>"""
        
        response = Response(
            url="http://example.com/feed.xml",
            status=200,
            body=feed_no_title.encode('utf-8'),
            headers={},
            request=Request(url="http://example.com/feed.xml", metadata={"is_feed": True})
        )
        
        items, _ = spider.parse(response)
        # Should use default title or handle gracefully
        assert len(items) > 0
        assert items[0].title  # Should have some title (default or extracted)
    
    def test_parse_item_without_url(self, spider):
        """Test parsing item without URL"""
        feed_no_url = """<?xml version="1.0"?>
        <rss version="2.0">
            <channel>
                <item>
                    <title>Article without URL</title>
                    <description>Content</description>
                </item>
            </channel>
        </rss>"""
        
        response = Response(
            url="http://example.com/feed.xml",
            status=200,
            body=feed_no_url.encode('utf-8'),
            headers={},
            request=Request(url="http://example.com/feed.xml", metadata={"is_feed": True})
        )
        
        items, _ = spider.parse(response)
        # Items without URLs might be skipped or have empty URL
        # Check behavior is consistent
        for item in items:
            assert isinstance(item.url, str)  # Should be string (even if empty)
    
    def test_parse_item_with_html_in_description(self, spider):
        """Test parsing item with HTML in description"""
        feed_html_desc = """<?xml version="1.0"?>
        <rss version="2.0">
            <channel>
                <item>
                    <title>Article</title>
                    <link>http://example.com/article</link>
                    <description><![CDATA[<p>HTML content with <strong>bold</strong> text</p>]]></description>
                </item>
            </channel>
        </rss>"""
        
        response = Response(
            url="http://example.com/feed.xml",
            status=200,
            body=feed_html_desc.encode('utf-8'),
            headers={},
            request=Request(url="http://example.com/feed.xml", metadata={"is_feed": True})
        )
        
        items, _ = spider.parse(response)
        assert len(items) > 0
        # HTML should be cleaned
        body = items[0].body
        assert "<p>" not in body or "<strong>" not in body  # HTML tags should be removed or cleaned
    
    def test_parse_very_large_feed(self, spider):
        """Test parsing feed with many items"""
        # Create a feed with 100 items
        items_xml = "\n".join([
            f"""<item>
                <title>Article {i}</title>
                <link>http://example.com/article{i}</link>
                <description>Content {i}</description>
            </item>"""
            for i in range(100)
        ])
        
        large_feed = f"""<?xml version="1.0"?>
        <rss version="2.0">
            <channel>
                <title>Large Feed</title>
                {items_xml}
            </channel>
        </rss>"""
        
        response = Response(
            url="http://example.com/feed.xml",
            status=200,
            body=large_feed.encode('utf-8'),
            headers={},
            request=Request(url="http://example.com/feed.xml", metadata={"is_feed": True})
        )
        
        items, _ = spider.parse(response)
        assert len(items) == 100
    
    def test_parse_feed_with_special_characters(self, spider):
        """Test parsing feed with special characters"""
        feed_special = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
            <channel>
                <item>
                    <title>Article with "quotes" &amp; &lt;tags&gt;</title>
                    <link>http://example.com/article</link>
                    <description>Content with émojis 🎉 and unicode 中文</description>
                </item>
            </channel>
        </rss>"""
        
        response = Response(
            url="http://example.com/feed.xml",
            status=200,
            body=feed_special.encode('utf-8'),
            headers={},
            request=Request(url="http://example.com/feed.xml", metadata={"is_feed": True})
        )
        
        items, _ = spider.parse(response)
        assert len(items) > 0
        # Should handle special characters correctly
        assert "quotes" in items[0].title or "&" in items[0].title
