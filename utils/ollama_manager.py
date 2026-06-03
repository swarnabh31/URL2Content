"""
OllamaModelManager - Detects, lists, and filters locally installed Ollama models.
Filters to only return models capable of text generation (chat / instruct / text).
"""

import json
import urllib.request
import urllib.error
import logging
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def get_ollama_base_url() -> str:
    """Return the Ollama API base URL."""
    return settings.OLLAMA_BASE_URL


def list_all_models() -> list[dict]:
    """Fetch all models from the local Ollama instance."""
    base = get_ollama_base_url()
    try:
        req = urllib.request.Request(f"{base}/api/tags")
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            return data.get("models", [])
    except (urllib.error.URLError, ConnectionError, OSError) as e:
        logger.error(f"Failed to fetch models from Ollama at {base}: {e}")
        return []
    except json.JSONDecodeError as e:
        logger.error(f"Failed to decode Ollama API response: {e}")
        return []


def is_text_or_chat_model(model_info: dict) -> bool:
    """
    Heuristic to determine if a model supports text generation / chat.
    Accepts models with tags containing: instruct, chat, text, phi, llama, mistral,
    qwen, gemma, deepseek, codellama, neural-chat, or similar text-capable families.
    Rejects purely image, video, audio, or embedding-only models.
    """
    name = (model_info.get("name") or "").lower()
    details = model_info.get("details", {})
    parent = (details.get("parent_model") or "").lower()

    # Hard exclude patterns
    exclude_patterns = [
        "clip", "sentence-transform", "all-minilm",
        "whisper", "vosk", "faster-whisper",
        "stable-diffusion", "flux", "sdxl", "t2i",
        "lcm", "controlnet", "segment", "sam",
        "embed", "embedder", "embedding", "rerank",
        "nomic-embed", "bge-m3", "e5-mistral",
    ]
    for pat in exclude_patterns:
        if pat in name:
            return False

    # Include patterns for text/chat
    include_patterns = [
        "instruct", "chat", "text", "phi", "llama", "mistral",
        "qwen", "gemma", "deepseek", "codellama", "neural-chat",
        "aya", "yarn", "command", "openchat", "starcoder",
        "falcon", "dolphin", "solar", "nemo", "hermes",
        "neural-chat", "openhermes", "openorca",
        "zephyr", "tinyllama", "gpt2", "bert",
    ]
    for pat in include_patterns:
        if pat in name:
            return True

    # If no clear signal, include if model details has a format hint
    ftype = (details.get("format") or "").lower()
    family = (details.get("family") or "").lower()
    if ftype or family:
        return True

    # If details is empty, include conservatively (small models are usually text)
    if not details:
        return True

    # Fallback: include if we have a name at all
    return bool(name)


def get_text_chat_models() -> list[dict]:
    """Return list of model dicts that support text/chat, suitable for dropdown display."""
    all_models = list_all_models()
    return [m for m in all_models if is_text_or_chat_model(m)]


def get_model_names() -> list[str]:
    """Return just the model name strings for dropdown display."""
    models = get_text_chat_models()
    return [m["name"] for m in models]


def get_model_info_by_name(name: str) -> dict | None:
    """Return full model info dict for a given name."""
    for m in get_text_chat_models():
        if m["name"] == name:
            return m
    return None


def is_ollama_available() -> bool:
    """Check if Ollama is running and accessible."""
    try:
        base = get_ollama_base_url()
        req = urllib.request.Request(f"{base}/api/tags")
        urllib.request.urlopen(req, timeout=5)
        return True
    except (urllib.error.URLError, ConnectionError, OSError):
        return False
