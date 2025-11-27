"""
Transcript-related API endpoints.
"""

from fastapi import APIRouter, HTTPException
from helpers.getTranscript import getTranscript
from helpers import format_duration, extract_video_id
from models import get_db

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
    
    # Get database instance
    db = get_db()
    
    # Check if transcript already exists in database
    cached_video = db.get_video(video_id)
    if cached_video:
        print(f"✅ Using cached transcript for {video_id}")
        # Reconstruct full text from cached transcript
        full_text = ' '.join(snippet["text"] for snippet in cached_video["transcript"])
        video_length = format_duration(cached_video["duration_seconds"])
        
        return {
            "video_id": video_id,
            "transcript": full_text,
            "video_length": video_length,
            "snippet_count": cached_video["snippet_count"]
        }
    
    # Fetch fresh transcript
    res = getTranscript(video_id)
    
    if not res:
        raise HTTPException(status_code=404, detail="No transcript available for this video")
    
    # Extract snippets
    snippets = res.snippets if hasattr(res, 'snippets') else res
    
    # Save to database
    db.save_video(video_id, snippets)
    print(f"💾 Saved transcript for {video_id}")
    
    video_length_seconds = snippets[-1].start + snippets[-1].duration if snippets else 0
    video_length = format_duration(video_length_seconds)
    
    # Extract full text
    full_text = ' '.join(s.text for s in snippets)
    
    return {
        "video_id": video_id,
        "transcript": full_text,
        "video_length": video_length,
        "snippet_count": len(snippets)
    }
