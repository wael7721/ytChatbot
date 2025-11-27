"""
Test database functionality.
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import VideoDatabase
from models.pydantic_models import VideoSegment, VideoSegmentation


def test_database():
    """Test basic database operations."""
    
    # Use test database
    db = VideoDatabase("test_videos.db")
    
    print("✅ Database created")
    
    # Create mock transcript snippets
    class MockSnippet:
        def __init__(self, text, start, duration):
            self.text = text
            self.start = start
            self.duration = duration
    
    snippets = [
        MockSnippet("Hello world", 0, 2),
        MockSnippet("This is a test", 2, 3),
        MockSnippet("Testing database", 5, 2)
    ]
    
    # Test saving video
    success = db.save_video("test123", snippets, "Test Video")
    assert success, "Failed to save video"
    print("✅ Video saved")
    
    # Test retrieving video
    video = db.get_video("test123")
    assert video is not None, "Failed to retrieve video"
    assert video["video_id"] == "test123"
    assert video["title"] == "Test Video"
    assert len(video["transcript"]) == 3
    print("✅ Video retrieved")
    
    # Test saving segmentation
    segments = [
        VideoSegment(
            title="Introduction",
            start_time=0,
            end_time=2,
            summary="Intro section",
            key_topics=["intro", "welcome"],
            difficulty_level="easy"
        ),
        VideoSegment(
            title="Main Content",
            start_time=2,
            end_time=7,
            summary="Main content section",
            key_topics=["testing", "database"],
            difficulty_level="medium"
        )
    ]
    
    segmentation = VideoSegmentation(
        video_id="test123",
        overall_topic="Database Testing",
        segments=segments,
        total_segments=2
    )
    
    seg_id = db.save_segmentation("test123", segmentation)
    assert seg_id > 0, "Failed to save segmentation"
    print("✅ Segmentation saved")
    
    # Test retrieving segmentation
    saved_seg = db.get_segmentation("test123")
    assert saved_seg is not None, "Failed to retrieve segmentation"
    assert saved_seg["overall_topic"] == "Database Testing"
    assert saved_seg["total_segments"] == 2
    print("✅ Segmentation retrieved")
    
    # Test time-based query
    time_segments = db.get_segments_by_time("test123", 1, 5)
    assert len(time_segments) == 2, "Time query failed"
    print("✅ Time-based query works")
    
    # Test search
    results = db.search_segments("test123", "database")
    assert len(results) == 1, "Search failed"
    assert "database" in results[0]["key_topics"]
    print("✅ Search works")
    
    # Cleanup
    db.close()
    os.remove("test_videos.db")
    print("✅ Cleanup complete")
    
    print("\n🎉 All tests passed!")


if __name__ == "__main__":
    test_database()
