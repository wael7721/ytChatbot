"""
Segment a video transcript into logical parts.
"""

from typing import Optional
from models import VideoSegmentation
from .create_segmentation_chain import create_segmentation_chain
from .format_transcript_snippets import format_transcript_snippets


def segment_video(video_id: str, transcript_snippets: list, api_key: Optional[str] = None) -> VideoSegmentation:
    """
    Segment a video transcript into logical parts.
    
    Args:
        video_id: YouTube video ID
        transcript_snippets: List of transcript snippets with .text, .start, .duration
        api_key: Optional Groq API key
    
    Returns:
        VideoSegmentation object with structured segments
    """
    # Create chain
    chain = create_segmentation_chain(api_key)
    
    # Format transcript
    formatted_transcript = format_transcript_snippets(transcript_snippets)
    
    # Run chain
    result = chain.invoke({
        "video_id": video_id,
        "transcript": formatted_transcript
    })
    
    return result
