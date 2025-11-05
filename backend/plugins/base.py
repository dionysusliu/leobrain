from typing import Protocol
from common.models import Content


class AnalysisResult:
    def __init__(self, plugin_name: str, version: str, result_type: str, payload: dict):
        self.plugin_name = plugin_name
        self.version = version
        self.result_type = result_type
        self.payload = payload


class AnalysisPlugin(Protocol):
    name: str
    version: str
    
    def run(self, content: Content) -> AnalysisResult:
        """Run analysis on content and return results"""
        ...