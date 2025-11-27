"""
Database models and schema for storing video data and segmentation.
"""

import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
import json


class VideoDatabase:
    """SQLite database for storing video transcripts and segmentations."""
    
    def __init__(self, db_path: str = "videos.db"):
        """
        Initialize database connection and create tables if needed.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.conn = None
        self._connect()
        self._create_tables()
    
    def _connect(self):
        """Establish database connection."""
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row  # Enable column access by name
    
    def _create_tables(self):
        """Create database tables if they don't exist."""
        cursor = self.conn.cursor()
        
        # Videos table - stores video metadata and transcript
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS videos (
                video_id TEXT PRIMARY KEY,
                title TEXT,
                duration_seconds REAL,
                snippet_count INTEGER,
                transcript_json TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Segmentations table - stores video segmentation results
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS segmentations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                video_id TEXT NOT NULL,
                overall_topic TEXT,
                total_segments INTEGER,
                segmentation_json TEXT NOT NULL,
                processing_status TEXT DEFAULT 'complete',
                chunks_processed INTEGER,
                total_chunks INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (video_id) REFERENCES videos (video_id)
            )
        """)
        
        # Segments table - individual segments for easy querying
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS segments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                segmentation_id INTEGER NOT NULL,
                video_id TEXT NOT NULL,
                title TEXT NOT NULL,
                start_time REAL NOT NULL,
                end_time REAL NOT NULL,
                summary TEXT,
                key_topics_json TEXT,
                difficulty TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (segmentation_id) REFERENCES segmentations (id),
                FOREIGN KEY (video_id) REFERENCES videos (video_id)
            )
        """)
        
        # Create indexes for faster queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_segments_video_id 
            ON segments (video_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_segments_time 
            ON segments (video_id, start_time, end_time)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_segmentations_video_id 
            ON segmentations (video_id)
        """)
        
        self.conn.commit()
    
    def save_video(self, video_id: str, transcript_snippets: list, title: Optional[str] = None) -> bool:
        """
        Save video transcript data.
        
        Args:
            video_id: YouTube video ID
            transcript_snippets: List of transcript snippets
            title: Optional video title
        
        Returns:
            True if saved successfully
        """
        cursor = self.conn.cursor()
        
        # Calculate duration and count
        duration = transcript_snippets[-1].start + transcript_snippets[-1].duration if transcript_snippets else 0
        snippet_count = len(transcript_snippets)
        
        # Convert snippets to JSON-serializable format
        transcript_data = [
            {
                "text": snippet.text,
                "start": snippet.start,
                "duration": snippet.duration
            }
            for snippet in transcript_snippets
        ]
        
        try:
            cursor.execute("""
                INSERT INTO videos (video_id, title, duration_seconds, snippet_count, transcript_json)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(video_id) DO UPDATE SET
                    title = excluded.title,
                    duration_seconds = excluded.duration_seconds,
                    snippet_count = excluded.snippet_count,
                    transcript_json = excluded.transcript_json,
                    updated_at = CURRENT_TIMESTAMP
            """, (video_id, title, duration, snippet_count, json.dumps(transcript_data)))
            
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error saving video: {e}")
            self.conn.rollback()
            return False
    
    def get_video(self, video_id: str) -> Optional[Dict[str, Any]]:
        """
        Get video data by ID.
        
        Args:
            video_id: YouTube video ID
        
        Returns:
            Dictionary with video data or None if not found
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT video_id, title, duration_seconds, snippet_count, 
                   transcript_json, created_at, updated_at
            FROM videos
            WHERE video_id = ?
        """, (video_id,))
        
        row = cursor.fetchone()
        if not row:
            return None
        
        return {
            "video_id": row["video_id"],
            "title": row["title"],
            "duration_seconds": row["duration_seconds"],
            "snippet_count": row["snippet_count"],
            "transcript": json.loads(row["transcript_json"]),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"]
        }
    
    def save_segmentation(self, video_id: str, segmentation_result, 
                         chunks_processed: Optional[int] = None,
                         total_chunks: Optional[int] = None) -> int:
        """
        Save video segmentation result.
        
        Args:
            video_id: YouTube video ID
            segmentation_result: VideoSegmentation object
            chunks_processed: Number of chunks processed (for partial results)
            total_chunks: Total number of chunks (for partial results)
        
        Returns:
            Segmentation ID
        """
        cursor = self.conn.cursor()
        
        # Determine processing status
        if chunks_processed and total_chunks and chunks_processed < total_chunks:
            status = "partial"
        else:
            status = "complete"
        
        # Convert to JSON-serializable format
        segmentation_data = {
            "video_id": segmentation_result.video_id,
            "overall_topic": segmentation_result.overall_topic,
            "total_segments": segmentation_result.total_segments,
            "segments": [
                {
                    "title": seg.title,
                    "start_time": seg.start_time,
                    "end_time": seg.end_time,
                    "summary": seg.summary,
                    "key_topics": seg.key_topics,
                    "difficulty_level": seg.difficulty_level
                }
                for seg in segmentation_result.segments
            ]
        }
        
        try:
            # Insert segmentation
            cursor.execute("""
                INSERT INTO segmentations 
                (video_id, overall_topic, total_segments, segmentation_json, 
                 processing_status, chunks_processed, total_chunks)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                video_id,
                segmentation_result.overall_topic,
                segmentation_result.total_segments,
                json.dumps(segmentation_data),
                status,
                chunks_processed,
                total_chunks
            ))
            
            segmentation_id = cursor.lastrowid
            
            # Insert individual segments for easy querying
            for segment in segmentation_result.segments:
                cursor.execute("""
                    INSERT INTO segments 
                    (segmentation_id, video_id, title, start_time, end_time, 
                     summary, key_topics_json, difficulty)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    segmentation_id,
                    video_id,
                    segment.title,
                    segment.start_time,
                    segment.end_time,
                    segment.summary,
                    json.dumps(segment.key_topics),
                    segment.difficulty_level
                ))
            
            self.conn.commit()
            return segmentation_id
        except Exception as e:
            print(f"Error saving segmentation: {e}")
            self.conn.rollback()
            return -1
    
    def get_segmentation(self, video_id: str, latest: bool = True) -> Optional[Dict[str, Any]]:
        """
        Get segmentation for a video.
        
        Args:
            video_id: YouTube video ID
            latest: If True, get the most recent segmentation
        
        Returns:
            Dictionary with segmentation data or None if not found
        """
        cursor = self.conn.cursor()
        
        if latest:
            cursor.execute("""
                SELECT id, video_id, overall_topic, total_segments, segmentation_json,
                       processing_status, chunks_processed, total_chunks, created_at
                FROM segmentations
                WHERE video_id = ?
                ORDER BY id DESC
                LIMIT 1
            """, (video_id,))
        else:
            cursor.execute("""
                SELECT id, video_id, overall_topic, total_segments, segmentation_json,
                       processing_status, chunks_processed, total_chunks, created_at
                FROM segmentations
                WHERE video_id = ?
                ORDER BY id ASC
                LIMIT 1
            """, (video_id,))
        
        row = cursor.fetchone()
        if not row:
            return None
        
        return {
            "id": row["id"],
            "video_id": row["video_id"],
            "overall_topic": row["overall_topic"],
            "total_segments": row["total_segments"],
            "segmentation": json.loads(row["segmentation_json"]),
            "processing_status": row["processing_status"],
            "chunks_processed": row["chunks_processed"],
            "total_chunks": row["total_chunks"],
            "created_at": row["created_at"]
        }
    
    def get_segments_by_time(self, video_id: str, start_time: float, end_time: float) -> List[Dict[str, Any]]:
        """
        Get segments within a time range.
        
        Args:
            video_id: YouTube video ID
            start_time: Start time in seconds
            end_time: End time in seconds
        
        Returns:
            List of segments overlapping with the time range
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT title, start_time, end_time, summary, key_topics_json, difficulty
            FROM segments
            WHERE video_id = ?
              AND end_time >= ?
              AND start_time <= ?
            ORDER BY start_time
        """, (video_id, start_time, end_time))
        
        return [
            {
                "title": row["title"],
                "start_time": row["start_time"],
                "end_time": row["end_time"],
                "summary": row["summary"],
                "key_topics": json.loads(row["key_topics_json"]),
                "difficulty": row["difficulty"]
            }
            for row in cursor.fetchall()
        ]
    
    def search_segments(self, video_id: str, query: str) -> List[Dict[str, Any]]:
        """
        Search segments by title, summary, or topics.
        
        Args:
            video_id: YouTube video ID
            query: Search query
        
        Returns:
            List of matching segments
        """
        cursor = self.conn.cursor()
        search_pattern = f"%{query}%"
        
        cursor.execute("""
            SELECT title, start_time, end_time, summary, key_topics_json, difficulty
            FROM segments
            WHERE video_id = ?
              AND (title LIKE ? OR summary LIKE ? OR key_topics_json LIKE ?)
            ORDER BY start_time
        """, (video_id, search_pattern, search_pattern, search_pattern))
        
        return [
            {
                "title": row["title"],
                "start_time": row["start_time"],
                "end_time": row["end_time"],
                "summary": row["summary"],
                "key_topics": json.loads(row["key_topics_json"]),
                "difficulty": row["difficulty"]
            }
            for row in cursor.fetchall()
        ]
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


# Singleton instance
_db_instance = None

def get_db() -> VideoDatabase:
    """Get or create database singleton instance."""
    global _db_instance
    if _db_instance is None:
        _db_instance = VideoDatabase()
    return _db_instance
