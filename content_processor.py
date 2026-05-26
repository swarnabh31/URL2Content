from enum import Enum
import logging
from typing import List
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

class ContextStrategy(Enum):
    FULL = "full"       # Pass entire transcript (for 128K+ models)
    CHUNKED = "chunked" # Map-reduce summarization
    SMART = "smart"     # Keep intro, middle samples, and conclusion

def get_optimal_strategy(model_name: str, transcript_len: int) -> ContextStrategy:
    """
    Auto-select best processing strategy based on model capabilities
    and transcript length.
    """
    # Estimated context windows in characters (rough approximation)
    # Note: In a real scenario, these would be tokens. 1 token ~= 4 chars.
    context_windows = {
        "gemma4": 128000,
        "qwen": 128000,
        "llama": 128000,
        "mistral": 32000,
        "phi3": 128000,
        "deepseek": 128000,
    }

    # Clean model name to match keys (e.g., 'gemma4:31b' -> 'gemma4')
    base_model = model_name.split(":")[0].lower()
    
    # Find the best match in our known windows
    max_chars = 8000 # Default fallback
    for key, window in context_windows.items():
        if key in base_model:
            max_chars = window
            break

    # Strategy logic
    if transcript_len <= max_chars * 0.75:
        return ContextStrategy.FULL
    elif transcript_len <= max_chars * 2:
        return ContextStrategy.SMART
    else:
        return ContextStrategy.CHUNKED

def chunk_transcript(text: str, chunk_size: int = 10000) -> List[str]:
    """Split text into chunks of approximately chunk_size characters."""
    chunks = []
    for i in range(0, len(text), chunk_size):
        chunks.append(text[i : i + chunk_size])
    return chunks

def smart_truncate(text: str, max_chars: int = 15000) -> str:
    """
    Extracts the 'heart' of the transcript: 
    Intro (25%), Middle Sample (25%), and Conclusion (50%).
    """
    if len(text) <= max_chars:
        return text
    
    length = len(text)
    intro = text[:int(length * 0.2)]
    middle = text[int(length * 0.4):int(length * 0.6)]
    outro = text[int(length * 0.8):]
    
    return f"{intro}\n\n[... Middle Section Omitted ...]\n\n{middle}\n\n[... Middle Section Omitted ...]\n\n{outro}"
