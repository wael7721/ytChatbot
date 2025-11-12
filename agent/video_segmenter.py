"""
Video segmentation using LangChain and LLM with structured output parsing.
"""

import os
from typing import List, Optional
from langchain_groq import ChatGroq
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate
from models import VideoSegment, VideoSegmentation



class VideoSegmenter:
    """
    Segments video transcripts into logical parts using LLM analysis.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the video segmenter with Groq LLM.
        
        Args:
            api_key: Groq API key (defaults to GROQ_API_KEY env variable)
        """
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY not found in environment or provided")
        
        # Initialize LLM with Groq
        self.llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            temperature=0.1,  # Low temperature for consistent segmentation
            api_key=self.api_key
        )
        
        # Set up Pydantic output parser
        self.parser = PydanticOutputParser(pydantic_object=VideoSegmentation)
        
        # Create prompt template
        self.prompt = PromptTemplate(
            template="""You are an expert at analyzing educational video transcripts and identifying logical topic segments.

Given a video transcript with timestamps in [MM:SS] or [HH:MM:SS] format, identify distinct segments where the topic or concept changes.
Each segment should represent a coherent section of the video covering a specific subtopic.

VIDEO ID: {video_id}
TRANSCRIPT (timestamps shown as [MM:SS] or [HH:MM:SS]):
{transcript}

INSTRUCTIONS:
1. Identify 3-8 logical segments (topics/sections) in the video
2. Each segment should have clear start/end times based on topic transitions
3. **IMPORTANT**: Return start_time and end_time in SECONDS (not minutes or hours). 
   Examples: [02:30] = 150 seconds, [01:30:45] = 5445 seconds
4. Provide a clear title for each segment
5. Write a brief 2-3 sentence summary
6. List 3-5 key topics/concepts covered
7. Estimate difficulty level (easy/medium/hard)
8. Determine the overall topic/theme of the entire video

{format_instructions}

Provide your analysis:""",
            input_variables=["video_id", "transcript"],
            partial_variables={"format_instructions": self.parser.get_format_instructions()}
        )
        
        # Create the chain
        self.chain = self.prompt | self.llm | self.parser
    
    def segment(self, video_id: str, transcript_data: list) -> VideoSegmentation:
        """
        Segment a video transcript into logical parts.
        
        Args:
            video_id: YouTube video ID
            transcript_data: List of transcript snippets with .text, .start, .duration
        
        Returns:
            VideoSegmentation object with structured segments
        """
        # Format transcript with timestamps for LLM
        formatted_transcript = self._format_transcript(transcript_data)
        
        # Run the chain
        result = self.chain.invoke({
            "video_id": video_id,
            "transcript": formatted_transcript
        })
        
        return result
    
    def _format_transcript(self, transcript_data: list, max_chars: int = 15000) -> str:
        """
        Format transcript data into a readable format with timestamps.
        Truncate if too long to avoid token limits.
        
        Args:
            transcript_data: List of transcript snippets
            max_chars: Maximum characters to include (to stay within token limits)
        
        Returns:
            Formatted transcript string
        """
        lines = []
        total_chars = 0
        
        for snippet in transcript_data:
            # Format: [MM:SS] Text
            timestamp = self._format_timestamp(snippet.start)
            line = f"[{timestamp}] {snippet.text}"
            
            # Check if adding this line would exceed max_chars
            if total_chars + len(line) > max_chars:
                lines.append("... [transcript truncated for length] ...")
                break
            
            lines.append(line)
            total_chars += len(line) + 1  # +1 for newline
        
        return "\n".join(lines)
    
    @staticmethod
    def _format_timestamp(seconds: float) -> str:
        """Convert seconds to HH:MM:SS or MM:SS format."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes:02d}:{secs:02d}"
    
    def segment_from_text(self, video_id: str, full_text: str, duration: float) -> VideoSegmentation:
        """
        Alternative method: segment from full transcript text (no timestamps).
        This is less accurate but works when timestamp data isn't available.
        
        Args:
            video_id: YouTube video ID
            full_text: Complete transcript as plain text
            duration: Total video duration in seconds
        
        Returns:
            VideoSegmentation object
        """
        # Use simplified prompt for plain text
        simple_prompt = PromptTemplate(
            template="""You are an expert at analyzing educational video transcripts.

VIDEO ID: {video_id}
TOTAL DURATION: {duration} seconds
TRANSCRIPT:
{transcript}

Identify logical segments in this video. Since exact timestamps aren't available,
estimate start/end times proportionally based on the text flow.

{format_instructions}

Provide your analysis:""",
            input_variables=["video_id", "transcript", "duration"],
            partial_variables={"format_instructions": self.parser.get_format_instructions()}
        )
        
        simple_chain = simple_prompt | self.llm | self.parser
        
        # Truncate text if too long
        max_chars = 12000
        truncated_text = full_text[:max_chars]
        if len(full_text) > max_chars:
            truncated_text += "\n... [transcript truncated for length] ..."
        
        result = simple_chain.invoke({
            "video_id": video_id,
            "transcript": truncated_text,
            "duration": duration
        })
        
        return result
