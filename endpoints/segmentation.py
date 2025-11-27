"""
Video segmentation API endpoints.
"""

from fastapi import APIRouter, HTTPException
from helpers.getTranscript import getTranscript
from helpers import extract_video_id
from agent import segment_video, segment_long_video
from models import get_db
import requests

router = APIRouter(prefix="/segment", tags=["Segmentation"])


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
            # Verify segmentation actually covers the full video
            is_complete = _verify_segmentation_coverage(cached_segmentation, video_id, db)
            
            if is_complete:
                print(f"✅ Using cached complete segmentation for {video_id}")
                return cached_segmentation["segmentation"]
            else:
                # Incomplete coverage - reprocess
                print(f"⚠️  Cached segmentation incomplete. Re-processing entire video...")
    else:
        print(f"🔄 Force reprocessing {video_id}")
        print(f"🔄 Force reprocessing {video_id}")
    
    # Get transcript
    res = getTranscript(video_id)
    
    if not res:
        raise HTTPException(status_code=404, detail="No transcript available for this video")
    
    try:
        # Extract snippets
        snippets = res.snippets if hasattr(res, 'snippets') else res
        
        # Fetch video title
        video_title = get_video_title(video_id)
        if video_title:
            print(f"📺 Fetched title: {video_title}")
        
        # Save video data to database with title
        db.save_video(video_id, snippets, title=video_title)
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


def _verify_segmentation_coverage(cached_segmentation: dict, video_id: str, db) -> bool:
    """
    Verify that cached segmentation covers the full video duration.
    
    Compares the last segment's end_time with actual video duration.
    
    Args:
        cached_segmentation: Cached segmentation data from database
        video_id: YouTube video ID
        db: Database instance
    
    Returns:
        True if segments cover at least 95% of video, False otherwise
    """
    # Get video data to determine actual duration
    video_data = db.get_video(video_id)
    if not video_data:
        print(f"  ❌ No video data found in database")
        return False
    
    # Calculate actual video duration from transcript
    transcript = video_data.get("transcript", [])
    if not transcript or len(transcript) == 0:
        print(f"  ❌ No transcript data")
        return False
    
    last_snippet = transcript[-1]
    if isinstance(last_snippet, dict):
        actual_duration = last_snippet.get("start", 0) + last_snippet.get("duration", 0)
    else:
        actual_duration = last_snippet.start + last_snippet.duration
    
    # Get segments from cached segmentation
    segments = cached_segmentation["segmentation"].get("segments", [])
    if not segments or len(segments) == 0:
        print(f"  ❌ No segments found")
        return False
    
    # Find the last segment by end_time
    last_segment_end = max(seg["end_time"] for seg in segments)
    
    # Calculate coverage percentage
    coverage_percentage = (last_segment_end / actual_duration) * 100 if actual_duration > 0 else 0
    time_missing = actual_duration - last_segment_end
    
    print(f"  📊 Video duration: {actual_duration:.0f}s | Last segment ends: {last_segment_end:.0f}s | Coverage: {coverage_percentage:.1f}%")
    
    # Consider complete if segments cover at least 95% of video
    # (allows for slight variations in processing)
    is_complete = coverage_percentage >= 95.0
    
    if not is_complete:
        print(f"  ❌ Incomplete: missing last {time_missing:.0f}s ({100-coverage_percentage:.1f}% uncovered)")
    
    return is_complete


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
        Status information including coverage percentage and completeness
    """
    video_id = extract_video_id(video_url)
    
    if not video_id:
        raise HTTPException(status_code=400, detail="Invalid YouTube URL or video ID")
    
    db = get_db()
    segmentation = db.get_segmentation(video_id)
    
    if not segmentation:
        raise HTTPException(status_code=404, detail="No segmentation found for this video")
    
    # Get video data for coverage calculation
    video_data = db.get_video(video_id)
    actual_duration = 0
    last_segment_end = 0
    coverage_percentage = 0
    
    if video_data:
        transcript = video_data.get("transcript", [])
        if transcript and len(transcript) > 0:
            last_snippet = transcript[-1]
            if isinstance(last_snippet, dict):
                actual_duration = last_snippet.get("start", 0) + last_snippet.get("duration", 0)
            else:
                actual_duration = last_snippet.start + last_snippet.duration
        
        # Get last segment end time
        segments = segmentation["segmentation"].get("segments", [])
        if segments and len(segments) > 0:
            last_segment_end = max(seg["end_time"] for seg in segments)
            coverage_percentage = (last_segment_end / actual_duration) * 100 if actual_duration > 0 else 0
    
    status_info = {
        "video_id": video_id,
        "status": segmentation["processing_status"],
        "total_segments": segmentation["total_segments"],
        "created_at": segmentation["created_at"],
        "video_duration_seconds": round(actual_duration, 1),
        "last_segment_ends_at": round(last_segment_end, 1),
        "coverage_percentage": round(coverage_percentage, 1),
        "is_actually_complete": coverage_percentage >= 95.0
    }
    
    # Add chunk info if partial
    if segmentation["processing_status"] == "partial":
        status_info["chunks_processed"] = segmentation["chunks_processed"]
        status_info["total_chunks"] = segmentation["total_chunks"]
        status_info["message"] = f"Partial: {segmentation['chunks_processed']}/{segmentation['total_chunks']} chunks processed. Use ?force=true to retry."
    else:
        # Check if actually complete based on coverage
        if coverage_percentage >= 95.0:
            status_info["message"] = f"Complete: {coverage_percentage:.1f}% of video covered"
        else:
            time_missing = actual_duration - last_segment_end
            status_info["message"] = f"Marked complete but missing {time_missing:.0f}s. Use ?force=true to reprocess."
    
    return status_info

