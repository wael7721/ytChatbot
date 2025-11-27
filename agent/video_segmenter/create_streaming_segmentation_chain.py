"""
Create an LCEL chain that supports streaming output.
"""

import os
from typing import Optional
from langchain_groq import ChatGroq
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate
from models import VideoSegmentation


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
