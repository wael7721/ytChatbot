"""
Example: Using database in conversational chatbot.

This shows how to access video data and segments from the database
to provide context-aware responses.
"""

from models import get_db


def get_video_context(video_id: str) -> dict:
    """
    Get full context about a video from database.
    
    Args:
        video_id: YouTube video ID
    
    Returns:
        Dictionary with video data, segments, and metadata
    """
    db = get_db()
    
    # Get video transcript
    video = db.get_video(video_id)
    if not video:
        return {"error": f"Video {video_id} not found in database"}
    
    # Get segmentation
    segmentation = db.get_segmentation(video_id)
    if not segmentation:
        return {
            "video_id": video_id,
            "transcript": video["transcript"],
            "duration": video["duration_seconds"],
            "segments": None,
            "error": "Segmentation not available"
        }
    
    return {
        "video_id": video_id,
        "transcript": video["transcript"],
        "duration": video["duration_seconds"],
        "overall_topic": segmentation["overall_topic"],
        "segments": segmentation["segmentation"]["segments"],
        "total_segments": segmentation["total_segments"]
    }


def get_segment_at_timestamp(video_id: str, timestamp: float) -> dict:
    """
    Get the segment that contains a specific timestamp.
    
    Args:
        video_id: YouTube video ID
        timestamp: Time in seconds
    
    Returns:
        Segment information or None
    """
    db = get_db()
    
    # Get segments overlapping with this timestamp
    segments = db.get_segments_by_time(video_id, timestamp, timestamp + 1)
    
    if not segments:
        return None
    
    # Return the first segment (most relevant)
    return segments[0]


def search_video_topics(video_id: str, query: str) -> list:
    """
    Search for segments related to a query.
    
    Args:
        video_id: YouTube video ID
        query: Search query
    
    Returns:
        List of relevant segments
    """
    db = get_db()
    return db.search_segments(video_id, query)


def get_transcript_snippet(video_id: str, start_time: float, end_time: float) -> str:
    """
    Get transcript text for a specific time range.
    
    Args:
        video_id: YouTube video ID
        start_time: Start time in seconds
        end_time: End time in seconds
    
    Returns:
        Transcript text for the time range
    """
    db = get_db()
    
    video = db.get_video(video_id)
    if not video:
        return ""
    
    # Filter transcript snippets by time
    relevant_snippets = [
        snippet for snippet in video["transcript"]
        if snippet["start"] >= start_time and snippet["start"] < end_time
    ]
    
    return " ".join(snippet["text"] for snippet in relevant_snippets)


# Example usage in conversational context
if __name__ == "__main__":
    # Example video ID
    video_id = "dQw4w9WgXcQ"
    
    # Get full context
    context = get_video_context(video_id)
    print(f"Video topic: {context.get('overall_topic')}")
    print(f"Total segments: {context.get('total_segments')}")
    
    # Find segment at 5 minutes
    segment = get_segment_at_timestamp(video_id, 300)
    if segment:
        print(f"\nAt 5:00 - {segment['title']}")
        print(f"Topics: {', '.join(segment['key_topics'])}")
    
    # Search for specific topic
    results = search_video_topics(video_id, "machine learning")
    print(f"\nFound {len(results)} segments about 'machine learning'")
    for seg in results:
        print(f"  - {seg['title']} ({seg['start_time']}s - {seg['end_time']}s)")
    
    # Get transcript for first minute
    transcript = get_transcript_snippet(video_id, 0, 60)
    print(f"\nFirst minute transcript:\n{transcript[:200]}...")
