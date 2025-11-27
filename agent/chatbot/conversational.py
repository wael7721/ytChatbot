from langchain_core.prompts import PromptTemplate
from langchain.agents import create_agent
from langchain.tools import tool
from src.config import instruction_model
from models import get_db


@tool
def getSegmentTranscript(video_id: str, start_time: int, end_time: int, max_snippets: int = 50) -> str:
    """
    Get transcript text for a specific time range.
    
    If start_time equals end_time, returns the transcript snippet at that exact time.
    Otherwise returns all transcript snippets within the time range, up to max_snippets limit.
    
    Args:
        video_id: YouTube video ID
        start_time: Start time in seconds
        end_time: End time in seconds (if equal to start_time, gets single snippet)
        max_snippets: Maximum number of transcript snippets to return (default: 50)
    
    Returns:
        Transcript text for the time range, or error message if video not found
    """
    db = get_db()
    
    # Get video from database
    video = db.get_video(video_id)
    if not video:
        return f"Error: Video {video_id} not found in database"
    
    transcript = video["transcript"]
    
    # Handle exact time query (start == end)
    if start_time == end_time:
        # Find the snippet that contains this exact timestamp
        for snippet in transcript:
            snippet_start = snippet["start"]
            snippet_end = snippet_start + snippet.get("duration", 0)
            
            if snippet_start <= start_time < snippet_end:
                return snippet["text"]
        
        return f"No transcript found at {start_time} seconds"
    
    # Handle time range query
    relevant_snippets = []
    for snippet in transcript:
        snippet_start = snippet["start"]
        snippet_end = snippet_start + snippet.get("duration", 0)
        
        # Include snippet if it overlaps with the requested range
        if snippet_start < end_time and snippet_end > start_time:
            relevant_snippets.append(snippet)
            
            # Stop if we've reached the limit
            if len(relevant_snippets) >= max_snippets:
                break
    
    if not relevant_snippets:
        return f"No transcript found between {start_time}s and {end_time}s"
    
    # Join all snippet texts
    transcript_text = " ".join(snippet["text"] for snippet in relevant_snippets)
    
    # Add notice if limit was reached
    if len(relevant_snippets) >= max_snippets:
        transcript_text += f"\n\n[Note: Showing first {max_snippets} snippets. Total range may contain more.]"
    
    return transcript_text


def format_instructions(video_id: str = None, video_title: str = None, conversation_history: list = None) -> dict:
    """
    Format all variables needed for the agent initialization.
    
    Args:
        video_id: YouTube video ID (optional, will fetch from getSegmentTranscript context if None)
        video_title: Title of the video (optional, will fetch from database if None and video_id is provided)
        conversation_history: List of previous conversation messages
    
    Returns:
        Dictionary with all formatted variables for the agent
    """
    db = get_db()
    
    # If video_id is None, set default values
    if video_id is None:
        formatted_segments = "No video specified yet."
        video_title = video_title or "No video"
        formatted_history = "No previous conversation." if not conversation_history else "\n".join([
            f"{msg.get('role', 'user')}: {msg.get('content', '')}"
            for msg in conversation_history
        ])
    else:
        # Get video info from database if title not provided or to fetch segments
        video = db.get_video(video_id)
        
        # Use provided title, or fetch from DB, or use fallback
        if video_title is None:
            video_title = video.get("title", f"Video {video_id}") if video else f"Video {video_id}"
        
        # Get segmentation from database
        segmentation = db.get_segmentation(video_id)
        
        # Format video segments
        if segmentation and segmentation.get("segmentation"):
            segments = segmentation["segmentation"]["segments"]
            formatted_segments = "\n".join([
                f"- {seg['title']} ({seg['start_time']}s - {seg['end_time']}s): {seg['summary']}"
                for seg in segments
            ])
        else:
            formatted_segments = "No segments available yet."
        
        # Format conversation history
        if conversation_history:
            formatted_history = "\n".join([
                f"{msg.get('role', 'user')}: {msg.get('content', '')}"
                for msg in conversation_history
            ])
        else:
            formatted_history = "No previous conversation."
    
    # Format tool information
    tool_name = getSegmentTranscript.name
    tool_description = getSegmentTranscript.description
    
    return {
        "tool_names": tool_name,
        "tool": f"{tool_name}: {tool_description}",
        "video_title": video_title,
        "video_segments": formatted_segments,
        "conversation_history": formatted_history,
    }


# Agent prompt template
prompt = """You are a youtube chatbot designed to assist users with inquiries about youtube videos.
your primary function is to provide accurate and concise information based on the video's transcript and metadata.
and assist users in navigating and understanding the content of youtube videos effectively by providing exercises and explanations.
You should be able to answer questions related to the video's content, summarize key points, and provide additional context or explanations as needed.
you are given a tool named {tool_names} that helps you with getting the full transcript of a video segment to help you answer user questions.

Tool available:
{tool}

here is the video title: {video_title}
Heres the key segments of the video:
{video_segments}

The conversation history so far:
{conversation_history}

User message: {message}

"""

template = PromptTemplate(
    input_variables=[
        "tool_names",
        "tool",
        "video_title",
        "video_segments",
        "conversation_history",
        "message",
    ],
    template=prompt,
)

# Initialize agent with prompt, tools, and model
agent = create_agent(
    model=instruction_model,
    tools=[getSegmentTranscript],
    system_prompt=prompt
)


def run_chatbot(video_id: str, video_title: str, user_message: str, conversation_history: list = None):
    """
    Run the chatbot agent with formatted context.
    
    Args:
        video_id: YouTube video ID
        video_title: Title of the video
        user_message: The user's current message/question
        conversation_history: List of previous conversation messages
    
    Returns:
        Agent's response
    """
    # Format all the context variables
    context = format_instructions(video_id, video_title, conversation_history)
    
    # Add the current user message
    context["message"] = user_message
    
    # Invoke the agent with all variables

    formatted_prompt = template.format(**context)

    response = agent.invoke({"system_instructions":formatted_prompt})
    
    return response["messages"][-1].content