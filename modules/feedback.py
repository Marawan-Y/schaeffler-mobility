# modules/feedback.py
import json
from datetime import datetime
from typing import Dict, List
from dataclasses import dataclass
import numpy as np
import pymysql

@dataclass
class HumanFeedback:
    """Model for capturing human feedback"""
    analysis_id: str
    feedback_type: str
    accuracy_rating: float
    usefulness_rating: float
    corrections: Dict
    comments: str
    user_id: str
    timestamp: datetime

class HumanFeedbackRL:
    """Implements human feedback reinforcement learning"""
    
    def __init__(self, db_config: Dict, learning_rate: float = 0.01):
        self.db_config = db_config
        self.learning_rate = learning_rate
        self.weights = self._load_weights()
    
    def _get_db_connection(self):
        """Get database connection"""
        return pymysql.connect(**self.db_config)
    
    def _load_weights(self) -> Dict:
        """Load model weights from database"""
        conn = self._get_db_connection()
        try:
            with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                cursor.execute("SELECT factor, weight, history FROM learning_weights")
                weights = {}
                for row in cursor.fetchall():
                    weights[row['factor']] = {
                        'weight': row['weight'],
                        'history': json.loads(row['history']) if row['history'] else []
                    }
                return weights
        finally:
            conn.close()
    
    def record_feedback(self, analysis_id: str, feedback_data: Dict, user_id: str):
        """Record human feedback and update model"""
        # Create feedback object
        feedback = HumanFeedback(
            analysis_id=analysis_id,
            feedback_type=feedback_data.get('type', 'modification'),
            accuracy_rating=feedback_data.get('accuracy', 0.5),
            usefulness_rating=feedback_data.get('usefulness', 0.5),
            corrections=feedback_data.get('corrections', {}),
            comments=feedback_data.get('comments', ''),
            user_id=user_id,
            timestamp=datetime.now()
        )
        
        # Save to database
        self._save_feedback(feedback)
        
        # Update model weights
        self._update_weights(feedback)
    
    def _save_feedback(self, feedback: HumanFeedback):
        """Save feedback to database"""
        conn = self._get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO human_feedback
                    (analysis_id, feedback_type, accuracy_rating, usefulness_rating,
                     corrections, comments, user_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    feedback.analysis_id,
                    feedback.feedback_type,
                    feedback.accuracy_rating,
                    feedback.usefulness_rating,
                    json.dumps(feedback.corrections),
                    feedback.comments,
                    feedback.user_id
                ))
                conn.commit()
        finally:
            conn.close()
    
    def _update_weights(self, feedback: HumanFeedback):
        """Update model weights based on feedback"""
        # Calculate error
        error = 1.0 - feedback.accuracy_rating
        
        # Update each factor weight
        for factor in self.weights:
            current_weight = self.weights[factor]['weight']
            
            # Calculate adjustment
            if feedback.feedback_type == 'approval':
                # Positive feedback - increase weight slightly
                adjustment = self.learning_rate * (1 - error)
                new_weight = min(1.0, current_weight + adjustment)
            elif feedback.feedback_type == 'rejection':
                # Negative feedback - decrease weight
                adjustment = self.learning_rate * error
                new_weight = max(0.1, current_weight - adjustment)
            else:  # modification
                # Moderate adjustment based on accuracy
                adjustment = self.learning_rate * (0.5 - error)
                new_weight = max(0.1, min(1.0, current_weight + adjustment))
            
            # Update weight
            self.weights[factor]['weight'] = new_weight
            
            # Record history
            history_entry = {
                'timestamp': datetime.now().isoformat(),
                'adjustment': adjustment,
                'new_weight': new_weight,
                'feedback_type': feedback.feedback_type
            }
            self.weights[factor]['history'].append(history_entry)
            
            # Keep only last 100 history entries
            if len(self.weights[factor]['history']) > 100:
                self.weights[factor]['history'] = self.weights[factor]['history'][-100:]
        
        # Save updated weights
        self._save_weights()
    
    def _save_weights(self):
        """Save weights to database"""
        conn = self._get_db_connection()
        try:
            with conn.cursor() as cursor:
                for factor, data in self.weights.items():
                    cursor.execute("""
                        UPDATE learning_weights
                        SET weight = %s,
                            history = %s,
                            adjustment_count = adjustment_count + 1
                        WHERE factor = %s
                    """, (
                        data['weight'],
                        json.dumps(data['history']),
                        factor
                    ))
                conn.commit()
        finally:
            conn.close()
    
    def get_adjusted_confidence(self, base_confidence: float, factors: Dict) -> float:
        """Adjust confidence based on learned weights"""
        adjusted = base_confidence
        
        for factor, value in factors.items():
            if factor in self.weights:
                weight = self.weights[factor]['weight']
                # Apply weight to adjust confidence
                # Value should be normalized 0-1
                factor_impact = (value - 0.5) * weight * 0.2
                adjusted += factor_impact
        
        return max(0.1, min(1.0, adjusted))
    
    def get_learning_insights(self) -> Dict:
        """Get insights from learning history"""
        conn = self._get_db_connection()
        try:
            with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                # Get total feedback count
                cursor.execute("SELECT COUNT(*) as count FROM human_feedback")
                total_feedback = cursor.fetchone()['count']
                
                # Get average ratings
                cursor.execute("""
                    SELECT 
                        AVG(accuracy_rating) as avg_accuracy,
                        AVG(usefulness_rating) as avg_usefulness
                    FROM human_feedback
                    WHERE created_at > DATE_SUB(NOW(), INTERVAL 30 DAY)
                """)
                ratings = cursor.fetchone()
                
                # Build insights
                insights = {
                    'total_feedback': total_feedback,
                    'average_accuracy': float(ratings['avg_accuracy']) if ratings['avg_accuracy'] else 0,
                    'average_usefulness': float(ratings['avg_usefulness']) if ratings['avg_usefulness'] else 0,
                    'weight_evolution': {}
                }
                
                # Add weight evolution for each factor
                for factor, data in self.weights.items():
                    if data['history']:
                        recent_history = data['history'][-10:]
                        trend = 'stable'
                        
                        if len(recent_history) >= 2:
                            recent_changes = [h['adjustment'] for h in recent_history]
                            if sum(recent_changes) > 0.1:
                                trend = 'increasing'
                            elif sum(recent_changes) < -0.1:
                                trend = 'decreasing'
                        
                        insights['weight_evolution'][factor] = {
                            'current': data['weight'],
                            'trend': trend,
                            'stability': float(np.std([h['new_weight'] for h in recent_history])) if recent_history else 0
                        }
                
                return insights
        finally:
            conn.close()
    
    def get_total_feedbacks(self) -> int:
        """Get total number of feedbacks"""
        conn = self._get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM human_feedback")
                return cursor.fetchone()[0]
        finally:
            conn.close()
    
    def get_feedback_summary(self, days: int = 7) -> Dict:
        """Get feedback summary for recent days"""
        conn = self._get_db_connection()
        try:
            with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                cursor.execute("""
                    SELECT 
                        feedback_type,
                        COUNT(*) as count,
                        AVG(accuracy_rating) as avg_accuracy,
                        AVG(usefulness_rating) as avg_usefulness
                    FROM human_feedback
                    WHERE created_at > DATE_SUB(NOW(), INTERVAL %s DAY)
                    GROUP BY feedback_type
                """, (days,))
                
                summary = {
                    'by_type': {},
                    'total': 0
                }
                
                for row in cursor.fetchall():
                    summary['by_type'][row['feedback_type']] = {
                        'count': row['count'],
                        'avg_accuracy': float(row['avg_accuracy']) if row['avg_accuracy'] else 0,
                        'avg_usefulness': float(row['avg_usefulness']) if row['avg_usefulness'] else 0
                    }
                    summary['total'] += row['count']
                
                return summary
        finally:
            conn.close()