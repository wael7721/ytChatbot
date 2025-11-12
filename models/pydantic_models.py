"""
Pydantic models for structured video analysis output.
"""

from pydantic import BaseModel, Field
from typing import List, Optional


class VideoSegment(BaseModel):
    """Represents a logical segment/section within a video."""
    
    title: str = Field(
        description="Clear, descriptive title for this segment (e.g., 'Introduction to Linear Regression')"
    )
    start_time: float = Field(
        description="Start timestamp in seconds"
    )
    end_time: float = Field(
        description="End timestamp in seconds"
    )
    summary: str = Field(
        description="Brief summary of what is covered in this segment (2-3 sentences)"
    )
    key_topics: List[str] = Field(
        description="List of main topics, concepts, or keywords discussed in this segment"
    )
    difficulty_level: Optional[str] = Field(
        default="medium",
        description="Estimated difficulty: 'easy', 'medium', or 'hard'"
    )


class VideoSegmentation(BaseModel):
    """Complete segmentation result for a video."""
    
    video_id: str = Field(
        description="YouTube video ID"
    )
    total_segments: int = Field(
        description="Total number of segments identified"
    )
    segments: List[VideoSegment] = Field(
        description="List of all video segments in chronological order"
    )
    overall_topic: Optional[str] = Field(
        default=None,
        description="Overall topic or theme of the entire video"
    )
