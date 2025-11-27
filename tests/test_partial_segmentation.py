"""
Test partial segmentation handling.
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import VideoDatabase
from models.pydantic_models import VideoSegment, VideoSegmentation


def test_partial_segmentation():
    """Test that partial segmentations are correctly flagged and handled."""
    
    # Use test database
    db = VideoDatabase("test_partial.db")
    
    print("Testing partial segmentation handling...")
    
    # Create mock segments (simulating partial result)
    segments = [
        VideoSegment(
            title="Segment 1",
            start_time=0,
            end_time=3600,
            summary="First hour",
            key_topics=["topic1"],
            difficulty_level="easy"
        )
    ]
    
    segmentation = VideoSegmentation(
        video_id="test_partial",
        overall_topic="Test Video [Partial: 8/21 chunks processed up to 08:00:00]",
        segments=segments,
        total_segments=1
    )
    
    # Save partial segmentation
    seg_id = db.save_segmentation(
        video_id="test_partial",
        segmentation_result=segmentation,
        chunks_processed=8,
        total_chunks=21
    )
    
    print(f"✅ Saved partial segmentation (ID: {seg_id})")
    
    # Retrieve and check status
    saved = db.get_segmentation("test_partial")
    
    assert saved is not None, "Failed to retrieve segmentation"
    assert saved["processing_status"] == "partial", f"Expected 'partial', got '{saved['processing_status']}'"
    assert saved["chunks_processed"] == 8, f"Expected 8 chunks, got {saved['chunks_processed']}"
    assert saved["total_chunks"] == 21, f"Expected 21 total, got {saved['total_chunks']}"
    
    print(f"✅ Status correctly marked as: {saved['processing_status']}")
    print(f"✅ Chunks: {saved['chunks_processed']}/{saved['total_chunks']}")
    
    # Now save complete segmentation
    complete_segments = [
        VideoSegment(
            title=f"Segment {i}",
            start_time=i*3600,
            end_time=(i+1)*3600,
            summary=f"Hour {i+1}",
            key_topics=[f"topic{i}"],
            difficulty_level="medium"
        )
        for i in range(21)
    ]
    
    complete_segmentation = VideoSegmentation(
        video_id="test_partial",
        overall_topic="Test Video - Complete",
        segments=complete_segments,
        total_segments=21
    )
    
    seg_id2 = db.save_segmentation(
        video_id="test_partial",
        segmentation_result=complete_segmentation,
        chunks_processed=None,  # Complete
        total_chunks=None
    )
    
    print(f"✅ Saved complete segmentation (ID: {seg_id2})")
    
    # Debug: check what's in database
    cursor = db.conn.cursor()
    cursor.execute("SELECT id, processing_status, chunks_processed, total_chunks FROM segmentations WHERE video_id = ?", ("test_partial",))
    rows = cursor.fetchall()
    print(f"\nDEBUG: All segmentations for test_partial:")
    for row in rows:
        print(f"  ID {row[0]}: status={row[1]}, chunks={row[2]}/{row[3]}")
    
    # Retrieve latest (should be complete)
    latest = db.get_segmentation("test_partial", latest=True)
    
    print(f"\nDEBUG: Latest segmentation ID: {latest['id']}")
    print(f"DEBUG: Latest status: {latest['processing_status']}")
    
    assert latest["processing_status"] == "complete", f"Expected 'complete', got '{latest['processing_status']}'"
    assert latest["total_segments"] == 21, f"Expected 21 segments, got {latest['total_segments']}"
    
    print(f"✅ Latest segmentation is: {latest['processing_status']}")
    print(f"✅ Total segments: {latest['total_segments']}")
    
    # Cleanup
    db.close()
    os.remove("test_partial.db")
    print("✅ Cleanup complete")
    
    print("\n🎉 Partial segmentation handling works correctly!")
    print("\nKey behaviors verified:")
    print("  ✓ Partial segmentations are marked with status='partial'")
    print("  ✓ Chunk progress is tracked (8/21)")
    print("  ✓ Complete segmentations are marked with status='complete'")
    print("  ✓ Latest segmentation retrieval works correctly")


if __name__ == "__main__":
    test_partial_segmentation()
