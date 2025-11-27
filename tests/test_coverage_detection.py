"""
Test coverage-based detection of incomplete segmentations.
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import VideoDatabase
from models.pydantic_models import VideoSegment, VideoSegmentation


def test_coverage_detection():
    """Test that incomplete coverage is properly detected."""
    
    # Use test database
    db = VideoDatabase("test_coverage.db")
    
    print("Testing coverage-based detection...\n")
    
    # Create mock transcript for 2-hour video (7200 seconds)
    class MockSnippet:
        def __init__(self, text, start, duration):
            self.text = text
            self.start = start
            self.duration = duration
    
    # Create snippets spanning 2 hours
    snippets = [
        MockSnippet(f"Text {i}", i * 10, 10)
        for i in range(720)  # 720 snippets * 10 seconds = 7200 seconds
    ]
    
    # Save video
    db.save_video("coverage_test", snippets, "2-Hour Test Video")
    print("✅ Saved video (duration: 7200s = 2 hours)")
    
    # Test Case 1: Incomplete segmentation (only first hour)
    print("\n--- Test Case 1: Incomplete (only first hour) ---")
    incomplete_segments = [
        VideoSegment(
            title=f"Segment {i}",
            start_time=i * 600,
            end_time=(i + 1) * 600,
            summary=f"Content {i}",
            key_topics=[f"topic{i}"],
            difficulty_level="medium"
        )
        for i in range(6)  # 6 segments * 600s = 3600s (only 1 hour)
    ]
    
    incomplete_seg = VideoSegmentation(
        video_id="coverage_test",
        overall_topic="Test Video",
        segments=incomplete_segments,
        total_segments=6
    )
    
    seg_id1 = db.save_segmentation("coverage_test", incomplete_seg)
    print(f"Saved segmentation covering 0-3600s (50% of video)")
    
    # Retrieve and check
    cached = db.get_segmentation("coverage_test")
    
    # Manually check coverage
    from endpoints.segmentation import _verify_segmentation_coverage
    is_complete = _verify_segmentation_coverage(cached, "coverage_test", db)
    
    assert not is_complete, "Should detect as incomplete (only 50% covered)"
    print("✅ Correctly detected as incomplete\n")
    
    # Test Case 2: Complete segmentation (covers 95%+)
    print("--- Test Case 2: Complete (covers 95%+) ---")
    complete_segments = [
        VideoSegment(
            title=f"Segment {i}",
            start_time=i * 600,
            end_time=(i + 1) * 600,
            summary=f"Content {i}",
            key_topics=[f"topic{i}"],
            difficulty_level="medium"
        )
        for i in range(12)  # 12 segments * 600s = 7200s (full 2 hours)
    ]
    
    complete_seg = VideoSegmentation(
        video_id="coverage_test",
        overall_topic="Test Video Complete",
        segments=complete_segments,
        total_segments=12
    )
    
    seg_id2 = db.save_segmentation("coverage_test", complete_seg)
    print(f"Saved segmentation covering 0-7200s (100% of video)")
    
    # Retrieve latest
    cached_complete = db.get_segmentation("coverage_test")
    is_complete = _verify_segmentation_coverage(cached_complete, "coverage_test", db)
    
    assert is_complete, "Should detect as complete (100% covered)"
    print("✅ Correctly detected as complete\n")
    
    # Test Case 3: Borderline case (96% coverage)
    print("--- Test Case 3: Borderline (96% coverage) ---")
    borderline_segments = [
        VideoSegment(
            title=f"Segment {i}",
            start_time=i * 600,
            end_time=(i + 1) * 600,
            summary=f"Content {i}",
            key_topics=[f"topic{i}"],
            difficulty_level="medium"
        )
        for i in range(11)  # 11 segments * 600s = 6600s (91.6%)
    ]
    # Add a 12th segment that ends at 6912s (96%)
    borderline_segments.append(
        VideoSegment(
            title="Final Segment",
            start_time=6600,
            end_time=6912,  # 96% of 7200
            summary="Final content",
            key_topics=["finale"],
            difficulty_level="easy"
        )
    )
    
    borderline_seg = VideoSegmentation(
        video_id="coverage_test",
        overall_topic="Test Video Borderline",
        segments=borderline_segments,
        total_segments=12
    )
    
    seg_id3 = db.save_segmentation("coverage_test", borderline_seg)
    print(f"Saved segmentation covering 0-6912s (96% of video)")
    
    cached_borderline = db.get_segmentation("coverage_test")
    is_complete = _verify_segmentation_coverage(cached_borderline, "coverage_test", db)
    
    assert is_complete, "Should detect as complete (96% > 95% threshold)"
    print("✅ Correctly detected as complete (above 95% threshold)\n")
    
    # Cleanup
    db.close()
    os.remove("test_coverage.db")
    print("✅ Cleanup complete")
    
    print("\n🎉 Coverage detection works correctly!")
    print("\nKey behaviors verified:")
    print("  ✓ Detects incomplete segmentation (50% coverage)")
    print("  ✓ Accepts complete segmentation (100% coverage)")
    print("  ✓ Accepts borderline segmentation (96% coverage, above 95% threshold)")


if __name__ == "__main__":
    test_coverage_detection()
