from youtube_transcript_api import YouTubeTranscriptApi
def getTranscript(video_id):
    ytt_api = YouTubeTranscriptApi()
    transcript= ytt_api.fetch(video_id)
    if transcript:
        return transcript
    else:
        return "No transcript available for this video."