from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound, TranscriptsDisabled

def getTranscript(video_id, languages=None):
    """
    Fetch transcript for a YouTube video with language fallback support.
    
    Args:
        video_id: YouTube video ID
        languages: List of language codes to try (default: ['en', 'es', 'fr', 'de'])
    
    Returns:
        Transcript object or error message string
    """
    if languages is None:
        # Try English first, then common languages, then any available
        languages = ['en', 'es', 'fr', 'de', 'pt', 'it', 'ja', 'ko', 'zh-Hans', 'zh-Hant']
    
    ytt_api = YouTubeTranscriptApi()
    
    try:
        # Try to fetch transcript in preferred languages
        transcript = ytt_api.fetch(video_id, languages=languages)
        return transcript
    except NoTranscriptFound as e:
        # If no transcript in preferred languages, try getting any available transcript
        try:
            transcript_list = ytt_api.list_transcripts(video_id)
            # Get first available transcript (generated or manual)
            transcript = transcript_list.find_transcript(transcript_list._manually_created_transcripts or transcript_list._generated_transcripts)
            # Translate to English if possible
            if hasattr(transcript, 'translate') and transcript.language_code != 'en':
                transcript = transcript.translate('en')
            return transcript.fetch()
        except (NoTranscriptFound, TranscriptsDisabled) as inner_e:
            return f"No transcript available for this video. Error: {str(inner_e)}"
    except TranscriptsDisabled:
        return "Transcripts are disabled for this video."
    except Exception as e:
        return f"Error fetching transcript: {str(e)}"