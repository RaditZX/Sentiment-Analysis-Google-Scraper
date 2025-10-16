from config import DB_CONFIG
import mysql.connector
from mysql.connector import Error
from datetime import datetime
import json
from typing import Optional, List, Dict


class DatabaseManager:
    
    @staticmethod
    def get_connection():
        """Create database connection"""
        try:
            conn = mysql.connector.connect(**DB_CONFIG)
            return conn
        except Error as e:
            print(f"Database connection error: {e}")
            return None
    
    @staticmethod
    def init_database():
        """Initialize database and create tables"""
        try:
            conn = DatabaseManager.get_connection()
            if not conn:
                return False
            
            cursor = conn.cursor()
            
            # Create sentiment_analysis table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sentiment_analysis (
                    id VARCHAR(255) PRIMARY KEY,
                    review_text TEXT NOT NULL,
                    rating INT NOT NULL,
                    reviewer_name VARCHAR(255),
                    review_at DATETIME,
                    sentiment VARCHAR(50) NOT NULL,
                    sentiment_score DECIMAL(3, 2) NOT NULL,
                    themes JSON,
                    analysis_reasons JSON,
                    ai_suggestions JSON,
                    processing_time_ms DECIMAL(10, 2),
                    source VARCHAR(50),
                    analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_sentiment (sentiment),
                    INDEX idx_rating (rating),
                    INDEX idx_analyzed_at (analyzed_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            
            conn.commit()
            cursor.close()
            conn.close()
            
            print("✅ Database tables initialized successfully")
            return True
            
        except Error as e:
            print(f"❌ Database initialization error: {e}")
            return False
    @staticmethod
    def parse_datetime_for_mysql(dt_str: str) -> str:
        """
        Convert ISO 8601 datetime string (with Z or timezone) 
        to MySQL DATETIME format.
        """
        if not dt_str:
            return None

        try:
            # Parsing ISO 8601 ke datetime Python
            dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
            # Format ke MySQL-compatible string
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception as e:
            print(f"Warning: invalid datetime format: {dt_str} -> {e}")
            return None
        
    @staticmethod
    def save_analysis(result: dict) -> bool:
        """Save sentiment analysis result to database"""
        try:
            conn = DatabaseManager.get_connection()
            if not conn:
                return False
            
            cursor = conn.cursor()
            
            query = """
                INSERT INTO sentiment_analysis 
                (id, review_text, rating, reviewer_name, review_at, sentiment, sentiment_score, themes, 
                 analysis_reasons, ai_suggestions, processing_time_ms, source)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    review_text = VALUES(review_text),
                    rating = VALUES(rating),
                    reviewer_name = VALUES(reviewer_name),
                    review_at = VALUES(review_at),
                    sentiment = VALUES(sentiment),
                    sentiment_score = VALUES(sentiment_score),
                    themes = VALUES(themes),
                    analysis_reasons = VALUES(analysis_reasons),
                    ai_suggestions = VALUES(ai_suggestions),
                    processing_time_ms = VALUES(processing_time_ms),
                    source = VALUES(source),
                    updated_at = CURRENT_TIMESTAMP
            """
            
            values = (
                result['id'],
                result['review_text'],
                result['rating'],
                result['reviewer_name'],
                DatabaseManager.parse_datetime_for_mysql(result['review_at']) if result.get('review_at') else None,
                result['sentiment'],
                result['sentiment_score'],
                json.dumps(result['themes'], ensure_ascii=False),
                json.dumps(result['analysis_reasons'], ensure_ascii=False),
                json.dumps(result['ai_suggestions'], ensure_ascii=False),
                result['processing_time_ms'],
                result['source']
            )
            
            cursor.execute(query, values)
            conn.commit()
            cursor.close()
            conn.close()
            
            return True
            
        except Error as e:
            print(f"Error saving to database: {e}")
            return False
    
    @staticmethod
    def get_analysis(review_id: str) -> Optional[dict]:
        """Get sentiment analysis result from database"""
        try:
            conn = DatabaseManager.get_connection()
            if not conn:
                return None
            
            cursor = conn.cursor(dictionary=True)
            
            query = """
                SELECT id, review_text, rating, reviewer_name, review_at, sentiment, sentiment_score,
                       themes, analysis_reasons, ai_suggestions, 
                       processing_time_ms, source, analyzed_at, updated_at
                FROM sentiment_analysis
                WHERE id = %s
                order by analyzed_at desc
            """
            
            cursor.execute(query, (review_id,))
            result = cursor.fetchone()
            
            cursor.close()
            conn.close()
            
            if result:
                # Parse JSON fields
                result['themes'] = json.loads(result['themes']) if result['themes'] else []
                result['analysis_reasons'] = json.loads(result['analysis_reasons']) if result['analysis_reasons'] else []
                result['ai_suggestions'] = json.loads(result['ai_suggestions']) if result['ai_suggestions'] else []
                result['analyzed_at'] = result['analyzed_at'].isoformat() if result['analyzed_at'] else None
                result['updated_at'] = result['updated_at'].isoformat() if result['updated_at'] else None
                
            return result
            
        except Error as e:
            print(f"Error fetching from database: {e}")
            return None
    
    @staticmethod
    def is_analyzed(review_id: str, review_text: str) -> bool:
        """Check if review is already analyzed (by ID and matching text)"""
        try:
            existing = DatabaseManager.get_analysis(review_id)
            if existing and existing['review_text'] == review_text:
                return True
            return False
        except Exception as e:
            print(f"Error checking analysis status: {e}")
            return False
    

    @staticmethod
    def get_all_analyses(
        limit: int = 100,
        offset: int = 0,
        sentiment_filter: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, any]:
        """Get all sentiment analyses with pagination, optional filters, and statistics summary"""
        try:
            conn = DatabaseManager.get_connection()
            if not conn:
                return {"results": [], "summary": {}}
            
            cursor = conn.cursor(dictionary=True)

            # --- Bagian Query Utama ---
            base_query = """
                FROM sentiment_analysis
                WHERE 1=1
            """
            params = []

            # Filter berdasarkan sentiment (jika ada)
            if sentiment_filter:
                base_query += " AND sentiment = %s"
                params.append(sentiment_filter)

            # Filter berdasarkan rentang tanggal (jika ada)
            if start_date:
                base_query += " AND analyzed_at >= %s"
                params.append(start_date)
            if end_date:
                base_query += " AND analyzed_at <= %s"
                params.append(end_date)

            # --- Query Data Detail ---
            data_query = f"""
                SELECT id, review_text, rating, reviewer_name, review_at, sentiment, sentiment_score,
                       themes, analysis_reasons, ai_suggestions, 
                       processing_time_ms, source, analyzed_at
                {base_query}
                ORDER BY analyzed_at DESC
                LIMIT %s OFFSET %s
            """
            cursor.execute(data_query, params + [limit, offset])
            results = cursor.fetchall()

            for result in results:
                result['themes'] = json.loads(result['themes']) if result['themes'] else []
                result['analysis_reasons'] = json.loads(result['analysis_reasons']) if result['analysis_reasons'] else []
                result['ai_suggestions'] = json.loads(result['ai_suggestions']) if result['ai_suggestions'] else []
                result['analyzed_at'] = result['analyzed_at'].isoformat() if result['analyzed_at'] else None

            # --- Query Statistik (tanpa pagination) ---
            summary_query = f"""
                SELECT 
                    COUNT(*) AS total_reviews,
                    SUM(CASE WHEN sentiment = 'Positive' THEN 1 ELSE 0 END) AS positive_count,
                    SUM(CASE WHEN sentiment = 'Negative' THEN 1 ELSE 0 END) AS negative_count,
                    SUM(CASE WHEN sentiment = 'Neutral' THEN 1 ELSE 0 END) AS neutral_count,
                    ROUND(AVG(sentiment_score), 3) AS average_sentiment_score
                {base_query}
            """
            cursor.execute(summary_query, params)
            summary = cursor.fetchone()

            cursor.close()
            conn.close()

            return {
                "results": results,
                "summary": summary
            }

        except Error as e:
            print(f"Error fetching analyses: {e}")
            return {"results": [], "summary": {}}

    @staticmethod
    def get_statistics() -> dict:
        """Get sentiment statistics"""
        try:
            conn = DatabaseManager.get_connection()
            if not conn:
                return {}
            
            cursor = conn.cursor(dictionary=True)
            
            # Overall stats
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    AVG(rating) as avg_rating,
                    AVG(sentiment_score) as avg_sentiment_score,
                    SUM(CASE WHEN sentiment = 'Positive' THEN 1 ELSE 0 END) as positive_count,
                    SUM(CASE WHEN sentiment = 'Neutral' THEN 1 ELSE 0 END) as neutral_count,
                    SUM(CASE WHEN sentiment = 'Negative' THEN 1 ELSE 0 END) as negative_count
                FROM sentiment_analysis
            """)
            
            stats = cursor.fetchone()
            
            cursor.close()
            conn.close()
            
            return {
                'total_reviews': stats['total'] or 0,
                'average_rating': round(float(stats['avg_rating'] or 0), 2),
                'average_sentiment_score': round(float(stats['avg_sentiment_score'] or 0), 2),
                'positive_count': stats['positive_count'] or 0,
                'neutral_count': stats['neutral_count'] or 0,
                'negative_count': stats['negative_count'] or 0,
                'sentiment_distribution': {
                    'Positive': round((stats['positive_count'] or 0) / max(stats['total'], 1) * 100, 1),
                    'Neutral': round((stats['neutral_count'] or 0) / max(stats['total'], 1) * 100, 1),
                    'Negative': round((stats['negative_count'] or 0) / max(stats['total'], 1) * 100, 1)
                }
            }
            
        except Error as e:
            print(f"Error getting statistics: {e}")
            return {}
