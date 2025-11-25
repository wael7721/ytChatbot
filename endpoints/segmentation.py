"""
Video segmentation API endpoints.
"""

from fastapi import APIRouter, HTTPException
from helpers.getTranscript import getTranscript
from helpers import extract_video_id
from agent import segment_video, segment_long_video

router = APIRouter(prefix="/segment", tags=["Segmentation"])


@router.get("")
def segment_video_endpoint(video_url: str):
    """
    Segment a YouTube video into logical parts using AI analysis.
    
    Accepts video URL or ID via query parameter:
    - Full URL: ?video_url=https://www.youtube.com/watch?v=VIDEO_ID
    - Short URL: ?video_url=https://youtu.be/VIDEO_ID
    - Just the video ID: ?video_url=VIDEO_ID
    
    Returns structured segments with:
    - video_id: YouTube video ID
    - total_segments: Number of segments identified
    - overall_topic: Main theme of the video
    - segments: List of segments, each containing:
      - title: Segment title
      - start_time: Start timestamp (seconds)
      - end_time: End timestamp (seconds)
      - summary: Brief description
      - key_topics: List of main concepts
      - difficulty_level: easy/medium/hard
    """
    video_id = extract_video_id(video_url)
    
    if not video_id:
        raise HTTPException(status_code=400, detail="Invalid YouTube URL or video ID")
    
    # Get transcript
    res = getTranscript(video_id)
    
    if not res:
        raise HTTPException(status_code=404, detail="No transcript available for this video")
    
    try:
        # Extract snippets
        snippets = res.snippets if hasattr(res, 'snippets') else res
        
        # Calculate video duration
        if snippets:
            video_duration = snippets[-1].start + snippets[-1].duration
        else:
            video_duration = 0
        
        # Use chunked processing for videos longer than 1 hour
        if video_duration > 3600:
            segmentation = segment_long_video(
                video_id=video_id,
                transcript_snippets=snippets,
                chunk_duration=3600,  # 1 hour chunks
                overlap_duration=300  # 5 minute overlap between chunks
            )
        else:
            # Use regular segmentation for shorter videos
            segmentation = segment_video(video_id, snippets)
        
        return segmentation.model_dump()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Segmentation failed: {str(e)}")
