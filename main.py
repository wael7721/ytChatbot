from fastapi import FastAPI
import time
import datetime
import uvicorn
from endpoints import transcript_router, segmentation_router
from dotenv import load_dotenv
from helpers.db_utils import get_database_stats
from models import get_db

load_dotenv()

app = FastAPI(title="ytChatbot API", version="0.1.0")
_start_time = time.time()

# Initialize database on startup
@app.on_event("startup")
def startup_event():
    """Initialize database on application startup."""
    db = get_db()
    print("✅ Database initialized")

# Include endpoint routers
app.include_router(transcript_router)
app.include_router(segmentation_router)


@app.get("/health", tags=["System"])
def health():
    """
    Simple health endpoint returning status, uptime (seconds) and current UTC timestamp.
    """
    uptime = time.time() - _start_time
    return {
        "status": "ok",
        "uptime_seconds": round(uptime, 2),
        "timestamp_utc": datetime.datetime.utcnow().isoformat() + "Z"
    }


@app.get("/stats", tags=["System"])
def stats():
    """
    Get database statistics.
    
    Returns information about stored videos, segmentations, and segments.
    """
    return get_database_stats()


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
