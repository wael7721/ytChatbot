from urllib.parse import urlparse, parse_qs

def extract_video_id(video_url: str) -> str:
    """
    Extract video ID from various YouTube URL formats:
    - https://www.youtube.com/watch?v=VIDEO_ID
    - https://youtu.be/VIDEO_ID
    - https://www.youtube.com/embed/VIDEO_ID
    - Or just VIDEO_ID directly
    """
    if not video_url:
        return None
    
    # If it's already just an ID (11 chars, no special chars)
    if len(video_url) == 11 and '/' not in video_url and '?' not in video_url:
        return video_url
    
    # Parse full URLs
    try:
        parsed = urlparse(video_url)
        
        # youtu.be format
        if parsed.hostname in ('youtu.be', 'www.youtu.be'):
            return parsed.path.lstrip('/')
        
        # youtube.com/watch format
        if parsed.hostname in ('youtube.com', 'www.youtube.com'):
            if parsed.path == '/watch':
                return parse_qs(parsed.query).get('v', [None])[0]
            # youtube.com/embed format
            elif parsed.path.startswith('/embed/'):
                return parsed.path.split('/')[2]
        
        # If no pattern matched, try to extract 11-char ID
        for part in video_url.split('/'):
            if len(part) == 11:
                return part
    except Exception:
        pass
    
    return None
