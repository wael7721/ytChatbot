"""
Create an LCEL chain for video segmentation.
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
