import re
import logging
from urllib.parse import urlparse
from error_handler import AppError

logger = logging.getLogger(__name__)

def validate_youtube_url(url: str) -> str:
    """
    Strict YouTube URL validation.
    
    Args:
        url: The YouTube URL to validate
        
    Returns:
        str: The validated YouTube video ID
        
    Raises:
        AppError: If the URL is invalid
    """
    if not url or not url.strip():
        logger.warning("Empty URL provided for validation")
        raise AppError("Please enter a YouTube URL")
    
    url = url.strip()
    parsed = urlparse(url)
    
    valid_domains = {"youtube.com", "www.youtube.com", "youtu.be", "m.youtube.com"}
    if parsed.netloc not in valid_domains:
        logger.warning(f"Invalid domain in URL: {parsed.netloc}")
        raise AppError("Only YouTube URLs are supported")
    
    # Extract and validate video ID
    patterns = [
        r"(?:v=|\/)([0-9A-Za-z_-]{11}).*",  # Standard YouTube URLs
        r"youtu.be\/([0-9A-Za-z_-]{11})",    # youtu.be short URLs
        r"^([0-9A-Za-z_-]{11})$",            # Just the video ID
    ]
    
    video_id = None
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            video_id = match.group(1)
            break
    
    if not video_id or len(video_id) != 11:
        logger.warning(f"Invalid video ID extracted from URL: {url}")
        raise AppError("Invalid YouTube video ID")
    
    logger.info(f"Valid YouTube URL validated. Video ID: {video_id}")
    return video_id

def sanitize_transcript(transcript: str) -> str:
    """
    Remove potential prompt injection patterns from transcript.
    
    Args:
        transcript: The raw transcript text
        
    Returns:
        str: Sanitized transcript with dangerous patterns removed
    """
    if not transcript:
        return transcript
    
    # Remove common jailbreak patterns
    dangerous_patterns = [
        r"ignore previous instructions",
        r"system prompt",
        r"you are now",
        r"override",
        r"DAN mode",
        r"developer mode",
        r"jailbreak",
        r"forget everything",
        r"you are no longer",
        r"new instructions",
    ]
    
    cleaned = transcript
    removed_count = 0
    
    for pattern in dangerous_patterns:
        # Case insensitive replacement
        cleaned, count = re.subn(pattern, "[REMOVED]", cleaned, flags=re.IGNORECASE)
        removed_count += count
    
    if removed_count > 0:
        logger.info(f"Sanitized transcript: removed {removed_count} potentially dangerous patterns")
    
    return cleaned