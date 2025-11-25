"""
Video segmentation using LangChain LCEL and functional composition.
"""

import os
from typing import Optional
from langchain_groq import ChatGroq
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate
from models import VideoSegmentation


def create_segmentation_chain(api_key: Optional[str] = None, model: str = "llama-3.3-70b-versatile"):
    """
    Create an LCEL chain for video segmentation.
    
    Args:
        api_key: Groq API key (defaults to GROQ_API_KEY env variable)
        model: LLM model to use
    
    Returns:
        Runnable chain that takes {video_id, transcript} and returns VideoSegmentation
    """
    api_key = api_key or os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY not found in environment or provided")
    
    # Initialize LLM
    llm = ChatGroq(
        model=model,
        temperature=0.1,
        api_key=api_key
    )
    
    # Set up output parser
    parser = PydanticOutputParser(pydantic_object=VideoSegmentation)
    
    # Create prompt
    prompt = PromptTemplate(
        template="""You are an expert at analyzing educational video transcripts and identifying logical topic segments.

Given a video transcript with timestamps in [MM:SS] or [HH:MM:SS] format, identify distinct segments where the topic or concept changes.
Each segment should represent a coherent section of the video covering a specific subtopic.

VIDEO ID: {video_id}
TRANSCRIPT (timestamps shown as [MM:SS] or [HH:MM:SS]):
{transcript}

INSTRUCTIONS:
1. Identify all logical segments (topics/sections) in the video
2. Each segment should have clear start/end times based on topic transitions
3. **IMPORTANT**: Return start_time and end_time in SECONDS (not minutes or hours). 
   Examples: [02:30] = 150 seconds, [01:30:45] = 5445 seconds
4. Provide a clear title for each segment
5. Write a brief 2-3 sentence summary
6. List the entire key topics/concepts covered
7. Estimate difficulty level (easy/medium/hard)
8. Determine the overall topic/theme of the entire video

{format_instructions}

Provide your analysis:""",
        input_variables=["video_id", "transcript"],
        partial_variables={"format_instructions": parser.get_format_instructions()}
    )
    
    # LCEL chain composition
    chain = (
        prompt 
        | llm 
        | parser
    )
    
    return chain


def format_transcript_snippets(snippets: list, max_chars: int = 15000, start_time: float = 0, end_time: float = None) -> str:
    """
    Format transcript snippets into timestamped text.
    
    Args:
        snippets: List of transcript snippets with .text, .start, .duration
        max_chars: Maximum characters to include
        start_time: Only include snippets starting after this time (in seconds)
        end_time: Only include snippets starting before this time (in seconds)
    
    Returns:
        Formatted transcript string
    """
    lines = []
    total_chars = 0
    
    for snippet in snippets:
        # Filter by time range if specified
        if snippet.start < start_time:
            continue
        if end_time is not None and snippet.start >= end_time:
            break
            
        timestamp = format_timestamp(snippet.start)
        line = f"[{timestamp}] {snippet.text}"
        
        if total_chars + len(line) > max_chars:
            lines.append("... [transcript truncated for length] ...")
            break
        
        lines.append(line)
        total_chars += len(line) + 1
    
    return "\n".join(lines)


def format_timestamp(seconds: float) -> str:
    """Convert seconds to HH:MM:SS or MM:SS format."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes:02d}:{secs:02d}"


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
    merged_segments = _merge_similar_segments(all_segments)
    
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


def _merge_similar_segments(segments: list, similarity_threshold: int = 300) -> list:
    """
    Merge adjacent segments that might be duplicates, overlaps, or continuations.
    
    HANDLES MULTI-HOUR SEGMENTS:
    When a single topic segment exceeds 1 hour (e.g., "Deep Dive into Transformers" 
    from 0:30 - 2:15), it gets split across multiple chunks:
    - Chunk 1: Creates segment 0:30 - 1:00
    - Chunk 2: Creates segment 1:00 - 1:55 (continuation)
    - Chunk 3: Creates segment 1:55 - 2:15 (continuation)
    
    This function merges them back into one segment by detecting:
    1. Time adjacency (segments within 5 minutes of each other)
    2. Topic similarity (>50% Jaccard similarity on key_topics)
    3. Explicit continuation markers ("continued", "part 2", etc.)
    
    Args:
        segments: List of VideoSegment objects
        similarity_threshold: Max time gap (seconds) between segments to consider merging
    
    Returns:
        List of merged segments with continuations combined
    """
    if not segments or len(segments) < 2:
        return segments
    
    # Sort by start time
    sorted_segments = sorted(segments, key=lambda s: s.start_time)
    merged = []
    current = sorted_segments[0]
    
    for next_seg in sorted_segments[1:]:
        # Calculate time gap between segments
        time_gap = next_seg.start_time - current.end_time
        
        # Case 1: Overlapping segments (next starts before current ends)
        if time_gap < 0:
            # Keep the segment with more detailed information
            if len(next_seg.summary) + len(next_seg.key_topics) > len(current.summary) + len(current.key_topics):
                current = next_seg
            # Skip adding the less detailed one
            continue
        
        # Case 2: Adjacent segments - likely a continuation of a long segment
        is_adjacent = time_gap <= similarity_threshold  # Within 5 minutes
        is_similar = _are_topics_similar(current, next_seg, threshold=0.5)
        
        # Check for explicit continuation markers in title
        has_continuation_marker = any(
            marker in next_seg.title.lower() 
            for marker in ['continued', 'continuation', 'part 2', 'part two', 'part 3', '(cont', '- cont']
        )
        
        # Merge if adjacent + similar, OR has explicit continuation marker
        if (is_adjacent and is_similar) or has_continuation_marker:
            # Merge: This is likely a single long segment split across chunks
            from models import VideoSegment
            current = VideoSegment(
                title=current.title,  # Keep original title
                summary=f"{current.summary} {next_seg.summary}".strip(),
                start_time=current.start_time,
                end_time=next_seg.end_time,  # Extend to next segment's end
                key_topics=list(set(current.key_topics + next_seg.key_topics)),  # Combine unique topics
                difficulty=current.difficulty  # Keep original difficulty
            )
            continue
        
        # Case 3: Distinct segments - keep both
        merged.append(current)
        current = next_seg
    
    # Add the last segment
    merged.append(current)
    
    return merged


def _are_topics_similar(seg1, seg2, threshold: float = 0.3) -> bool:
    """
    Check if two segments have similar topics using Jaccard similarity.
    
    Higher threshold = stricter matching (use 0.5 for continuations of same topic)
    Lower threshold = looser matching (use 0.3 for related topics)
    
    Args:
        seg1, seg2: VideoSegment objects
        threshold: Minimum Jaccard similarity (0.0 - 1.0) to consider similar
    
    Returns:
        True if topics overlap >= threshold
    """
    topics1 = set(topic.lower() for topic in seg1.key_topics)
    topics2 = set(topic.lower() for topic in seg2.key_topics)
    
    if not topics1 or not topics2:
        return False
    
    # Calculate Jaccard similarity: |A ∩ B| / |A ∪ B|
    intersection = len(topics1 & topics2)
    union = len(topics1 | topics2)
    
    similarity = intersection / union if union > 0 else 0
    
    return similarity >= threshold


def create_streaming_segmentation_chain(api_key: Optional[str] = None):
    """
    Create an LCEL chain that supports streaming output.
    Useful for real-time UI updates.
    
    Args:
        api_key: Groq API key
    
    Returns:
        Streaming-enabled LCEL chain
    """
    api_key = api_key or os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY not found")
    
    llm = ChatGroq(
        model="llama-3.3-70b-versatile",
        temperature=0.1,
        api_key=api_key,
        streaming=True  # Enable streaming
    )
    
    parser = PydanticOutputParser(pydantic_object=VideoSegmentation)
    
    prompt = PromptTemplate(
        template="""You are an expert at analyzing educational video transcripts and identifying logical topic segments.

VIDEO ID: {video_id}
TRANSCRIPT: {transcript}

Identify all "video_length": "21 hours 31 minutes 28 seconds",
  "snippet_count": 31348 logical segments. Return start_time and end_time in SECONDS.

{format_instructions}

Analysis:""",
        input_variables=["video_id", "transcript"],
        partial_variables={"format_instructions": parser.get_format_instructions()}
    )
    
    chain = prompt | llm | parser
    
    return chain


def prepare_segmentation_input(video_id: str, snippets: list) -> dict:
    """
    Prepare input dict for segmentation chain.
    Can be used in LCEL composition.
    
    Args:
        video_id: YouTube video ID
        snippets: Transcript snippets
    
    Returns:
        Dict ready for chain.invoke()
    """
    return {
        "video_id": video_id,
        "transcript": format_transcript_snippets(snippets)
    }

