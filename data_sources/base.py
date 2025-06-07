# data_sources/base.py
from abc import ABC, abstractmethod
from typing import Dict, List, Optional
import aiohttp
import asyncio

class BaseDataSource(ABC):
    """Base class for all data sources"""
    
    def __init__(self, name: str, api_key: Optional[str] = None):
        self.name = name
        self.api_key = api_key
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    @abstractmethod
    async def fetch_data(self, query: str) -> Dict:
        """Fetch data from the source"""
        pass
    
    @abstractmethod
    def process_data(self, raw_data: Dict) -> List[Dict]:
        """Process raw data into standardized format"""
        pass
    
    async def search(self, query: str) -> List[Dict]:
        """Main search method"""
        try:
            raw_data = await self.fetch_data(query)
            return self.process_data(raw_data)
        except Exception as e:
            print(f"Error in {self.name}: {e}")
            return []