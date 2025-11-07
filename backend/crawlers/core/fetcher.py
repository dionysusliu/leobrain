"""Fetcher interface and implementations"""
import asyncio
from abc import ABC, abstractmethod
from tracemalloc import start
from typing import Optional
from urllib import robotparser
import httpx
import logging
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

from crawlers.core.types import Request, Response

logger = logging.getLogger(__name__)


class IFetcher(ABC):
    """Fetcher interface"""

    @abstractmethod
    async def fetch(self, req: Request) -> Optional[Response]:
        """Fetch a request

        Args:
            req: request a object

        Returns:
            Response object or None if failed
        """
        pass

    
class HttpxFetcher(IFetcher):
    """Default httpx-based fetcher"""

    def __init__(self,
        timeout: int = 30,
        max_retries: int = 3,
        default_headers: Optional[dict] = None,
        respect_robots: bool = True,
    ) -> None:

        self.timeout = timeout
        self.max_retries = max_retries
        self.default_headers = default_headers or {}
        self.respect_rebots = respect_robots
        self.robot_parsers: dict[str, RobotFileParser] = {}
        
        self.client = httpx.AsyncClient(
            timeout=timeout,
            headers=self.default_headers,
            follow_redirects=True
        )

    
    def _get_robots_parser(self, url: str) -> Optional[RobotFileParser]:
        """Get robots.txt parser from domain"""
        if not self.respect_rebots:
            return None

        parsed = urlparse(url)
        domain = f"{parsed.scheme}://{parsed.netloc}"

        if domain not in self.robot_parsers:
            robot_url = f"{domain}/robots.txt"
            rp = RobotFileParser()
            try: 
                rp.set_url(robot_url)
                rp.read()
                self.robot_parsers[domain] = rp
                logger.info(f"Loaded robots.txt from {robot_url}")
            except Exception as e:
                logger.warning(f"Could not load robots.txt: {e}")
                rp = RobotFileParser()
                rp.set_url(robot_url)
                self.robot_parsers[domain] = rp

        return self.robot_parsers.get(domain)

    def can_fetch(self, url: str, user_agent: str = "*") -> bool:
        """Check if URL can be fetched"""
        if not self.respect_rebots:
            return True

        parser = self._get_robots_parser(url)
        if parser is None:
            return True

        return parser.can_fetch(user_agent, url)

    async def fetch(self, req: Request) -> Optional[Response]:
        """Fetch request using httpx"""
        import time

        # check robots.txt
        user_agent = req.headers.get('User-Agent', '*') if req.headers else '*' 
        if not self.can_fetch(req.url, user_agent):
            logger.warning(f"URL blocked by robots.txt: {req.url}")
            return None

        # overwrite default headers
        headers = {**self.default_headers} # deepcopy the dict
        if req.headers:
            headers.update(req.headers)

        # build request
        request_kwargs = {
            'url': req.url,
            'headers': headers,
        }

        if req.params:
            request_kwargs['params'] = req.params
        if req.data:
            request_kwargs['data'] = req.data
        if req.json:
            request_kwargs['json'] = req.json

        # execute request with retries
        start_time = time.time()
        for attempt in range(self.max_retries):
            try:
                httpx_resp = await self.client.request(
                    method=req.method.value,
                    **request_kwargs
                )
                httpx_resp.raise_for_status()
                
                elapsed = time.time() - start_time

                return Response(
                    url=req.url,
                    status=httpx_resp.status_code,
                    body=httpx_resp.content,
                    headers=dict(httpx_resp.headers),
                    request=req,
                    elapsed=elapsed
                )
            
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429: # 'too many requests'
                    wait_time = 2 ** attempt # 指数退避
                    logger.warning(f"Rate limited, waiting {wait_time}s")
                    await asyncio.sleep(wait_time)
                elif e.response.status_code == 500: # 'internal server error' 
                    wait_time = 2 ** attempt # 指数退避
                    logger.warning(f"Server error, waiting {wait_time}s")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"HTTP error {e.response.status_code}: {e}")
                    return None

            except Exception as e:
                logger.error(f"Request error: {e}")
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt
                    await asyncio.sleep(wait_time)
                    continue
                return None
        
        return None

    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()

        