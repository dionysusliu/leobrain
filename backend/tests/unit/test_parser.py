"""Tests for parser utilities"""
import pytest
from crawlers.core.parser import Parser


@pytest.mark.unit
class TestParser:
    """Test parser utilities"""
    
    def test_clean_text_removes_scripts(self):
        """Test that clean_text removes script tags"""
        html = "<html><body><script>alert('test');</script><p>Hello</p></body></html>"
        parser = Parser()
        result = parser.clean_text(html)
        assert "alert" not in result
        assert "Hello" in result
    
    def test_clean_text_removes_styles(self):
        """Test that clean_text removes style tags"""
        html = "<html><head><style>.hidden { display: none; }</style></head><body><p>Content</p></body></html>"
        parser = Parser()
        result = parser.clean_text(html)
        assert ".hidden" not in result
        assert "Content" in result
    
    def test_clean_text_preserves_content(self):
        """Test that clean_text preserves actual content"""
        html = "<html><body><h1>Title</h1><p>Paragraph 1</p><p>Paragraph 2</p></body></html>"
        parser = Parser()
        result = parser.clean_text(html)
        assert "Title" in result
        assert "Paragraph 1" in result
        assert "Paragraph 2" in result
    
    def test_clean_text_handles_empty_html(self):
        """Test that clean_text handles empty HTML"""
        parser = Parser()
        result = parser.clean_text("")
        assert result == ""
    
    def test_clean_text_handles_invalid_html(self):
        """Test that clean_text handles invalid HTML gracefully"""
        parser = Parser()
        invalid_html = "<html><body><p>Unclosed tag"
        result = parser.clean_text(invalid_html)
        # Should not raise exception, may return original or cleaned version
        assert isinstance(result, str)
    
    def test_parse_date_valid(self):
        """Test parsing valid date strings"""
        parser = Parser()
        date_str = "Mon, 01 Jan 2024 12:00:00 GMT"
        result = parser.parse_date(date_str)
        assert result is not None
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 1
    
    def test_parse_date_various_formats(self):
        """Test parsing various date formats"""
        parser = Parser()
        test_cases = [
            ("2024-01-01", 2024, 1, 1),
            ("2024-01-01T12:00:00Z", 2024, 1, 1),
            ("January 1, 2024", 2024, 1, 1),
            ("01/01/2024", 2024, 1, 1),
        ]
        
        for date_str, year, month, day in test_cases:
            result = parser.parse_date(date_str)
            assert result is not None, f"Failed to parse: {date_str}"
            assert result.year == year
            assert result.month == month
            assert result.day == day
    
    def test_parse_date_invalid(self):
        """Test parsing invalid date strings"""
        parser = Parser()
        result = parser.parse_date("invalid date")
        assert result is None
    
    def test_parse_date_none(self):
        """Test parsing None date"""
        parser = Parser()
        result = parser.parse_date(None)
        assert result is None
    
    def test_parse_html(self):
        """Test parse_html returns HTMLParser"""
        parser = Parser()
        html = "<html><body><p>Test</p></body></html>"
        result = parser.parse_html(html)
        assert result is not None
        # Check it's a selectolax HTMLParser
        assert hasattr(result, 'css')
    
    def test_parse_selector(self):
        """Test parse_selector returns Selector"""
        parser = Parser()
        html = "<html><body><p>Test</p></body></html>"
        result = parser.parse_selector(html)
        assert result is not None
        # Check it's a parsel Selector
        assert hasattr(result, 'css')
        assert hasattr(result, 'xpath')
    
    def test_extract_text_css(self):
        """Test extract_text with CSS selector"""
        parser = Parser()
        html = "<html><body><h1>Title</h1><p>Content</p></body></html>"
        selector = parser.parse_selector(html)
        result = parser.extract_text(selector, "h1")
        assert result == "Title"
    
    def test_extract_text_xpath(self):
        """Test extract_text with XPath"""
        parser = Parser()
        html = "<html><body><h1>Title</h1></body></html>"
        selector = parser.parse_selector(html)
        result = parser.extract_text(selector, None, "//h1/text()")
        assert result == "Title"
    
    def test_extract_text_not_found(self):
        """Test extract_text when element not found"""
        parser = Parser()
        html = "<html><body><p>Content</p></body></html>"
        selector = parser.parse_selector(html)
        result = parser.extract_text(selector, "h1")
        assert result is None
    
    def test_extract_all_text_css(self):
        """Test extract_all_text with CSS selector"""
        parser = Parser()
        html = "<html><body><p>First</p><p>Second</p><p>Third</p></body></html>"
        selector = parser.parse_selector(html)
        result = parser.extract_all_text(selector, "p")
        assert len(result) == 3
        assert "First" in result
        assert "Second" in result
        assert "Third" in result

