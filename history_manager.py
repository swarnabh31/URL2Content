import sqlite3
import logging
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class HistoryManager:
    """
    Manages persistent storage of generated content using SQLite.
    Provides functionality to save, retrieve, search, and rate generations.
    """
    
    def __init__(self, db_path: str = "./content_history.db"):
        """
        Initialize the history manager with a SQLite database.
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        # Ensure the directory exists
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        logger.info(f"HistoryManager initialized with database: {self.db_path}")
    
    def _init_db(self):
        """Initialize the database schema if it doesn't exist."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS generations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        url TEXT NOT NULL,
                        video_title TEXT,
                        content_type TEXT NOT NULL,
                        model TEXT NOT NULL,
                        generated_content TEXT NOT NULL,
                        transcript_length INTEGER,
                        generation_time_ms INTEGER,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        user_rating INTEGER,  -- 1-5 stars
                        user_feedback TEXT
                    )
                """)
                # Create indexes for better query performance
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_created_at 
                    ON generations(created_at DESC)
                """)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_content_type 
                    ON generations(content_type)
                """)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_model 
                    ON generations(model)
                """)
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    def save(self, url: str, content_type: str, model: str, 
             content: str, transcript_len: int, duration_ms: int,
             video_title: Optional[str] = None) -> int:
        """
        Save a generation record to the database.
        
        Args:
            url: YouTube URL of the source video
            content_type: Type of content generated (Summary, Blog Post, etc.)
            model: Ollama model used for generation
            content: The generated content
            transcript_len: Length of the source transcript in characters
            duration_ms: Generation time in milliseconds
            video_title: Optional title of the YouTube video
            
        Returns:
            int: The ID of the inserted record
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    INSERT INTO generations 
                    (url, video_title, content_type, model, generated_content, 
                     transcript_length, generation_time_ms)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (url, video_title, content_type, model, content, 
                      transcript_len, duration_ms))
                record_id = cursor.lastrowid
                conn.commit()
                logger.info(f"Saved generation record with ID: {record_id}")
                return record_id
        except Exception as e:
            logger.error(f"Failed to save generation record: {e}")
            raise
    
    def get_recent(self, limit: int = 20) -> List[Dict]:
        """
        Get the most recent generations.
        
        Args:
            limit: Maximum number of records to return
            
        Returns:
            List of dictionaries representing generation records
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(
                    "SELECT * FROM generations ORDER BY created_at DESC LIMIT ?", 
                    (limit,)
                ).fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to retrieve recent generations: {e}")
            return []
    
    def search(self, query: str) -> List[Dict]:
        """
        Full-text search across all generated content.
        
        Args:
            query: Search term to look for in generated content
            
        Returns:
            List of dictionaries matching the search query
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(
                    "SELECT * FROM generations WHERE generated_content LIKE ? ORDER BY created_at DESC",
                    (f"%{query}%",)
                ).fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to search generations: {e}")
            return []
    
    def get_by_id(self, record_id: int) -> Optional[Dict]:
        """
        Get a specific generation record by ID.
        
        Args:
            record_id: The ID of the record to retrieve
            
        Returns:
            Dictionary representing the generation record, or None if not found
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                row = conn.execute(
                    "SELECT * FROM generations WHERE id = ?", 
                    (record_id,)
                ).fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Failed to retrieve generation by ID {record_id}: {e}")
            return None
    
    def update_rating(self, record_id: int, rating: int) -> bool:
        """
        Update the user rating for a generation record.
        
        Args:
            record_id: The ID of the record to update
            rating: The user rating (1-5)
            
        Returns:
            bool: True if update was successful, False otherwise
        """
        if rating < 1 or rating > 5:
            logger.warning(f"Invalid rating value: {rating}. Must be between 1 and 5.")
            return False
            
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "UPDATE generations SET user_rating = ? WHERE id = ?",
                    (rating, record_id)
                )
                conn.commit()
                logger.info(f"Updated rating for record {record_id} to {rating}")
                return True
        except Exception as e:
            logger.error(f"Failed to update rating for record {record_id}: {e}")
            return False
    
    def update_feedback(self, record_id: int, feedback: str) -> bool:
        """
        Update the user feedback for a generation record.
        
        Args:
            record_id: The ID of the record to update
            feedback: User feedback text
            
        Returns:
            bool: True if update was successful, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "UPDATE generations SET user_feedback = ? WHERE id = ?",
                    (feedback, record_id)
                )
                conn.commit()
                logger.info(f"Updated feedback for record {record_id}")
                return True
        except Exception as e:
            logger.error(f"Failed to update feedback for record {record_id}: {e}")
            return False
    
    def get_stats(self) -> Dict:
        """
        Get usage statistics from the history database.
        
        Returns:
            Dictionary containing various statistics
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Total generations
                total = conn.execute("SELECT COUNT(*) FROM generations").fetchone()[0]
                
                # Generations by content type
                type_stats = conn.execute("""
                    SELECT content_type, COUNT(*) as count 
                    FROM generations 
                    GROUP BY content_type
                """).fetchall()
                
                # Generations by model
                model_stats = conn.execute("""
                    SELECT model, COUNT(*) as count 
                    FROM generations 
                    GROUP BY model
                """).fetchall()
                
                # Average generation time
                avg_time = conn.execute("""
                    SELECT AVG(generation_time_ms) 
                    FROM generations 
                    WHERE generation_time_ms IS NOT NULL
                """).fetchone()[0]
                
                # Average transcript length
                avg_transcript = conn.execute("""
                    SELECT AVG(transcript_length) 
                    FROM generations 
                    WHERE transcript_length IS NOT NULL
                """).fetchone()[0]
                
                return {
                    "total_generations": total,
                    "by_content_type": dict(type_stats),
                    "by_model": dict(model_stats),
                    "avg_generation_time_ms": round(avg_time, 2) if avg_time else 0,
                    "avg_transcript_length": round(avg_transcript, 2) if avg_transcript else 0
                }
        except Exception as e:
            logger.error(f"Failed to generate statistics: {e}")
            return {}