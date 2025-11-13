"""
Test script for video segmentation functionality.
"""

from agent import VideoSegmenter
from helpers.getTranscript import getTranscript
from helpers import extract_video_id, format_duration, format_timestamp
from dotenv import load_dotenv
load_dotenv()

def test_segmentation():
    """Test video segmentation with an example video."""
    
    # Example: Linear regression video
    video_url = "https://www.youtube.com/watch?v=i_LwzRVP7bg"
    
    print("=" * 60)
    print("VIDEO SEGMENTATION TEST")
    print("=" * 60)
    print(f"\nVideo URL: {video_url}")
    
    # Extract video ID
    video_id = extract_video_id(video_url)
    print(f"Video ID: {video_id}\n")
    
    # Get transcript
    print("Fetching transcript...")
    transcript = getTranscript(video_id)
    
    if not transcript:
        print("❌ No transcript available")
        return
    
    snippet_count = len(transcript.snippets) if hasattr(transcript, 'snippets') else len(transcript)
    print(f"✓ Got {snippet_count} transcript snippets\n")
    
    # Initialize segmenter
    print("Initializing AI segmenter...")
    segmenter = VideoSegmenter()
    print("✓ Segmenter ready\n")
    
    # Segment the video
    print("Analyzing video and identifying segments...")
    print("(This may take 10-30 seconds...)\n")
    
    result = segmenter.segment(
        video_id, 
        transcript.snippets if hasattr(transcript, 'snippets') else transcript
    )
    
    print("=" * 60)
    print("SEGMENTATION RESULT")
    print("=" * 60)
    print(f"\nVideo ID: {result.video_id}")
    print(f"Overall Topic: {result.overall_topic}")
    print(f"Total Segments: {result.total_segments}\n")
    
    # Display each segment
    for i, segment in enumerate(result.segments, 1):
        print(f"\n{'─' * 60}")
        print(f"SEGMENT {i}: {segment.title}")
        print(f"{'─' * 60}")
        print(f"Time Range: {format_timestamp(segment.start_time)} → {format_timestamp(segment.end_time)}")
        duration_seconds = segment.end_time - segment.start_time
        print(f"Duration: {format_duration(duration_seconds)}")
        print(f"Difficulty: {segment.difficulty_level}")
        print(f"\nSummary:")
        print(f"  {segment.summary}")
        print(f"\nKey Topics:")
        for topic in segment.key_topics:
            print(f"  • {topic}")
    
    print("\n" + "=" * 60)
    print("✓ Segmentation complete!")
    print("=" * 60)
    
    return result


if __name__ == "__main__":
    test_segmentation()
