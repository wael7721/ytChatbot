from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from agent.chatbot.conversational import run_chatbot
from models import get_db

router = APIRouter()


class Message(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    video_id: str
    message: str
    conversation_history: Optional[List[Message]] = None


class ChatResponse(BaseModel):
    video_id: str
    user_message: str
    response: str
    video_title: str


@router.post("/chat", response_model=ChatResponse)
async def chat_with_video(request: ChatRequest):
    """
    Chat with a YouTube video using the conversational agent.
    
    Args:
        request: ChatRequest with video_id, message, and optional conversation_history
    
    Returns:
        ChatResponse with the agent's response
    """
    db = get_db()
    
    # Get video from database to verify it exists and get title
    video = db.get_video(request.video_id)
    if not video:
        raise HTTPException(
            status_code=404,
            detail=f"Video {request.video_id} not found in database. Please fetch transcript first."
        )
    
    # Ensure video has a title
    video_title = video.get("title")
    if not video_title:
        raise HTTPException(
            status_code=400,
            detail=f"Video {request.video_id} has no title in database. Please re-fetch the video with title metadata."
        )
    
    # Convert Pydantic models to dicts for the agent
    conversation_history = None
    if request.conversation_history:
        conversation_history = [
            {"role": msg.role, "content": msg.content}
            for msg in request.conversation_history
        ]
    
    try:
        # Run the chatbot agent
        response = run_chatbot(
            video_id=request.video_id,
            video_title=video_title,
            user_message=request.message,
            conversation_history=conversation_history
        )
        
        return ChatResponse(
            video_id=request.video_id,
            user_message=request.message,
            response=response,
            video_title=video_title
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error running chatbot: {str(e)}"
        )


@router.get("/chat/segments/{video_id}")
async def get_video_segments(video_id: str):
    """
    Get the video segments to display in the chat interface.
    
    Args:
        video_id: YouTube video ID
    
    Returns:
        Video metadata and segments
    """
    db = get_db()
    
    # Get video
    video = db.get_video(video_id)
    if not video:
        raise HTTPException(
            status_code=404,
            detail=f"Video {video_id} not found in database"
        )
    
    # Get segmentation
    segmentation = db.get_segmentation(video_id)
    if not segmentation:
        return {
            "video_id": video_id,
            "title": video.get("title", ""),
            "duration_seconds": video["duration_seconds"],
            "segments": None,
            "message": "No segmentation available yet. Please segment the video first."
        }
    
    return {
        "video_id": video_id,
        "title": video.get("title", ""),
        "duration_seconds": video["duration_seconds"],
        "overall_topic": segmentation["overall_topic"],
        "total_segments": segmentation["total_segments"],
        "segments": segmentation["segmentation"]["segments"]
    }
