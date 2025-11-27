"""
Format transcript snippets into timestamped text.
"""

from .format_timestamp import format_timestamp


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
