"""
Database initialization and utility functions.
"""

from models.database import VideoDatabase, get_db


def init_database(db_path: str = "videos.db") -> VideoDatabase:
    """
    Initialize the database with tables.
    
    Args:
        db_path: Path to SQLite database file
    
    Returns:
        VideoDatabase instance
    """
    db = VideoDatabase(db_path)
    print(f"✅ Database initialized at {db_path}")
    return db


def get_database_stats(db: VideoDatabase = None) -> dict:
    """
    Get statistics about the database.
    
    Args:
        db: VideoDatabase instance (uses singleton if not provided)
    
    Returns:
        Dictionary with database statistics
    """
    if db is None:
        db = get_db()
    
    cursor = db.conn.cursor()
    
    # Count videos
    cursor.execute("SELECT COUNT(*) FROM videos")
    video_count = cursor.fetchone()[0]
    
    # Count segmentations
    cursor.execute("SELECT COUNT(*) FROM segmentations")
    segmentation_count = cursor.fetchone()[0]
    
    # Count segments
    cursor.execute("SELECT COUNT(*) FROM segments")
    segment_count = cursor.fetchone()[0]
    
    # Get total duration
    cursor.execute("SELECT SUM(duration_seconds) FROM videos")
    total_duration = cursor.fetchone()[0] or 0
    
    return {
        "videos": video_count,
        "segmentations": segmentation_count,
        "segments": segment_count,
        "total_duration_seconds": total_duration,
        "total_duration_hours": round(total_duration / 3600, 2)
    }


if __name__ == "__main__":
    # Initialize database when run directly
    db = init_database()
    stats = get_database_stats(db)
    print("\nDatabase Statistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
