# utils/database.py
import pymysql
import json
from contextlib import contextmanager
from typing import Dict, List, Optional

@contextmanager
def get_db_connection(db_config: Dict):
    """Context manager for database connections"""
    conn = None
    try:
        conn = pymysql.connect(**db_config)
        yield conn
    except Exception as e:
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()

def save_to_db(uc: str, sec: str, dem: str, trends_md: str, sel: str, 
               ass: str, rad: str, pes: str, msol: str, prts: str,
               titles: List[str], blocks: List[str], db_config: Dict):
    """Save trend query to database"""
    confidence_score = None
    
    # Extract confidence score from selected trend
    if titles and blocks and sel in titles:
        idx = titles.index(sel)
        if idx < len(blocks):
            import re
            m = re.search(r"Confidence\s*Score:\s*([0-9.]+)", blocks[idx], re.IGNORECASE)
            confidence_score = float(m.group(1)) if m else 0.5
    
    try:
        with get_db_connection(db_config) as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO trend_queries (
                        use_case, sector, demand, selected_trend,
                        trend_solutions, trend_assessment, radar_positioning,
                        pestel_tag, market_solution, partners, confidence_score
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """, (uc, sec, dem, sel, trends_md, ass, rad, pes,
                      msol, prts, confidence_score))
                conn.commit()
    except Exception as e:
        print(f"Database error saving trend query: {e}")
        raise

def get_trend_history(use_case: str = None, sector: str = None, 
                     limit: int = 10, db_config: Dict = None) -> List[Dict]:
    """Get trend query history"""
    with get_db_connection(db_config) as conn:
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            query = "SELECT * FROM trend_queries WHERE 1=1"
            params = []
            
            if use_case:
                query += " AND use_case = %s"
                params.append(use_case)
            if sector:
                query += " AND sector = %s"
                params.append(sector)
            
            query += " ORDER BY created_at DESC LIMIT %s"
            params.append(limit)
            
            cursor.execute(query, params)
            return cursor.fetchall()

def get_performance_metrics(metric_type: str = None, days: int = 30, 
                          db_config: Dict = None) -> List[Dict]:
    """Get performance metrics"""
    with get_db_connection(db_config) as conn:
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            query = """
                SELECT * FROM performance_metrics 
                WHERE recorded_at > DATE_SUB(NOW(), INTERVAL %s DAY)
            """
            params = [days]
            
            if metric_type:
                query += " AND metric_type = %s"
                params.append(metric_type)
            
            query += " ORDER BY recorded_at DESC"
            
            cursor.execute(query, params)
            return cursor.fetchall()

def save_session_data(session_id: str, user_id: str, data: Dict, 
                     db_config: Dict = None):
    """Save user session data"""
    with get_db_connection(db_config) as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO user_sessions (session_id, user_id, data, last_activity)
                VALUES (%s, %s, %s, NOW())
                ON DUPLICATE KEY UPDATE
                data = VALUES(data),
                last_activity = NOW()
            """, (session_id, user_id, json.dumps(data)))
            conn.commit()

def cleanup_old_data(days: int = 90, db_config: Dict = None):
    """Cleanup old data from various tables"""
    with get_db_connection(db_config) as conn:
        with conn.cursor() as cursor:
            # Clean old alerts
            cursor.execute("""
                UPDATE trend_alerts 
                SET status = 'archived'
                WHERE timestamp < DATE_SUB(NOW(), INTERVAL %s DAY)
                AND status = 'resolved'
            """, (days,))
            
            # Clean old sessions
            cursor.execute("""
                DELETE FROM user_sessions
                WHERE last_activity < DATE_SUB(NOW(), INTERVAL 7 DAY)
            """)
            
            # Archive old performance metrics
            cursor.execute("""
                DELETE FROM performance_metrics
                WHERE recorded_at < DATE_SUB(NOW(), INTERVAL %s DAY)
            """, (days * 2,))
            
            conn.commit()
            
            return cursor.rowcount