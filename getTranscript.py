from youtube_transcript_api import YouTubeTranscriptApi
def getTranscript(video_id):
    ytt_api = YouTubeTranscriptApi()
    transcript= ytt_api.fetch(video_id)
    if transcript:
        return transcript
    else:
        return "No transcript available for this video."


def getTranscriptExample():
    video_id = "i_LwzRVP7bg"  # Example video ID https://www.youtube.com/watch?v=i_LwzRVP7bg
    transcript = getTranscript(video_id)
    print(transcript)
    if transcript:
        text= ' '.join(item.text for item in transcript)
        print("extracted transcript for video:" + text)
    else:
        print("no text extracted")