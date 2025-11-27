"""
Check if two segments have similar topics using Jaccard similarity.
"""


def are_topics_similar(seg1, seg2, threshold: float = 0.3) -> bool:
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
