"""YouTube URL parsing and video ID extraction utilities."""

import re
from urllib.parse import urlparse, parse_qs


def extract_video_id(url: str) -> str:
    """
    Extract YouTube video ID from various URL formats.
    
    Handles:
    - youtube.com/watch?v=VIDEO_ID
    - youtu.be/VIDEO_ID
    - youtube.com/shorts/VIDEO_ID
    - youtube.com/embed/VIDEO_ID
    - m.youtube.com/watch?v=VIDEO_ID
    - URLs with timestamps, playlists, and other params
    """
    # Normalize the URL first
    url = normalize_youtube_url(url)
    
    # Pattern for standard watch URLs
    watch_pattern = r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/|youtube\.com/shorts/)([a-zA-Z0-9_-]{11})'
    match = re.search(watch_pattern, url)
    
    if match:
        return match.group(1)
    
    # Fallback: try parsing query params
    parsed = urlparse(url)
    if parsed.hostname and 'youtube.com' in parsed.hostname or 'youtu.be' in parsed.hostname:
        if parsed.path.startswith('/shorts/'):
            video_id = parsed.path.split('/shorts/')[1].split('/')[0]
            if len(video_id) == 11:
                return video_id
        if parsed.path.startswith('/'):
            video_id = parsed.path.lstrip('/').split('/')[0]
            if len(video_id) == 11 and video_id.replace('-', '').replace('_', '').isalnum():
                return video_id
    
    # Try query params
    query_params = parse_qs(parsed.query)
    if 'v' in query_params:
        video_id = query_params['v'][0]
        if len(video_id) == 11:
            return video_id
    
    raise ValueError(f"Could not extract video ID from URL: {url}")


def normalize_youtube_url(url: str) -> str:
    """
    Normalize YouTube URL by removing tracking params and timestamps.
    Keeps only essential video ID.
    """
    # Remove common tracking parameters
    tracking_params = ['si', 'feature', 'utm_source', 'utm_medium', 'utm_campaign', 'ref']
    
    # Parse URL
    parsed = urlparse(url)
    query_params = parse_qs(parsed.query)
    
    # Keep only 'v' and 'list' params, remove others
    clean_params = {}
    if 'v' in query_params:
        clean_params['v'] = query_params['v'][0]
    if 'list' in query_params:
        clean_params['list'] = query_params['list'][0]
    
    # Reconstruct URL
    clean_query = '&'.join(f"{k}={v}" for k, v in clean_params.items())
    clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    if clean_query:
        clean_url += f"?{clean_query}"
    
    return clean_url
