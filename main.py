from fastapi import FastAPI
import time
import datetime
import uvicorn
from getTranscript import getTranscriptExample,getTranscript
app = FastAPI(title="ytChatbot API", version="0.1.0")
_start_time = time.time()

@app.get("/health")
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
@app.get("/transcript-example")
def transcript_example():
    """
    Endpoint to demonstrate fetching a transcript for an example video.
    """
    getTranscriptExample()
    return {"message": "Transcript example executed. Check console for output."}

@app.get("/transcript")
def transcript(video_id: str):
    """
    Endpoint to fetch the transcript for a given YouTube video ID.
    """
    transcript = getTranscript(video_id)
    if transcript:
        full = ' '.join(item['text'] for item in transcript)
        return {"transcript": full}
    else:
        return {"message": "No transcript available for this video."}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)