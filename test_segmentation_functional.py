"""
Test script for functional LCEL-style video segmentation.
"""

from agent import (
    segment_video,
    create_segmentation_chain,
    prepare_segmentation_input
)

from helpers import extract_video_id, format_duration, format_timestamp,getTranscript
from dotenv import load_dotenv

load_dotenv()


def test_functional_segmentation():
    """Test functional segment_video() approach."""
    
    print("=" * 60)
    print("FUNCTIONAL LCEL SEGMENTATION TEST")
    print("=" * 60)
    
    # Example video
    video_url = "https://www.youtube.com/watch?v=i_LwzRVP7bg"
    video_id = extract_video_id(video_url)
    
    print(f"\nVideo URL: {video_url}")
    print(f"Video ID: {video_id}\n")
    
    # Get transcript
    print("Fetching transcript...")
    transcript = getTranscript(video_id)
    
    if not transcript:
        print("❌ No transcript available")
        return
    
    snippet_count = len(transcript.snippets) if hasattr(transcript, 'snippets') else len(transcript)
    print(f"✓ Got {snippet_count} transcript snippets\n")
    
    # Segment using functional approach (no class instantiation needed)
    print("Segmenting video with functional LCEL chain...")
    print("(This may take 10-30 seconds...)\n")
    
    result = segment_video(
        video_id,
        transcript.snippets if hasattr(transcript, 'snippets') else transcript
    )
    
    # Display results
    print("=" * 60)
    print("SEGMENTATION RESULT")
    print("=" * 60)
    print(f"\nVideo ID: {result.video_id}")
    print(f"Overall Topic: {result.overall_topic}")
    print(f"Total Segments: {result.total_segments}\n")
    
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
    print("✓ Functional segmentation complete!")
    print("=" * 60)
    
    return result


def test_chain_directly():
    """Test by creating and using the chain directly (more LCEL-style)."""
    
    print("\n\n" + "=" * 60)
    print("DIRECT CHAIN TEST (Pure LCEL)")
    print("=" * 60)
    
    video_url = "https://www.youtube.com/watch?v=i_LwzRVP7bg"
    video_id = extract_video_id(video_url)
    
    print(f"\nVideo ID: {video_id}")
    
    # Get transcript
    transcript = getTranscript(video_id)
    
    # Create chain once
    print("\nCreating LCEL chain...")
    chain = create_segmentation_chain()
    print("✓ Chain created")
    
    # Prepare input
    print("Preparing input...")
    input_data = prepare_segmentation_input(
        video_id,
        transcript.snippets if hasattr(transcript, 'snippets') else transcript
    )
    print("✓ Input prepared")
    
    # Invoke chain
    print("Invoking chain...\n")
    result = chain.invoke(input_data)
    
    print(f"✓ Got {result.total_segments} segments")
    print(f"Topic: {result.overall_topic}")
    
    return result


def test_chain_reuse():
    """Test reusing the same chain multiple times (efficient pattern)."""
    
    print("\n\n" + "=" * 60)
    print("CHAIN REUSE TEST")
    print("=" * 60)
    
    # Create chain once (can be reused across requests)
    print("\nCreating chain...")
    chain = create_segmentation_chain()
    print("✓ Chain created (this chain can be reused)")
    
    video_url = "https://www.youtube.com/watch?v=i_LwzRVP7bg"
    video_id = extract_video_id(video_url)
    transcript = getTranscript(video_id)
    
    # Use the same chain multiple times
    print("\nInvoking chain (1st time)...")
    input_data = prepare_segmentation_input(video_id, transcript.snippets)
    result1 = chain.invoke(input_data)
    print(f"✓ Result 1: {result1.total_segments} segments")
    
    # Can reuse for different videos without recreating the chain
    print("\nThe same chain can be reused for other videos")
    print("without recreating the LLM connection!")
    
    return result1


if __name__ == "__main__":
    print("\n🎯 FUNCTIONAL LCEL VIDEO SEGMENTATION TESTS\n")
    
    # Test 1: Simple functional approach
    test_functional_segmentation()
    
    # Test 2: Direct chain usage
    test_chain_directly()
    
    # Test 3: Chain reuse pattern
    test_chain_reuse()
    
    print("\n" + "=" * 60)
    print("✅ All functional tests completed!")
    print("=" * 60)
    print("\nKey Differences from Class-based:")
    print("  • No VideoSegmenter() instantiation needed")
    print("  • Direct function calls: segment_video()")
    print("  • Can create/reuse chains explicitly")
    print("  • More composable with LCEL operators")
    print("=" * 60 + "\n")
