"""
Merge adjacent segments that might be duplicates, overlaps, or continuations.
"""

from models import VideoSegment
from .are_topics_similar import are_topics_similar


def merge_similar_segments(segments: list, similarity_threshold: int = 300) -> list:
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
        is_similar = are_topics_similar(current, next_seg, threshold=0.5)
        
        # Check for explicit continuation markers in title
        has_continuation_marker = any(
            marker in next_seg.title.lower() 
            for marker in ['continued', 'continuation', 'part 2', 'part two', 'part 3', '(cont', '- cont']
        )
        
        # Merge if adjacent + similar, OR has explicit continuation marker
        if (is_adjacent and is_similar) or has_continuation_marker:
            # Merge: This is likely a single long segment split across chunks
            current = VideoSegment(
                title=current.title,  # Keep original title
                summary=f"{current.summary} {next_seg.summary}".strip(),
                start_time=current.start_time,
                end_time=next_seg.end_time,  # Extend to next segment's end
                key_topics=list(set(current.key_topics + next_seg.key_topics)),  # Combine unique topics
                difficulty_level=current.difficulty_level  # Keep original difficulty
            )
            continue
        
        # Case 3: Distinct segments - keep both
        merged.append(current)
        current = next_seg
    
    # Add the last segment
    merged.append(current)
    
    return merged
