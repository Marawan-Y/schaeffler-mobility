# data_sources/patent_api.py
import aiohttp
from typing import Dict, List
from datetime import datetime, timedelta
from .base import BaseDataSource

class PatentAPISource(BaseDataSource):
    """USPTO Patent data source for technology trend monitoring"""
    
    def __init__(self):
        super().__init__('USPTO', None)  # No API key required
        self.base_url = 'https://developer.uspto.gov/ibd-api/v1/patent/application'
    
    async def fetch_data(self, query: str) -> Dict:
        """Fetch patent data from USPTO"""
        # USPTO API parameters
        params = {
            'searchText': query,
            'start': 0,
            'rows': 20,
            'largeTextSearchFlag': 'N',
            'sortField': 'lastModifiedDate',
            'sortDirection': 'desc'
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    'Accept': 'application/json',
                    'User-Agent': 'Schaeffler Mobility Platform/1.0'
                }
                
                async with session.get(self.base_url, params=params, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {'patents': data.get('results', [])}
                    else:
                        print(f"USPTO API error: {response.status}")
                        return {'patents': []}
        except Exception as e:
            print(f"Error fetching patents: {e}")
            return {'patents': []}
    
    def process_data(self, raw_data: Dict) -> List[Dict]:
        """Process patent data into standardized format"""
        processed = []
        
        # Keywords relevant to Schaeffler's interests
        schaeffler_keywords = [
            'bearing', 'e-mobility', 'electric motor', 'autonomous',
            'sensor', 'actuator', 'transmission', 'clutch', 'chassis',
            'predictive maintenance', 'condition monitoring'
        ]
        
        for patent in raw_data.get('patents', []):
            title = patent.get('inventionTitle', '')
            abstract = patent.get('inventionAbstract', '')
            
            if not title:
                continue
            
            # Check relevance to Schaeffler
            relevance_score = self._calculate_relevance(
                title + ' ' + abstract, 
                schaeffler_keywords
            )
            
            # Only include highly relevant patents
            if relevance_score < 0.3:
                continue
            
            processed_patent = {
                'source': 'USPTO',
                'type': 'patent',
                'title': title,
                'description': abstract[:500] + '...' if len(abstract) > 500 else abstract,
                'data': {
                    'application_number': patent.get('applicationNumber', ''),
                    'filing_date': patent.get('filingDate', ''),
                    'applicant': patent.get('applicantName', ''),
                    'status': patent.get('applicationStatus', ''),
                    'relevance_score': relevance_score
                },
                'relevance_keywords': self._extract_matching_keywords(
                    title + ' ' + abstract, 
                    schaeffler_keywords
                )
            }
            
            processed.append(processed_patent)
        
        # Sort by relevance
        processed.sort(key=lambda x: x['data']['relevance_score'], reverse=True)
        
        return processed[:10]  # Return top 10 most relevant
    
    def _calculate_relevance(self, text: str, keywords: List[str]) -> float:
        """Calculate relevance score based on keyword matches"""
        text_lower = text.lower()
        matches = 0
        
        for keyword in keywords:
            if keyword in text_lower:
                matches += 1
        
        return matches / len(keywords) if keywords else 0
    
    def _extract_matching_keywords(self, text: str, keywords: List[str]) -> List[str]:
        """Extract keywords that match in the text"""
        text_lower = text.lower()
        return [kw for kw in keywords if kw in text_lower]
    
    async def search_competitor_patents(self, competitors: List[str]) -> Dict:
        """Search for patents from specific competitors"""
        competitor_patents = {}
        
        for competitor in competitors:
            data = await self.fetch_data(f'applicantName:{competitor}')
            processed = self.process_data(data)
            if processed:
                competitor_patents[competitor] = processed
        
        return competitor_patents