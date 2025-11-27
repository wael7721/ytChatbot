"""
Transcript-related API endpoints.
"""

from fastapi import APIRouter, HTTPException
from helpers.getTranscript import getTranscript
from helpers import format_duration, extract_video_id
from models import get_db
import requests

router = APIRouter(prefix="/transcript", tags=["Transcript"])


def get_video_title(video_id: str) -> str:
    """
    Fetch video title from YouTube using oembed API.
    
    Args:
        video_id: YouTube video ID
    
    Returns:
        Video title or None if unable to fetch
    """
    try:
        url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            return data.get("title")
    except Exception as e:
        print(f"⚠️  Could not fetch title for {video_id}: {e}")
    return None


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
        
        # If title is missing, fetch and update it
        if not cached_video.get("title"):
            print(f"⚠️  Title missing for {video_id}, fetching...")
            video_title = get_video_title(video_id)
            if video_title:
                print(f"📺 Fetched title: {video_title}")
                # Update the video with the title
                snippets = [
                    type('Snippet', (), {
                        'text': s['text'],
                        'start': s['start'],
                        'duration': s['duration']
                    })()
                    for s in cached_video["transcript"]
                ]
                db.save_video(video_id, snippets, title=video_title)
                cached_video["title"] = video_title
        
        # Reconstruct full text from cached transcript
        full_text = ' '.join(snippet["text"] for snippet in cached_video["transcript"])
        video_length = format_duration(cached_video["duration_seconds"])
        
        return {
            "video_id": video_id,
            "transcript": full_text,
            "video_length": video_length,
            "snippet_count": cached_video["snippet_count"],
            "title": cached_video.get("title")
        }
    
    # Fetch fresh transcript
    res = getTranscript(video_id)
    
    if not res:
        raise HTTPException(status_code=404, detail="No transcript available for this video")
    
    # Extract snippets
    snippets = res.snippets if hasattr(res, 'snippets') else res
    
    # Fetch video title
    video_title = get_video_title(video_id)
    if video_title:
        print(f"📺 Fetched title: {video_title}")
    
    # Save to database with title
    db.save_video(video_id, snippets, title=video_title)
    print(f"💾 Saved transcript for {video_id}")
    
    video_length_seconds = snippets[-1].start + snippets[-1].duration if snippets else 0
    video_length = format_duration(video_length_seconds)
    
    # Extract full text
    full_text = ' '.join(s.text for s in snippets)
    
    return {
        "video_id": video_id,
        "transcript": full_text,
        "video_length": video_length,
        "snippet_count": len(snippets),
        "title": video_title
    }
