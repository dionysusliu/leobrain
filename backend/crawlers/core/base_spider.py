"""Spider interface"""
from abc import ABC, abstractmethod
from typing import List, Tuple
from crawlers.core.types import Request, Item, Response

class ISpider(ABC):
    """Spider interface - sites only implement parse() and seeds()"""
    name: str

    @abstractmethod
    def seeds(self) -> List[Request]:
        """Generate initial requests

        Returns:
            List of initial requests to crawl
        """
        pass

    @abstractmethod
    def parse(self, resp: Response) -> Tuple[List[Item], List[Request]]:
        """Parse response and extract items

        Args:
            resp (Response): response object 

        Returns:
            Tuple of (items, new_requests)
            - items: list of extracted items
            - new_requests: List of follow-up requests (for pagination, etc.)
        """
        pass

    def closed(self, reason: str):
        """Called when spider closes"""
        pass