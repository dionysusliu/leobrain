"""Parsing utils"""
from typing import Optional
from datetime import datetime
from selectolax.parser import HTMLParser
from parsel import Selector
import dateutil.parser
import logging

logger = logging.getLogger(__name__)


class Parser:
    """Universal parser utils"""

    @staticmethod
    def parse_html(html: str) -> HTMLParser:
        """Parse HTML using selectolax"""
        return HTMLParser(html)

    @staticmethod
    def parse_selector(html: str) -> Selector:
        """Parse HTML using parsel (CSS/XPath)"""
        return Selector(text=html)

    @staticmethod
    def clean_text(html: str) -> str:
        """Extract clean text from HTML"""
        try:
            tree = HTMLParser(html)
            # remove scripts and styles
            for tag in tree.css('script, style'):
                tag.decompose()
            # get text
            text = tree.body.text(separator=' ', strip=True)
            return text
        except Exception as e:
            logger.warning(f"Error cleaning HTML: {e}")
            return html

    @staticmethod
    def parse_date(date_str: Optional[str]) -> Optional[datetime]:
        """Parse date string to datetime"""
        if not date_str:
            return None
        
        try:
            return dateutil.parser.parse(date_str)
        except Exception as e:
            logger.debug(f"Could not parse date '{date_str}': {e}")
            return None

    @staticmethod
    def extract_text(selector: Selector, css_selector: str, xpath: Optional[str] = None) -> Optional[str]:
        """Extract text using CSS or XPath"""
        if css_selector:
            text = selector.css(css_selector).get("")
        elif xpath:
            text = selector.xpath(xpath).get("")
        else:
            return None
        
        return text.strip() if text else None
    
    @staticmethod
    def extract_all_text(selector: Selector, css_selector: str, xpath: Optional[str] = None) -> list[str]:
        """Extract all matching text"""
        if css_selector:
            texts = selector.css(css_selector).getall()
        elif xpath:
            texts = selector.xpath(xpath).getall()
        else:
            return []
        
        return [t.strip() for t in texts if t.strip()]
    
    