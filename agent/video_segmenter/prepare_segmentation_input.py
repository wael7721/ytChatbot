"""
Prepare input dictionary for segmentation chain.
"""

from .format_transcript_snippets import format_transcript_snippets


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
