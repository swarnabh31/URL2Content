from pydantic_settings import BaseSettings
from functools import lru_cache
from pathlib import Path

class Settings(BaseSettings):
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_TIMEOUT: int = 300
    MAX_TRANSCRIPT_CHARS: int = 60000  # Base limit, adjusted by strategy
    DEFAULT_TEMPERATURE: float = 0.7
    MAX_TOKENS: int = 4096
    CACHE_DIR: str = "./.cache"
    LOG_LEVEL: str = "INFO"
    LOG_DIR: str = "./logs"

    class Config:
        env_file = ".env"
        extra = "ignore"

@lru_cache()
def get_settings() -> Settings:
    return Settings()
