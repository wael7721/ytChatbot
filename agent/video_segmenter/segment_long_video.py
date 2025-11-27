"""
Segment long videos by processing them in chunks with overlap.
"""

from typing import Optional
from models import VideoSegmentation
from .segment_video import segment_video
from .format_transcript_snippets import format_transcript_snippets
from .format_timestamp import format_timestamp
from .create_segmentation_chain import create_segmentation_chain
from .merge_similar_segments import merge_similar_segments


def segment_long_video(
    video_id: str, 
    transcript_snippets: list, 
    api_key: Optional[str] = None,
    chunk_duration: int = 3600,
    overlap_duration: int = 300
) -> VideoSegmentation:
    """
    Segment a long video by processing it in chunks with overlap.
    
    For videos longer than chunk_duration, this splits the video into overlapping chunks,
    processes each chunk separately, then merges the results while handling duplicates.
    
    KEY SEGMENT HANDLING:
    - If a single topic segment exceeds 1 hour, it will be split across chunks
    - The merge function detects continuations via:
      1. Time adjacency (<5 min gap)
      2. Topic similarity (>50% overlap)
      3. Explicit continuation markers in titles
    - Example: "Transformers Deep Dive" (0:30 - 2:15) split into 3 chunks
      will be merged back into one continuous segment
    
    RATE LIMIT HANDLING:
    - If rate limit is hit mid-processing, returns partial results
    - Includes metadata about which chunks were processed
    
    Args:
        video_id: YouTube video ID
        transcript_snippets: List of transcript snippets with .text, .start, .duration
        api_key: Optional Groq API key
        chunk_duration: Duration of each chunk in seconds (default: 3600 = 1 hour)
        overlap_duration: Overlap between chunks in seconds (default: 300 = 5 minutes)
    
    Returns:
        VideoSegmentation object with all segments merged
    """
    # Calculate total duration
    if not transcript_snippets:
        raise ValueError("No transcript snippets provided")
    
    total_duration = transcript_snippets[-1].start + transcript_snippets[-1].duration
    
    # If video is short enough, use regular segmentation
    if total_duration <= chunk_duration:
        return segment_video(video_id, transcript_snippets, api_key)
    
    # Process in chunks with overlap
    all_segments = []
    chunk_start = 0
    chunk_number = 1
    total_chunks = int((total_duration - overlap_duration) / (chunk_duration - overlap_duration)) + 1
    last_processed_chunk = 0
    overall_topic = "Long video content"
    
    while chunk_start < total_duration:
        # Define chunk boundaries
        chunk_end = min(chunk_start + chunk_duration, total_duration)
        
        print(f"Processing chunk {chunk_number}/{total_chunks}: {format_timestamp(chunk_start)} - {format_timestamp(chunk_end)}")
        
        try:
            # Format transcript for this chunk
            chunk_transcript = format_transcript_snippets(
                transcript_snippets,
                max_chars=15000,
                start_time=chunk_start,
                end_time=chunk_end
            )
            
            # Create chain and process chunk
            chain = create_segmentation_chain(api_key)
            chunk_result = chain.invoke({
                "video_id": f"{video_id} (part {chunk_number})",
                "transcript": chunk_transcript
            })
            
            # Store overall topic from first successful chunk
            if chunk_number == 1:
                overall_topic = chunk_result.overall_topic
            
            # Add segments from this chunk
            for segment in chunk_result.segments:
                # Only include segments that start within the non-overlap portion
                # This prevents duplicates from overlapping regions
                if chunk_number == 1:
                    # First chunk: include all segments
                    all_segments.append(segment)
                else:
                    # Subsequent chunks: only include segments starting after overlap
                    overlap_boundary = chunk_start + overlap_duration
                    if segment.start_time >= overlap_boundary:
                        all_segments.append(segment)
            
            last_processed_chunk = chunk_number
            
        except Exception as e:
            error_msg = str(e).lower()
            # Check if it's a rate limit error
            if 'rate' in error_msg or 'limit' in error_msg or '429' in error_msg:
                print(f"⚠️  Rate limit hit at chunk {chunk_number}. Returning partial results for {last_processed_chunk} chunks.")
                break
            else:
                # For other errors, re-raise
                raise
        
        # Move to next chunk (subtract overlap to create continuity)
        chunk_start = chunk_end - overlap_duration
        chunk_number += 1
        
        # Break if we've reached the end
        if chunk_end >= total_duration:
            break
    
    # Merge adjacent segments with similar topics
    # This handles segments that span multiple chunks (>1 hour segments)
    merged_segments = merge_similar_segments(all_segments)
    
    # Add processing metadata to overall topic if partial
    if last_processed_chunk < total_chunks:
        processed_duration = format_timestamp(all_segments[-1].end_time if all_segments else 0)
        overall_topic = f"{overall_topic} [Partial: {last_processed_chunk}/{total_chunks} chunks processed up to {processed_duration}]"
    
    return VideoSegmentation(
        video_id=video_id,
        segments=merged_segments,
        total_segments=len(merged_segments),
        overall_topic=overall_topic
    )
