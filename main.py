from fastapi import FastAPI, HTTPException
import time
import datetime
import uvicorn
from getTranscript import getTranscript
from helpers import format_duration, extract_video_id
from agent import VideoSegmenter

app = FastAPI(title="ytChatbot API", version="0.1.0")
_start_time = time.time()

# Initialize video segmenter (lazy initialization to avoid errors if API key missing)
_segmenter = None

def get_segmenter():
    global _segmenter
    if _segmenter is None:
        _segmenter = VideoSegmenter()
    return _segmenter

@app.get("/health")
def health():
    """
    Simple health endpoint returning status, uptime (seconds) and current UTC timestamp.
    """
    uptime = time.time() - _start_time
    return {
        "status": "ok",
        "uptime_seconds": round(uptime, 2),
        "timestamp_utc": datetime.datetime.utcnow().isoformat() + "Z"
    }
@app.get("/transcript")
def transcript(video_url: str):
    """
    Endpoint to fetch transcript from a YouTube URL or video ID.
    Accepts various formats via query parameter:
    - Full URL: ?video_url=https://www.youtube.com/watch?v=VIDEO_ID
    - Short URL: ?video_url=https://youtu.be/VIDEO_ID
    - Just the video ID: ?video_url=VIDEO_ID
    """
    video_id = extract_video_id(video_url)
    
    if not video_id:
        return {"error": "Invalid YouTube URL or video ID"}
    
    res = getTranscript(video_id)
    
    if not res:
        return {"message": "No transcript available for this video."}
    
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


@app.get("/segment")
def segment_video(video_url: str):
    """
    Segment a YouTube video into logical parts using AI analysis.
    
    Accepts video URL or ID via query parameter:
    - Full URL: ?video_url=https://www.youtube.com/watch?v=VIDEO_ID
    - Short URL: ?video_url=https://youtu.be/VIDEO_ID
    - Just the video ID: ?video_url=VIDEO_ID
    
    Returns structured segments with:
    - Title, start/end times, summary
    - Key topics and difficulty level
    - Overall video topic
    """
    video_id = extract_video_id(video_url)
    
    if not video_id:
        raise HTTPException(status_code=400, detail="Invalid YouTube URL or video ID")
    
    # Get transcript
    res = getTranscript(video_id)
    
    if not res:
        raise HTTPException(status_code=404, detail="No transcript available for this video")
    
    try:
        # Get segmenter and analyze
        segmenter = get_segmenter()
        
        # Segment using transcript snippets
        segmentation = segmenter.segment(video_id, res.snippets if hasattr(res, 'snippets') else res)
        
        return segmentation.model_dump()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Segmentation failed: {str(e)}")


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
