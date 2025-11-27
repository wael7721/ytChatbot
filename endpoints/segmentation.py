"""
Video segmentation API endpoints.
"""

from fastapi import APIRouter, HTTPException
from helpers.getTranscript import getTranscript
from helpers import extract_video_id
from agent import segment_video, segment_long_video
from models import get_db

router = APIRouter(prefix="/segment", tags=["Segmentation"])


@router.get("")
def segment_video_endpoint(video_url: str, force: bool = False):
    """
    Segment a YouTube video into logical parts using AI analysis.
    
    Accepts video URL or ID via query parameter:
    - Full URL: ?video_url=https://www.youtube.com/watch?v=VIDEO_ID
    - Short URL: ?video_url=https://youtu.be/VIDEO_ID
    - Just the video ID: ?video_url=VIDEO_ID
    
    Query parameters:
    - force: Set to true to force reprocessing even if cached (default: false)
    
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
    
    # Get database instance
    db = get_db()
    
    # Check if segmentation already exists in database (unless force=true)
    if not force:
        cached_segmentation = db.get_segmentation(video_id)
        if cached_segmentation:
            # Only use cache if segmentation is complete
            if cached_segmentation["processing_status"] == "complete":
                print(f"✅ Using cached complete segmentation for {video_id}")
                return cached_segmentation["segmentation"]
            else:
                # Partial segmentation - warn and reprocess
                chunks_done = cached_segmentation.get("chunks_processed", 0)
                total = cached_segmentation.get("total_chunks", 0)
                print(f"⚠️  Found partial segmentation ({chunks_done}/{total} chunks). Re-processing entire video...")
    else:
        print(f"🔄 Force reprocessing {video_id}")
    
    # Get transcript
    res = getTranscript(video_id)
    
    if not res:
        raise HTTPException(status_code=404, detail="No transcript available for this video")
    
    try:
        # Extract snippets
        snippets = res.snippets if hasattr(res, 'snippets') else res
        
        # Save video data to database
        db.save_video(video_id, snippets)
        print(f"💾 Saved video transcript for {video_id}")
        
        # Calculate video duration
        if snippets:
            video_duration = snippets[-1].start + snippets[-1].duration
        else:
            video_duration = 0
        
        # Use chunked processing for videos longer than 1 hour
        chunks_processed = None
        total_chunks = None
        
        if video_duration > 3600:
            total_chunks = int((video_duration - 300) / (3600 - 300)) + 1
            segmentation = segment_long_video(
                video_id=video_id,
                transcript_snippets=snippets,
                chunk_duration=3600,  # 1 hour chunks
                overlap_duration=300  # 5 minute overlap between chunks
            )
            # Check if partial result (rate limit hit)
            if "[Partial:" in segmentation.overall_topic:
                # Extract chunks_processed from overall_topic
                import re
                match = re.search(r'\[Partial: (\d+)/(\d+)', segmentation.overall_topic)
                if match:
                    chunks_processed = int(match.group(1))
                    total_chunks = int(match.group(2))
                print(f"⚠️  Partial result: {chunks_processed}/{total_chunks} chunks processed due to rate limit")
        else:
            # Use regular segmentation for shorter videos
            segmentation = segment_video(video_id, snippets)
        
        # Save segmentation to database
        segmentation_id = db.save_segmentation(
            video_id=video_id,
            segmentation_result=segmentation,
            chunks_processed=chunks_processed,
            total_chunks=total_chunks
        )
        
        status = "partial" if chunks_processed and chunks_processed < total_chunks else "complete"
        print(f"💾 Saved {status} segmentation for {video_id} (ID: {segmentation_id})")
        
        return segmentation.model_dump()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Segmentation failed: {str(e)}")


@router.get("/search")
def search_segments(video_url: str, query: str):
    """
    Search for segments by keyword in a specific video.
    
    Args:
        video_url: YouTube video URL or ID
        query: Search query (searches title, summary, and topics)
    
    Returns:
        List of matching segments
    """
    video_id = extract_video_id(video_url)
    
    if not video_id:
        raise HTTPException(status_code=400, detail="Invalid YouTube URL or video ID")
    
    db = get_db()
    segments = db.search_segments(video_id, query)
    
    if not segments:
        raise HTTPException(status_code=404, detail=f"No segments found matching '{query}'")
    
    return {
        "video_id": video_id,
        "query": query,
        "results": segments,
        "count": len(segments)
    }


@router.get("/time-range")
def get_segments_by_time(video_url: str, start_time: float, end_time: float):
    """
    Get segments within a specific time range.
    
    Args:
        video_url: YouTube video URL or ID
        start_time: Start time in seconds
        end_time: End time in seconds
    
    Returns:
        List of segments overlapping with the time range
    """
    video_id = extract_video_id(video_url)
    
    if not video_id:
        raise HTTPException(status_code=400, detail="Invalid YouTube URL or video ID")
    
    if start_time < 0 or end_time < 0 or start_time >= end_time:
        raise HTTPException(status_code=400, detail="Invalid time range")
    
    db = get_db()
    segments = db.get_segments_by_time(video_id, start_time, end_time)
    
    if not segments:
        raise HTTPException(status_code=404, detail="No segments found in time range")
    
    return {
        "video_id": video_id,
        "start_time": start_time,
        "end_time": end_time,
        "segments": segments,
        "count": len(segments)
    }


@router.get("/status")
def get_segmentation_status(video_url: str):
    """
    Check the processing status of a video's segmentation.
    
    Args:
        video_url: YouTube video URL or ID
    
    Returns:
        Status information including whether segmentation is complete or partial
    """
    video_id = extract_video_id(video_url)
    
    if not video_id:
        raise HTTPException(status_code=400, detail="Invalid YouTube URL or video ID")
    
    db = get_db()
    segmentation = db.get_segmentation(video_id)
    
    if not segmentation:
        raise HTTPException(status_code=404, detail="No segmentation found for this video")
    
    status_info = {
        "video_id": video_id,
        "status": segmentation["processing_status"],
        "total_segments": segmentation["total_segments"],
        "created_at": segmentation["created_at"]
    }
    
    # Add chunk info if partial
    if segmentation["processing_status"] == "partial":
        status_info["chunks_processed"] = segmentation["chunks_processed"]
        status_info["total_chunks"] = segmentation["total_chunks"]
        status_info["completion_percentage"] = round(
            (segmentation["chunks_processed"] / segmentation["total_chunks"]) * 100, 1
        )
        status_info["message"] = f"Only {segmentation['chunks_processed']}/{segmentation['total_chunks']} chunks processed. Use ?force=true to retry full segmentation."
    else:
        status_info["message"] = "Segmentation complete"
    
    return status_info

