# data_sources/market_data.py
import os
import aiohttp
from typing import Dict, List
from .base import BaseDataSource

class MarketDataSource(BaseDataSource):
    """Alpha Vantage market data source for financial insights"""
    
    def __init__(self):
        api_key = os.getenv('ALPHA_VANTAGE_KEY')
        super().__init__('AlphaVantage', api_key)
        self.base_url = 'https://www.alphavantage.co/query'
        
        # Relevant stock symbols for mobility sector
        self.mobility_stocks = {
            'TSLA': 'Tesla',
            'GM': 'General Motors',
            'F': 'Ford',
            'VWAGY': 'Volkswagen',
            'TM': 'Toyota',
            'STLA': 'Stellantis',
            'NIO': 'NIO Inc',
            'XPEV': 'XPeng',
            'LI': 'Li Auto',
            'RIVN': 'Rivian'
        }
    
    async def fetch_data(self, query: str = None) -> Dict:
        """Fetch market data for mobility stocks"""
        if not self.api_key:
            return {'market_data': []}
        
        market_data = []
        
        # For demo, just fetch a few key stocks
        symbols = ['TSLA', 'GM', 'F'] if not query else [query]
        
        try:
            async with aiohttp.ClientSession() as session:
                for symbol in symbols:
                    params = {
                        'function': 'GLOBAL_QUOTE',
                        'symbol': symbol,
                        'apikey': self.api_key
                    }
                    
                    async with session.get(self.base_url, params=params) as response:
                        if response.status == 200:
                            data = await response.json()
                            if 'Global Quote' in data:
                                market_data.append({
                                    'symbol': symbol,
                                    'data': data['Global Quote']
                                })
                        
                        # Rate limit: 5 calls per minute for free tier
                        await asyncio.sleep(12)
                
                return {'market_data': market_data}
        except Exception as e:
            print(f"Error fetching market data: {e}")
            return {'market_data': []}
    
    def process_data(self, raw_data: Dict) -> List[Dict]:
        """Process market data into insights"""
        processed = []
        
        for item in raw_data.get('market_data', []):
            symbol = item['symbol']
            quote = item['data']
            
            if not quote:
                continue
            
            # Calculate metrics
            price = float(quote.get('05. price', 0))
            change_percent = quote.get('10. change percent', '0%')
            volume = int(quote.get('06. volume', 0))
            
            # Determine if this is a significant movement
            change_value = float(change_percent.rstrip('%')) if change_percent else 0
            is_significant = abs(change_value) > 3.0  # More than 3% change
            
            processed_item = {
                'source': 'AlphaVantage',
                'type': 'market',
                'title': f"{self.mobility_stocks.get(symbol, symbol)} Stock Movement",
                'description': f"{symbol} is {'up' if change_value > 0 else 'down'} {abs(change_value):.2f}% at ${price:.2f}",
                'data': {
                    'symbol': symbol,
                    'company': self.mobility_stocks.get(symbol, symbol),
                    'price': price,
                    'change_percent': change_value,
                    'volume': volume,
                    'is_significant': is_significant
                },
                'relevance_keywords': ['market', 'stock', 'financial', symbol.lower()]
            }
            
            processed.append(processed_item)
        
        return processed
    
    async def get_sector_performance(self) -> Dict:
        """Get overall mobility sector performance"""
        # This would aggregate data across multiple stocks
        # For now, return a simplified version
        return {
            'sector': 'Mobility & Automotive',
            'trend': 'Mixed',
            'top_performers': ['TSLA', 'NIO'],
            'notable_movements': []
        }