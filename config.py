from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
import os

class Settings(BaseSettings):
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_TIMEOUT: int = 300
    MAX_TRANSCRIPT_CHARS: int = 60000
    DEFAULT_TEMPERATURE: float = 0.7
    MAX_TOKENS: int = 4096
    CACHE_DIR: str = "./.cache"
    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

@lru_cache()
def get_settings() -> Settings:
    return Settings()
