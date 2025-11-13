"""
Transcript-related API endpoints.
"""

from fastapi import APIRouter, HTTPException
from helpers.getTranscript import getTranscript
from helpers import format_duration, extract_video_id

router = APIRouter(prefix="/transcript", tags=["Transcript"])


@router.get("")
def get_transcript(video_url: str):
    """
    Fetch transcript from a YouTube URL or video ID.
    
    Accepts various formats via query parameter:
    - Full URL: ?video_url=https://www.youtube.com/watch?v=VIDEO_ID
    - Short URL: ?video_url=https://youtu.be/VIDEO_ID
    - Just the video ID: ?video_url=VIDEO_ID
    
    Returns:
    - video_id: YouTube video ID
    - transcript: Full transcript text
    - video_length: Human-readable duration
    - snippet_count: Number of transcript segments
    """
    video_id = extract_video_id(video_url)
    
    if not video_id:
        raise HTTPException(status_code=400, detail="Invalid YouTube URL or video ID")
    
    res = getTranscript(video_id)
    
    if not res:
        raise HTTPException(status_code=404, detail="No transcript available for this video")
    
    video_length_seconds = res.snippets[-1].start + res.snippets[-1].duration if res.snippets else 0
    video_length = format_duration(video_length_seconds)
    
    # Extract full text
    full_text = ' '.join(s.text for s in res.snippets) if hasattr(res, 'snippets') else ' '.join(item.text for item in res)
    
    return {
        "video_id": video_id,
        "transcript": full_text,
        "video_length": video_length,
        "snippet_count": len(res.snippets) if hasattr(res, 'snippets') else len(res)
    }
