# crawlers/core/crawler_service.py (新建)
"""爬虫服务层"""
import logging
from typing import Dict

from crawlers.core.engine import CrawlerEngine
from crawlers.core.spiders.rss_spider import RSSSpider

logger = logging.getLogger(__name__)


async def crawl_site(site_name: str, config: Dict):
    """
    Crawl a single site
    
    Args:
        site_name: Name of the site
        config: Site configuration
    """
    logger.info(f"Starting crawl task for {site_name}")
    
    try:
        # Create spider based on config
        spider_type = config.get('spider', 'rss')
        
        if spider_type == 'rss':
            spider = RSSSpider(
                source_name=config['source_name'],
                feed_url=config['feed_url'],
                max_items=config.get('max_items'),
                fetch_full_content=config.get('fetch_full_content', False)
            )
        else:
            raise ValueError(f"Unknown spider type: {spider_type}")
        
        # Create engine and crawl
        engine = CrawlerEngine()
        await engine.crawl_spider(spider, config)
        await engine.close()
        
        logger.info(f"Completed crawl task for {site_name}")
        
    except Exception as e:
        logger.error(f"Error in crawl task for {site_name}: {e}", exc_info=True)
        raise