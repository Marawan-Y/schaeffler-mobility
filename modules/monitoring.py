# modules/monitoring.py
import asyncio
import hashlib
import json
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
import aiohttp
import pymysql

@dataclass
class TrendAlert:
    """Model for trend alerts"""
    id: str
    timestamp: datetime
    category: str
    severity: str
    title: str
    description: str
    data_sources: List[str]
    confidence: float
    requires_action: bool
    status: str = 'active'
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        d = asdict(self)
        d['timestamp'] = d['timestamp'].isoformat()
        return d

class IntelligentMonitor:
    """Monitors multiple data sources for relevant trends"""
    
    def __init__(self, db_config: Dict, alert_threshold: float = 0.7):
        self.db_config = db_config
        self.alert_threshold = alert_threshold
        self.data_sources = self._load_data_sources()
        self.monitored_keywords = self._load_keywords()
        
    def _get_db_connection(self):
        """Get database connection"""
        return pymysql.connect(**self.db_config)
    
    def _load_data_sources(self) -> Dict[str, List[Dict]]:
        """Load configured data sources from database"""
        conn = self._get_db_connection()
        try:
            with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                cursor.execute("""
                    SELECT source_type, source_name, api_endpoint, 
                           api_key_env_var, config
                    FROM data_sources 
                    WHERE enabled = TRUE
                """)
                sources = cursor.fetchall()
                
                # Group by type
                grouped = {}
                for source in sources:
                    source_type = source['source_type']
                    if source_type not in grouped:
                        grouped[source_type] = []
                    grouped[source_type].append(source)
                
                return grouped
        finally:
            conn.close()
    
    def _load_keywords(self) -> Dict[str, List[Dict]]:
        """Load monitored keywords from database"""
        conn = self._get_db_connection()
        try:
            with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                cursor.execute("""
                    SELECT category, keyword, weight
                    FROM monitored_keywords
                    WHERE active = TRUE
                    ORDER BY category, weight DESC
                """)
                keywords = cursor.fetchall()
                
                # Group by category
                grouped = {}
                for kw in keywords:
                    cat = kw['category']
                    if cat not in grouped:
                        grouped[cat] = []
                    grouped[cat].append({
                        'keyword': kw['keyword'],
                        'weight': kw['weight']
                    })
                
                return grouped
        finally:
            conn.close()
    
    async def scan_sources(self) -> List[TrendAlert]:
        """Scan all configured data sources"""
        alerts = []
        
        # Use asyncio to scan sources concurrently
        tasks = []
        for source_type, sources in self.data_sources.items():
            for source in sources:
                task = self._scan_single_source(source_type, source)
                tasks.append(task)
        
        # Gather results
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, Exception):
                print(f"Error scanning source: {result}")
                continue
            if result:
                alerts.extend(result)
        
        # Filter and deduplicate alerts
        return self._filter_alerts(alerts)
    
    async def _scan_single_source(self, source_type: str, source: Dict) -> List[TrendAlert]:
        """Scan a single data source"""
        try:
            # Fetch data from source
            raw_data = await self._fetch_data(source)
            if not raw_data:
                return []
            
            # Process based on source type
            if source_type == 'news':
                return self._process_news_data(raw_data, source['source_name'])
            elif source_type == 'patents':
                return self._process_patent_data(raw_data, source['source_name'])
            elif source_type == 'market':
                return self._process_market_data(raw_data, source['source_name'])
            elif source_type == 'regulatory':
                return self._process_regulatory_data(raw_data, source['source_name'])
            
            return []
        except Exception as e:
            print(f"Error scanning {source['source_name']}: {e}")
            return []
    
    async def _fetch_data(self, source: Dict) -> Optional[Dict]:
        """Fetch data from API endpoint"""
        # This is a placeholder - implement actual API calls based on source
        # For demo purposes, return mock data
        await asyncio.sleep(0.1)  # Simulate API delay
        
        if source['source_name'] == 'NewsAPI':
            return {
                'articles': [
                    {
                        'title': 'Schaeffler Announces New E-Mobility Partnership',
                        'description': 'Leading automotive supplier partners with tech startup for advanced bearing systems',
                        'publishedAt': datetime.now().isoformat(),
                        'source': {'name': 'Automotive News'}
                    },
                    {
                        'title': 'Electric Vehicle Sales Surge 45% in Europe',
                        'description': 'Growing demand for sustainable mobility solutions drives market growth',
                        'publishedAt': datetime.now().isoformat(),
                        'source': {'name': 'Reuters'}
                    }
                ]
            }
        
        return None
    
    def _process_news_data(self, data: Dict, source_name: str) -> List[TrendAlert]:
        """Process news data into alerts"""
        alerts = []
        
        for article in data.get('articles', []):
            relevance = self._calculate_relevance(
                f"{article.get('title', '')} {article.get('description', '')}"
            )
            
            if relevance > self.alert_threshold:
                alert = TrendAlert(
                    id=hashlib.md5(f"{article['title']}{datetime.now()}".encode()).hexdigest()[:8],
                    timestamp=datetime.now(),
                    category='news',
                    severity=self._determine_severity(relevance, 'news'),
                    title=article['title'],
                    description=article.get('description', '')[:500],
                    data_sources=[source_name],
                    confidence=relevance,
                    requires_action=relevance > 0.85
                )
                alerts.append(alert)
        
        return alerts
    
    def _process_patent_data(self, data: Dict, source_name: str) -> List[TrendAlert]:
        """Process patent data into alerts"""
        # Implement patent-specific processing
        return []
    
    def _process_market_data(self, data: Dict, source_name: str) -> List[TrendAlert]:
        """Process market data into alerts"""
        # Implement market data processing
        return []
    
    def _process_regulatory_data(self, data: Dict, source_name: str) -> List[TrendAlert]:
        """Process regulatory data into alerts"""
        # Implement regulatory data processing
        return []
    
    def _calculate_relevance(self, content: str) -> float:
        """Calculate relevance score based on keywords"""
        content_lower = content.lower()
        total_score = 0.0
        matched_categories = set()
        
        for category, keywords in self.monitored_keywords.items():
            category_score = 0.0
            
            for kw_data in keywords:
                keyword = kw_data['keyword'].lower()
                weight = kw_data['weight']
                
                if keyword in content_lower:
                    category_score += weight * 0.2
                    matched_categories.add(category)
            
            total_score += min(category_score, 1.0)
        
        # Bonus for matching multiple categories
        if len(matched_categories) > 1:
            total_score *= (1 + len(matched_categories) * 0.1)
        
        # Special boost for Schaeffler mentions
        if 'schaeffler' in content_lower:
            total_score *= 1.5
        
        return min(total_score, 1.0)
    
    def _determine_severity(self, relevance: float, source_type: str) -> str:
        """Determine alert severity"""
        # Regulatory alerts are more critical
        if source_type == 'regulatory' and relevance > 0.7:
            return 'critical'
        
        if relevance > 0.9:
            return 'high'
        elif relevance > 0.8:
            return 'medium'
        else:
            return 'low'
    
    def _filter_alerts(self, alerts: List[TrendAlert]) -> List[TrendAlert]:
        """Filter and deduplicate alerts"""
        # Remove duplicates based on title similarity
        unique_alerts = []
        seen_titles = set()
        
        for alert in alerts:
            title_hash = hashlib.md5(alert.title.lower().encode()).hexdigest()
            if title_hash not in seen_titles:
                seen_titles.add(title_hash)
                unique_alerts.append(alert)
        
        # Sort by severity and confidence
        severity_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
        unique_alerts.sort(key=lambda a: (severity_order[a.severity], -a.confidence))
        
        return unique_alerts
    
    def save_alert(self, alert: TrendAlert):
        """Save alert to database"""
        conn = self._get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO trend_alerts 
                    (id, timestamp, category, severity, title, description,
                     data_sources, confidence, requires_action, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                    confidence = VALUES(confidence),
                    data_sources = VALUES(data_sources)
                """, (
                    alert.id, alert.timestamp, alert.category, alert.severity,
                    alert.title, alert.description, json.dumps(alert.data_sources),
                    alert.confidence, alert.requires_action, alert.status
                ))
                conn.commit()
        finally:
            conn.close()
    
    def get_recent_alerts(self, limit: int = 20) -> List[TrendAlert]:
        """Get recent alerts from database"""
        conn = self._get_db_connection()
        try:
            with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                cursor.execute("""
                    SELECT * FROM trend_alerts
                    WHERE status = 'active'
                    ORDER BY timestamp DESC
                    LIMIT %s
                """, (limit,))
                
                alerts = []
                for row in cursor.fetchall():
                    alert = TrendAlert(
                        id=row['id'],
                        timestamp=row['timestamp'],
                        category=row['category'],
                        severity=row['severity'],
                        title=row['title'],
                        description=row['description'],
                        data_sources=json.loads(row['data_sources']),
                        confidence=row['confidence'],
                        requires_action=bool(row['requires_action']),
                        status=row['status']
                    )
                    alerts.append(alert)
                
                return alerts
        finally:
            conn.close()
    
    def create_manual_alert(self, title: str, description: str, 
                          category: str = 'manual', severity: str = 'medium') -> TrendAlert:
        """Create a manual alert"""
        alert = TrendAlert(
            id=hashlib.md5(f"{title}{datetime.now()}".encode()).hexdigest()[:8],
            timestamp=datetime.now(),
            category=category,
            severity=severity,
            title=title,
            description=description,
            data_sources=['manual_entry'],
            confidence=0.9,  # High confidence for manual entries
            requires_action=severity in ['high', 'critical']
        )
        
        self.save_alert(alert)
        return alert
    
    def log_user_query(self, use_case: str, sector: str, demand: str):
        """Log user query for learning"""
        conn = self._get_db_connection()
        try:
            with conn.cursor() as cursor:
                # Extract keywords from user input for monitoring
                keywords = f"{use_case} {sector} {demand}".lower().split()
                
                # Add to performance metrics
                cursor.execute("""
                    INSERT INTO performance_metrics
                    (metric_type, metric_value, metadata, recorded_at)
                    VALUES ('user_query', 1.0, %s, %s)
                """, (
                    json.dumps({
                        'use_case': use_case,
                        'sector': sector,
                        'demand': demand,
                        'keywords': keywords
                    }),
                    datetime.now()
                ))
                conn.commit()
        finally:
            conn.close()