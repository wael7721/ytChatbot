"""
Endpoints package - exports all API routers.
"""

from .transcript import router as transcript_router
from .segmentation import router as segmentation_router
from .chatbot import router as chatbot_router

__all__ = ["transcript_router", "segmentation_router", "chatbot_router"]
