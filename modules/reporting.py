# modules/reporting.py
import json
import hashlib
import schedule
import logging
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
import pymysql
import numpy as np

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class Report:
    """Model for automated reports"""
    id: str
    report_type: str
    period_start: datetime
    period_end: datetime
    executive_summary: str
    content: Dict
    metrics: Dict
    generated_at: datetime
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        d = asdict(self)
        d['period_start'] = d['period_start'].isoformat()
        d['period_end'] = d['period_end'].isoformat()
        d['generated_at'] = d['generated_at'].isoformat()
        return d

class ReportGenerator:
    """Generates automated reports from analyses"""
    
    def __init__(self, db_config: Dict):
        self.db_config = db_config
        self.scheduler_thread = None
    
    def _get_db_connection(self):
        """Get database connection with retry logic"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                return pymysql.connect(**self.db_config)
            except pymysql.Error as e:
                if attempt == max_retries - 1:
                    raise
                logger.warning(f"DB connection failed (attempt {attempt + 1}): {e}")
                threading.Event().wait(2)
    
    def schedule_reports(self):
        """Schedule automated report generation with proper monthly handling"""
        try:
            # Clear any existing schedules
            schedule.clear()
            
            # Daily report at 9 AM (optional)
            # schedule.every().day.at("09:00").do(lambda: self.generate_report('daily'))
            
            # Weekly report every Monday at 9 AM
            schedule.every().monday.at("09:00").do(
                lambda: self._safe_generate_report('weekly')
            )
            
            # Monthly report check (runs daily but only executes on 1st of month at 9 AM)
            schedule.every().day.at("09:00").do(self._check_monthly_report)
            
            # Start scheduler thread
            self._running = True
            self.scheduler_thread = threading.Thread(
                target=self._run_scheduler, 
                daemon=True
            )
            self.scheduler_thread.start()
            logger.info("Report scheduler started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start scheduler: {e}")
            raise
    
    def stop_scheduler(self):
        """Stop the report scheduler"""
        self._running = False
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.scheduler_thread.join(timeout=5)
        schedule.clear()
        logger.info("Report scheduler stopped")
    
    def _run_scheduler(self):
        """Internal method to run the scheduler loop"""
        while self._running:
            try:
                schedule.run_pending()
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
            finally:
                threading.Event().wait(60)  # Check every minute
    
    def _check_monthly_report(self):
        """Check if today is the 1st of month to run monthly report"""
        if datetime.now().day == 1:
            self._safe_generate_report('monthly')
    
    def _safe_generate_report(self, report_type: str):
        """Wrapper for report generation with error handling"""
        try:
            logger.info(f"Generating {report_type} report...")
            report = self.generate_report(report_type)
            logger.info(f"Successfully generated {report_type} report (ID: {report.id})")
            return report
        except Exception as e:
            logger.error(f"Failed to generate {report_type} report: {e}")
            return None
    
    def generate_report(self, report_type: str = 'weekly') -> Report:
        """Generate comprehensive report"""
        # Determine period
        period_end = datetime.now()
        if report_type == 'daily':
            period_start = period_end - timedelta(days=1)
        elif report_type == 'weekly':
            period_start = period_end - timedelta(days=7)
        elif report_type == 'monthly':
            period_start = period_end - timedelta(days=30)
        else:  # quarterly
            period_start = period_end - timedelta(days=90)
        
        # Gather data
        analyses = self._get_period_analyses(period_start, period_end)
        alerts = self._get_period_alerts(period_start, period_end)
        feedback = self._get_period_feedback(period_start, period_end)
        
        # Generate report content
        report = Report(
            id=hashlib.md5(f"{report_type}{period_end}".encode()).hexdigest()[:8],
            report_type=report_type,
            period_start=period_start,
            period_end=period_end,
            executive_summary=self._create_executive_summary(analyses, alerts, feedback),
            content=self._create_report_content(analyses, alerts, feedback),
            metrics=self._calculate_metrics(analyses, alerts, feedback),
            generated_at=datetime.now()
        )
        
        # Save report
        self._save_report(report)
        
        return report
    
    def _get_period_analyses(self, start: datetime, end: datetime) -> List[Dict]:
        """Get analyses for period"""
        conn = self._get_db_connection()
        try:
            with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                cursor.execute("""
                    SELECT * FROM trend_analyses
                    WHERE analysis_date BETWEEN %s AND %s
                    ORDER BY confidence_score DESC
                """, (start, end))
                return cursor.fetchall()
        finally:
            conn.close()
    
    def _get_period_alerts(self, start: datetime, end: datetime) -> List[Dict]:
        """Get alerts for period"""
        conn = self._get_db_connection()
        try:
            with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                cursor.execute("""
                    SELECT * FROM trend_alerts
                    WHERE timestamp BETWEEN %s AND %s
                    ORDER BY severity, confidence DESC
                """, (start, end))
                return cursor.fetchall()
        finally:
            conn.close()
    
    def _get_period_feedback(self, start: datetime, end: datetime) -> List[Dict]:
        """Get feedback for period"""
        conn = self._get_db_connection()
        try:
            with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                cursor.execute("""
                    SELECT * FROM human_feedback
                    WHERE created_at BETWEEN %s AND %s
                """, (start, end))
                return cursor.fetchall()
        finally:
            conn.close()
    
    def _create_executive_summary(self, analyses: List[Dict], alerts: List[Dict], 
                                feedback: List[Dict]) -> str:
        """Create executive summary"""
        high_impact = [a for a in analyses if a.get('predicted_impact') == 'high']
        critical_alerts = [a for a in alerts if a.get('severity') == 'critical']
        
        avg_confidence = np.mean([a.get('confidence_score', 0) for a in analyses]) if analyses else 0
        
        summary = f"""# Executive Summary - Schaeffler Mobility Insights

## Period Overview
- **Total Trends Identified**: {len(alerts)}
- **Analyses Performed**: {len(analyses)}
- **High-Impact Opportunities**: {len(high_impact)}
- **Critical Alerts**: {len(critical_alerts)}
- **Average Confidence Score**: {avg_confidence:.2%}

## Key Highlights
"""
        
        # Add top 3 high-impact trends
        if high_impact:
            summary += "\n### High-Impact Opportunities:\n"
            for i, analysis in enumerate(high_impact[:3], 1):
                summary += f"{i}. **{analysis['title']}** - {analysis.get('predicted_impact', 'Unknown')} impact\n"
        
        # Add critical actions
        critical_actions = []
        for analysis in analyses[:5]:
            if analysis.get('recommended_actions'):
                actions = json.loads(analysis['recommended_actions'])
                critical_actions.extend(actions[:2])
        
        if critical_actions:
            summary += "\n### Immediate Actions Required:\n"
            for i, action in enumerate(critical_actions[:5], 1):
                summary += f"{i}. {action}\n"
        
        # Add performance metrics
        if feedback:
            avg_accuracy = np.mean([f.get('accuracy_rating', 0) for f in feedback])
            summary += f"\n### System Performance:\n- **Analysis Accuracy**: {avg_accuracy:.2%}\n"
            summary += f"- **Human Approvals**: {len([f for f in feedback if f['feedback_type'] == 'approval'])}\n"
        
        return summary
    
    def _create_report_content(self, analyses: List[Dict], alerts: List[Dict], 
                             feedback: List[Dict]) -> Dict:
        """Create detailed report content"""
        content = {
            'trend_analyses': [],
            'key_recommendations': [],
            'risk_overview': {},
            'market_insights': {},
            'partner_opportunities': []
        }
        
        # Process analyses
        for analysis in analyses:
            content['trend_analyses'].append({
                'title': analysis['title'],
                'impact': analysis['predicted_impact'],
                'confidence': analysis['confidence_score'],
                'signals': json.loads(analysis['market_signals']) if analysis['market_signals'] else {},
                'actions': json.loads(analysis['recommended_actions']) if analysis['recommended_actions'] else [],
                'risks': json.loads(analysis['risk_assessment']) if analysis['risk_assessment'] else {}
            })
            
            # Extract recommendations
            actions = json.loads(analysis['recommended_actions']) if analysis['recommended_actions'] else []
            for action in actions:
                content['key_recommendations'].append({
                    'action': action,
                    'trend': analysis['title'],
                    'impact': analysis['predicted_impact'],
                    'confidence': analysis['confidence_score']
                })
        
        # Sort recommendations by impact and confidence
        content['key_recommendations'].sort(
            key=lambda x: (
                {'high': 3, 'medium': 2, 'low': 1}.get(x['impact'], 0),
                x['confidence']
            ),
            reverse=True
        )
        
        # Compile risk overview
        risk_categories = {}
        for analysis in analyses:
            risks = json.loads(analysis['risk_assessment']) if analysis['risk_assessment'] else {}
            for risk_type, risk_desc in risks.items():
                if risk_type not in risk_categories:
                    risk_categories[risk_type] = []
                risk_categories[risk_type].append({
                    'trend': analysis['title'],
                    'description': risk_desc
                })
        content['risk_overview'] = risk_categories
        
        # Extract market insights
        market_categories = {}
        for alert in alerts:
            category = alert['category']
            if category not in market_categories:
                market_categories[category] = []
            market_categories[category].append({
                'title': alert['title'],
                'severity': alert['severity'],
                'confidence': alert['confidence']
            })
        content['market_insights'] = market_categories
        
        return content
    
    def _calculate_metrics(self, analyses: List[Dict], alerts: List[Dict], 
                         feedback: List[Dict]) -> Dict:
        """Calculate report metrics"""
        metrics = {
            'total_alerts': len(alerts),
            'alerts_by_severity': {},
            'total_analyses': len(analyses),
            'analyses_by_impact': {},
            'average_confidence': 0,
            'auto_approved': 0,
            'human_approved': 0,
            'system_accuracy': 0,
            'response_time': 0
        }
        
        # Count by severity
        for alert in alerts:
            severity = alert['severity']
            metrics['alerts_by_severity'][severity] = metrics['alerts_by_severity'].get(severity, 0) + 1
        
        # Count by impact
        for analysis in analyses:
            impact = analysis['predicted_impact']
            metrics['analyses_by_impact'][impact] = metrics['analyses_by_impact'].get(impact, 0) + 1
        
        # Calculate averages
        if analyses:
            metrics['average_confidence'] = np.mean([a['confidence_score'] for a in analyses])
            metrics['auto_approved'] = len([a for a in analyses if not a['human_approval_required']])
            metrics['human_approved'] = len([a for a in analyses if a['approval_status'] == 'approved'])
        
        if feedback:
            metrics['system_accuracy'] = np.mean([f['accuracy_rating'] for f in feedback])
        
        return metrics
    
    def _save_report(self, report: Report):
        """Save report to database"""
        conn = self._get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO automated_reports
                    (id, report_type, period_start, period_end, executive_summary,
                     content, metrics, generated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    report.id,
                    report.report_type,
                    report.period_start,
                    report.period_end,
                    report.executive_summary,
                    json.dumps(report.content),
                    json.dumps(report.metrics),
                    report.generated_at
                ))
                conn.commit()
        finally:
            conn.close()
    
    def get_latest_report(self, report_type: str = 'weekly') -> Optional[Report]:
        """Get the latest report of given type"""
        conn = self._get_db_connection()
        try:
            with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                cursor.execute("""
                    SELECT * FROM automated_reports
                    WHERE report_type = %s
                    ORDER BY generated_at DESC
                    LIMIT 1
                """, (report_type,))
                
                row = cursor.fetchone()
                if row:
                    return Report(
                        id=row['id'],
                        report_type=row['report_type'],
                        period_start=row['period_start'],
                        period_end=row['period_end'],
                        executive_summary=row['executive_summary'],
                        content=json.loads(row['content']),
                        metrics=json.loads(row['metrics']),
                        generated_at=row['generated_at']
                    )
                return None
        finally:
            conn.close()
    
    def get_report_history(self, report_type: str = None, limit: int = 10) -> List[Report]:
        """Get report history"""
        conn = self._get_db_connection()
        try:
            with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                if report_type:
                    cursor.execute("""
                        SELECT * FROM automated_reports
                        WHERE report_type = %s
                        ORDER BY generated_at DESC
                        LIMIT %s
                    """, (report_type, limit))
                else:
                    cursor.execute("""
                        SELECT * FROM automated_reports
                        ORDER BY generated_at DESC
                        LIMIT %s
                    """, (limit,))
                
                reports = []
                for row in cursor.fetchall():
                    report = Report(
                        id=row['id'],
                        report_type=row['report_type'],
                        period_start=row['period_start'],
                        period_end=row['period_end'],
                        executive_summary=row['executive_summary'],
                        content=json.loads(row['content']),
                        metrics=json.loads(row['metrics']),
                        generated_at=row['generated_at']
                    )
                    reports.append(report)
                
                return reports
        finally:
            conn.close()
    
    def generate_custom_report(self, start_date: datetime, end_date: datetime, 
                             focus_areas: List[str] = None) -> Report:
        """Generate custom report for specific period and focus areas"""
        # Get data for custom period
        analyses = self._get_period_analyses(start_date, end_date)
        alerts = self._get_period_alerts(start_date, end_date)
        feedback = self._get_period_feedback(start_date, end_date)
        
        # Filter by focus areas if provided
        if focus_areas:
            analyses = [a for a in analyses 
                       if any(focus.lower() in a['title'].lower() for focus in focus_areas)]
            alerts = [a for a in alerts 
                     if any(focus.lower() in a['title'].lower() for focus in focus_areas)]
        
        # Generate custom report
        report = Report(
            id=hashlib.md5(f"custom_{start_date}_{end_date}".encode()).hexdigest()[:8],
            report_type='custom',
            period_start=start_date,
            period_end=end_date,
            executive_summary=self._create_executive_summary(analyses, alerts, feedback),
            content=self._create_report_content(analyses, alerts, feedback),
            metrics=self._calculate_metrics(analyses, alerts, feedback),
            generated_at=datetime.now()
        )
        
        # Save report
        self._save_report(report)
        
        return report