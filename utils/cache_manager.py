import hashlib
import json
from pathlib import Path
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class CacheManager:
    """
    Manages local caching of YouTube transcripts and generated LLM content
    to avoid redundant API calls and slow LLM processing.
    """
    def __init__(self, cache_dir: Path = Path("./.cache")):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(exist_ok=True)
        
        self.transcript_cache = cache_dir / "transcripts"
        self.content_cache = cache_dir / "content"
        
        self.transcript_cache.mkdir(exist_ok=True)
        self.content_cache.mkdir(exist_ok=True)

    def _get_key(self, data: str) -> str:
        """Generate a short unique hash for a given string."""
        return hashlib.sha256(data.encode()).hexdigest()[:16]

    def get_transcript(self, url: str) -> str | None:
        """Retrieve a cached transcript if it exists and is not expired."""
        key = self._get_key(url)
        cache_file = self.transcript_cache / f"{key}.json"

        if cache_file.exists():
            try:
                data = json.loads(cache_file.read_text())
                # Cache valid for 7 days
                cached_time = datetime.fromisoformat(data["cached_at"])
                if datetime.now() - cached_time < timedelta(days=7):
                    logger.info(f"Cache HIT: Transcript for {url}")
                    return data["transcript"]
                logger.info(f"Cache EXPIRED: Transcript for {url}")
            except Exception as e:
                logger.warning(f"Error reading transcript cache: {e}")
        
        return None

    def save_transcript(self, url: str, transcript: str):
        """Save a transcript to the local cache."""
        key = self._get_key(url)
        cache_file = self.transcript_cache / f"{key}.json"
        try:
            cache_file.write_text(json.dumps({
                "url": url,
                "transcript": transcript,
                "cached_at": datetime.now().isoformat()
            }))
            logger.info(f"Cache SAVE: Transcript for {url}")
        except Exception as e:
            logger.error(f"Error saving transcript cache: {e}")

    def get_content(self, transcript: str, model: str, content_type: str) -> str | None:
        """Retrieve cached generated content based on transcript, model, and type."""
        # We use the transcript hash + model + type as the unique key
        key = self._get_key(f"{transcript}{model}{content_type}")
        cache_file = self.content_cache / f"{key}.md"
        
        if cache_file.exists():
            try:
                logger.info(f"Cache HIT: {content_type} for model {model}")
                return cache_file.read_text()
            except Exception as e:
                logger.warning(f"Error reading content cache: {e}")
        
        return None

    def save_content(self, transcript: str, model: str, content_type: str, content: str):
        """Save generated content to the local cache."""
        key = self._get_key(f"{transcript}{model}{content_type}")
        cache_file = self.content_cache / f"{key}.md"
        try:
            cache_file.write_text(content)
            logger.info(f"Cache SAVE: {content_type} for model {model}")
        except Exception as e:
            logger.error(f"Error saving content cache: {e}")
