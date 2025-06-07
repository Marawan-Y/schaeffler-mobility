# data_sources/news_api.py
import os
import aiohttp
from typing import Dict, List
from datetime import datetime, timedelta
from .base import BaseDataSource

class NewsAPISource(BaseDataSource):
    """News API data source for monitoring news trends"""
    
    def __init__(self):
        api_key = os.getenv('NEWS_API_KEY')
        super().__init__('NewsAPI', api_key)
        self.base_url = 'https://newsapi.org/v2'
    
    async def fetch_data(self, query: str) -> Dict:
        """Fetch news data from NewsAPI"""
        if not self.api_key:
            return {'articles': []}
        
        # Calculate date range (last 7 days)
        to_date = datetime.now()
        from_date = to_date - timedelta(days=7)
        
        params = {
            'q': query,
            'apiKey': self.api_key,
            'from': from_date.strftime('%Y-%m-%d'),
            'to': to_date.strftime('%Y-%m-%d'),
            'sortBy': 'relevancy',
            'language': 'en',
            'pageSize': 20
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f'{self.base_url}/everything', params=params) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        print(f"NewsAPI error: {response.status}")
                        return {'articles': []}
        except Exception as e:
            print(f"Error fetching news: {e}")
            return {'articles': []}
    
    def process_data(self, raw_data: Dict) -> List[Dict]:
        """Process news articles into standardized format"""
        processed = []
        
        for article in raw_data.get('articles', []):
            # Skip if no title or description
            if not article.get('title') or not article.get('description'):
                continue
            
            processed_article = {
                'source': 'NewsAPI',
                'type': 'news',
                'title': article['title'],
                'description': article['description'],
                'content': article.get('content', ''),
                'url': article.get('url', ''),
                'published_at': article.get('publishedAt', ''),
                'source_name': article.get('source', {}).get('name', 'Unknown'),
                'relevance_keywords': self._extract_keywords(article)
            }
            processed.append(processed_article)
        
        return processed
    
    def _extract_keywords(self, article: Dict) -> List[str]:
        """Extract relevant keywords from article"""
        text = f"{article.get('title', '')} {article.get('description', '')}"
        
        # Keywords relevant to Schaeffler and mobility
        mobility_keywords = [
            'electric', 'autonomous', 'mobility', 'automotive', 'bearing',
            'e-mobility', 'sustainability', 'manufacturing', 'industry 4.0',
            'robotics', 'AI', 'IoT', 'smart', 'digital', 'transformation'
        ]
        
        found_keywords = []
        text_lower = text.lower()
        
        for keyword in mobility_keywords:
            if keyword in text_lower:
                found_keywords.append(keyword)
        
        return found_keywords