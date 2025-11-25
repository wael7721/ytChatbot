"""
Agent module for LangChain-based video analysis and processing.
"""

from models import VideoSegment, VideoSegmentation

# Functional LCEL-style exports
from .video_segmenter import (
    create_segmentation_chain,
    segment_video,
    segment_long_video,
    format_transcript_snippets,
    format_timestamp,
    create_streaming_segmentation_chain,
    prepare_segmentation_input
)

__all__ = [
    "VideoSegment", 
    "VideoSegmentation",
    "VideoSegmenter",
    "create_segmentation_chain",
    "segment_video",
    "segment_long_video",
    "format_transcript_snippets",
    "format_timestamp",
    "create_streaming_segmentation_chain",
    "prepare_segmentation_input"
]
