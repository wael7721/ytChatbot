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
        partial_variables={"format_instructions": parser.get_format_instructions()}
    )
    
    # LCEL chain composition
    chain = (
        prompt 
        | llm 
        | parser
    )
    
    return chain


def format_transcript_snippets(snippets: list, max_chars: int = 15000) -> str:
    """
    Format transcript snippets into timestamped text.
    
    Args:
        snippets: List of transcript snippets with .text, .start, .duration
        max_chars: Maximum characters to include
    
    Returns:
        Formatted transcript string
    """
    lines = []
    total_chars = 0
    
    for snippet in snippets:
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

Identify 3-8 logical segments. Return start_time and end_time in SECONDS.

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

