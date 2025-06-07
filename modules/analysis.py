# modules/analysis.py
import json
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
import pymysql

@dataclass
class TrendAnalysis:
    """Model for semi-autonomous trend analysis"""
    trend_id: str
    alert_id: Optional[str]
    title: str
    analysis_date: datetime
    market_signals: Dict
    confidence_score: float
    predicted_impact: str
    recommended_actions: List[str]
    supporting_evidence: List[str]
    risk_assessment: Dict
    human_approval_required: bool
    approval_status: str = 'pending'
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        d = asdict(self)
        d['analysis_date'] = d['analysis_date'].isoformat()
        return d

class SemiAutonomousAnalyzer:
    """Performs autonomous trend analysis with human approval gates"""
    
    def __init__(self, llm_client, approval_threshold: float = 0.8):
        self.llm_client = llm_client
        self.approval_threshold = approval_threshold
        self.db_config = None
    
    def set_db_config(self, db_config: Dict):
        """Set database configuration"""
        self.db_config = db_config
    
    def _get_db_connection(self):
        """Get database connection"""
        if not self.db_config:
            raise ValueError("Database configuration not set")
        return pymysql.connect(**self.db_config)
    
    async def analyze_trend(self, alert: 'TrendAlert', context: Dict) -> TrendAnalysis:
        """Perform comprehensive trend analysis"""
        # Gather market signals
        market_signals = await self._gather_market_signals(alert)
        
        # Build analysis prompt
        prompt = self._build_analysis_prompt(alert, market_signals, context)
        
        # Get LLM analysis
        llm_response = await self._call_llm_async(prompt)
        
        # Parse response
        parsed = self._parse_llm_response(llm_response)
        
        # Calculate confidence
        confidence = self._calculate_confidence(parsed, market_signals, context)
        
        # Determine if human approval needed
        requires_approval = (
            confidence < self.approval_threshold or 
            alert.severity == 'critical' or
            parsed.get('impact', '') == 'high'
        )
        
        # Create analysis object
        analysis = TrendAnalysis(
            trend_id=f"analysis_{alert.id}",
            alert_id=alert.id,
            title=alert.title,
            analysis_date=datetime.now(),
            market_signals=market_signals,
            confidence_score=confidence,
            predicted_impact=parsed.get('impact', 'medium'),
            recommended_actions=parsed.get('actions', []),
            supporting_evidence=parsed.get('evidence', []),
            risk_assessment=parsed.get('risks', {}),
            human_approval_required=requires_approval
        )
        
        return analysis
    
    async def _gather_market_signals(self, alert: 'TrendAlert') -> Dict:
        """Gather additional market signals"""
        # In production, this would call various APIs
        # For now, return contextual mock data based on alert
        
        signals = {
            'market_size': 'Growing',
            'growth_rate': '15-20%',
            'competitor_activity': 'High',
            'regulatory_environment': 'Favorable',
            'technology_readiness': 'Maturing',
            'customer_demand': 'Increasing'
        }
        
        # Adjust based on alert category
        if alert.category == 'regulatory':
            signals['regulatory_urgency'] = 'High'
            signals['compliance_deadline'] = '12 months'
        elif alert.category == 'technology':
            signals['innovation_level'] = 'Breakthrough'
            signals['patent_activity'] = 'Increasing'
        
        return signals
    
    def _build_analysis_prompt(self, alert: 'TrendAlert', signals: Dict, context: Dict) -> str:
        """Build comprehensive analysis prompt"""
        return f"""
        Analyze this mobility trend for {context.get('company', 'Schaeffler')}:
        
        Alert: {alert.title}
        Description: {alert.description}
        Category: {alert.category}
        Confidence: {alert.confidence}
        
        Market Signals:
        {json.dumps(signals, indent=2)}
        
        Company Context:
        - Focus Areas: {', '.join(context.get('focus_areas', []))}
        - Core Competencies: {', '.join(context.get('core_competencies', []))}
        - Risk Tolerance: {context.get('risk_tolerance', 'medium')}
        
        Provide a structured analysis with:
        1. Impact assessment (low/medium/high)
        2. Recommended actions (list 3-5 specific steps)
        3. Supporting evidence (key data points)
        4. Risk assessment (identify main risks and mitigation strategies)
        
        Format the response as JSON with keys: impact, actions, evidence, risks
        """
    
    async def _call_llm_async(self, prompt: str) -> str:
        """Async wrapper for LLM call"""
        try:
            response = self.llm_client.chat.completions.create(
                model="gpt-4-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=1000
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"LLM error: {e}")
            return "{}"
    
    def _parse_llm_response(self, response: str) -> Dict:
        """Parse LLM response into structured format"""
        try:
            return json.loads(response)
        except:
            # Fallback parsing
            return {
                'impact': 'medium',
                'actions': [
                    'Conduct detailed market assessment',
                    'Evaluate technical feasibility',
                    'Identify potential partners'
                ],
                'evidence': [
                    'Market signals indicate growing opportunity',
                    'Technology aligns with core competencies'
                ],
                'risks': {
                    'market': 'Competition from established players',
                    'technical': 'Integration complexity',
                    'regulatory': 'Evolving standards'
                }
            }
    
    def _calculate_confidence(self, analysis: Dict, signals: Dict, context: Dict) -> float:
        """Calculate confidence score for analysis"""
        base_score = 0.5
        
        # Evidence strength
        evidence_count = len(analysis.get('evidence', []))
        if evidence_count >= 4:
            base_score += 0.2
        elif evidence_count >= 2:
            base_score += 0.1
        
        # Market signals strength
        positive_signals = sum(1 for v in signals.values() 
                             if isinstance(v, str) and 
                             any(word in v.lower() for word in ['high', 'growing', 'favorable', 'increasing']))
        base_score += positive_signals * 0.05
        
        # Risk assessment
        risk_count = len(analysis.get('risks', {}))
        if risk_count <= 2:
            base_score += 0.1
        elif risk_count > 4:
            base_score -= 0.1
        
        # Context alignment
        if context.get('company') == 'Schaeffler':
            # Check alignment with Schaeffler focus areas
            actions_text = ' '.join(analysis.get('actions', [])).lower()
            for focus in context.get('focus_areas', []):
                if focus.lower() in actions_text:
                    base_score += 0.05
        
        return max(0.1, min(1.0, base_score))
    
    def save_analysis(self, analysis: TrendAnalysis):
        """Save analysis to database"""
        conn = self._get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO trend_analyses
                    (trend_id, alert_id, title, analysis_date, market_signals,
                     confidence_score, predicted_impact, recommended_actions,
                     supporting_evidence, risk_assessment, human_approval_required,
                     approval_status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    analysis.trend_id,
                    analysis.alert_id,
                    analysis.title,
                    analysis.analysis_date,
                    json.dumps(analysis.market_signals),
                    analysis.confidence_score,
                    analysis.predicted_impact,
                    json.dumps(analysis.recommended_actions),
                    json.dumps(analysis.supporting_evidence),
                    json.dumps(analysis.risk_assessment),
                    analysis.human_approval_required,
                    analysis.approval_status
                ))
                conn.commit()
        finally:
            conn.close()
    
    def get_pending_analyses(self) -> List[TrendAnalysis]:
        """Get analyses pending approval"""
        conn = self._get_db_connection()
        try:
            with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                cursor.execute("""
                    SELECT * FROM trend_analyses
                    WHERE approval_status = 'pending'
                    AND human_approval_required = TRUE
                    ORDER BY analysis_date DESC
                """)
                
                analyses = []
                for row in cursor.fetchall():
                    analysis = TrendAnalysis(
                        trend_id=row['trend_id'],
                        alert_id=row['alert_id'],
                        title=row['title'],
                        analysis_date=row['analysis_date'],
                        market_signals=json.loads(row['market_signals']),
                        confidence_score=row['confidence_score'],
                        predicted_impact=row['predicted_impact'],
                        recommended_actions=json.loads(row['recommended_actions']),
                        supporting_evidence=json.loads(row['supporting_evidence']),
                        risk_assessment=json.loads(row['risk_assessment']),
                        human_approval_required=bool(row['human_approval_required']),
                        approval_status=row['approval_status']
                    )
                    analyses.append(analysis)
                
                return analyses
        finally:
            conn.close()
    
    def approve_analysis(self, analysis_id: str, user_id: str = 'system'):
        """Approve an analysis"""
        conn = self._get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE trend_analyses
                    SET approval_status = 'approved',
                        approved_by = %s,
                        approved_at = %s
                    WHERE trend_id = %s
                """, (user_id, datetime.now(), analysis_id))
                conn.commit()
        finally:
            conn.close()
    
    def get_average_confidence(self) -> float:
        """Get average confidence score"""
        conn = self._get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT AVG(confidence_score) as avg_confidence
                    FROM trend_analyses
                    WHERE analysis_date > DATE_SUB(NOW(), INTERVAL 30 DAY)
                """)
                result = cursor.fetchone()
                return float(result[0]) if result[0] else 0.0
        finally:
            conn.close()
    
    def analyze_trend_by_id(self, trend_id: str) -> Optional[TrendAnalysis]:
        """Get analysis by trend ID"""
        conn = self._get_db_connection()
        try:
            with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                cursor.execute("""
                    SELECT * FROM trend_analyses
                    WHERE trend_id = %s
                """, (trend_id,))
                
                row = cursor.fetchone()
                if row:
                    return TrendAnalysis(
                        trend_id=row['trend_id'],
                        alert_id=row['alert_id'],
                        title=row['title'],
                        analysis_date=row['analysis_date'],
                        market_signals=json.loads(row['market_signals']),
                        confidence_score=row['confidence_score'],
                        predicted_impact=row['predicted_impact'],
                        recommended_actions=json.loads(row['recommended_actions']),
                        supporting_evidence=json.loads(row['supporting_evidence']),
                        risk_assessment=json.loads(row['risk_assessment']),
                        human_approval_required=bool(row['human_approval_required']),
                        approval_status=row['approval_status']
                    )
                return None
        finally:
            conn.close()