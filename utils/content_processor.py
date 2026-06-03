from enum import Enum
from typing import List
import logging
from config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

class ContextStrategy(Enum):
    FULL = "full"       # Pass entire transcript (for high-context models)
    CHUNKED = "chunked" # Map-reduce summarization (for massive videos)
    SMART = "smart"     # Keep intro, key middle sections, and conclusion

def get_optimal_strategy(model_name: str, transcript_len: int) -> ContextStrategy:
    """
    Auto-select the best processing strategy based on the model's 
    estimated context window and the transcript length.
    """
    # Estimated context windows in characters (roughly 4 chars per token)
    # We use a conservative estimate.
    context_windows = {
        "gemma4": 128000,
        "qwen3.6": 128000,
        "llama3.3": 128000,
        "mistral": 32000,
        "phi3": 128000,
        "deepseek": 64000,
    }

    # Get the base model name (strip tags like :latest or :8b)
    base_model = model_name.lower().split(":")[0]
    
    # Find matching window or use default
    max_chars = 8000 # Default safe fallback
    for key, size in context_windows.items():
        if key in base_model:
            max_chars = size
            break

    # Strategy Selection Logic
    if transcript_len <= max_chars * 0.75:
        return ContextStrategy.FULL
    elif transcript_len <= max_chars * 3:
        return ContextStrategy.SMART
    else:
        return ContextStrategy.CHUNKED

def chunk_transcript(transcript: str, chunk_size: int = 6000) -> List[str]:
    """Split transcript into manageable chunks for Map-Reduce."""
    return [transcript[i:i+chunk_size] for i in range(0, len(transcript), chunk_size)]

def smart_truncate(transcript: str, max_chars: int = 15000) -> str:
    """
    Keep the beginning, middle, and end of the transcript 
    to preserve context without exceeding limits.
    """
    if len(transcript) <= max_chars:
        return transcript
    
    # Keep 20% start, 60% middle (spread), 20% end
    start = transcript[:int(max_chars * 0.2)]
    end = transcript[-int(max_chars * 0.2):]
    
    mid_start = int(len(transcript) * 0.4)
    mid_end = int(len(transcript) * 0.6)
    middle = transcript[mid_start:mid_end][:int(max_chars * 0.6)]
    
    return f"{start}\n\n[... Content Truncated ...]\n\n{middle}\n\n[... Content Truncated ...]\n\n{end}"
