"""Crawler engine that orchestrates spiders, fetchers, and pipelines"""
import asyncio
import logging
from typing import List, Dict, Optional
import yaml
from pathlib import Path

from crawlers.core.base_spider import ISpider
from crawlers.core.fetcher import IFetcher, HttpxFetcher
from crawlers.core.pipelines import IPipeline, StoragePipeline
from crawlers.core.renderer import IRenderer, NoopRenderer, PlaywrightRenderer
from crawlers.core.anti_bot import AntiBotMiddleware
from crawlers.core.types import Request, Item

logger = logging.getLogger(__name__)


class CrawlerEngine:
    """Main crawler engine"""
    
    def __init__(
        self,
        fetcher: Optional[IFetcher] = None,
        pipeline: Optional[IPipeline] = None,
        renderer: Optional[IRenderer] = None
    ):
        self.fetcher = fetcher or HttpxFetcher()
        self.pipeline = pipeline or StoragePipeline()
        self.renderer = renderer or NoopRenderer()
        self.anti_bot = None
    
    def set_anti_bot(self, qps: float = 1.0, delay: float = 1.0):
        """Configure anti-bot middleware"""
        self.anti_bot = AntiBotMiddleware(qps=qps, delay=delay)
    
    async def crawl_spider(self, spider: ISpider, config: Dict) -> int:
        """
        Crawl a single spider
        
        Args:
            spider: Spider instance
            config: Configuration dict from sites.yaml
            
        Returns:
            Number of items successfully processed
        """
        logger.info(f"Starting crawl for spider: {spider.name}")
        
        # Configure anti-bot if specified
        if config.get('qps') or config.get('delay'):
            self.set_anti_bot(
                qps=config.get('qps', 1.0),
                delay=config.get('delay', 1.0)
            )
        
        # Get initial requests
        requests = spider.seeds()
        all_items = []
        
        # Process requests
        while requests:
            req = requests.pop(0)
            
            # Apply anti-bot delay
            if self.anti_bot:
                await self.anti_bot.before_request(req)
            
            # Fetch
            if req.use_render and isinstance(self.renderer, PlaywrightRenderer):
                resp = await self.renderer.render(req)
            else:
                resp = await self.fetcher.fetch(req)
            
            if not resp:
                logger.warning(f"Failed to fetch: {req.url}")
                continue
            
            # Parse based on request type
            # Check if this is a full content fetch request
            is_full_content = req.metadata.get('fetch_full', False)
            
            if is_full_content and hasattr(spider, 'parse_full_content'):
                # Use parse_full_content for follow-up requests
                items, new_requests = spider.parse_full_content(resp)
            else:
                # Use regular parse for RSS feed or initial requests
                items, new_requests = spider.parse(resp)
            
            all_items.extend(items)
            requests.extend(new_requests)
            
            # Apply anti-bot after request
            if self.anti_bot:
                await self.anti_bot.after_request(resp, req)
        
        # Process items through pipeline
        if all_items:
            success_count = await self.pipeline.process_items(all_items)
            logger.info(f"Crawled {success_count}/{len(all_items)} items successfully")
            return success_count
        
        return 0
    
    async def close(self):
        """Close all resources"""
        if isinstance(self.fetcher, HttpxFetcher):
            await self.fetcher.close()
        if isinstance(self.renderer, PlaywrightRenderer):
            await self.renderer.close()


def load_site_configs(config_path: Optional[str] = None) -> Dict:
    """Load site configurations from YAML"""
    if config_path is None:
        config_path = Path(__file__).parent.parent / "configs" / "sites.yaml"
    else:
        config_path = Path(config_path)
    
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)