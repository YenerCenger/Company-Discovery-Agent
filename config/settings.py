from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Database Configuration
    DATABASE_URL: str = "postgresql://postgres:admin123@localhost:5432/realestate_intel"
    DB_ECHO: bool = False

    # Application Settings
    APP_NAME: str = "Real Estate Marketing Intelligence"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # Scraping Configuration
    REQUEST_TIMEOUT: int = 30
    MAX_RETRIES: int = 3
    USER_AGENT: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"

    # Instagram Authentication
    INSTAGRAM_USERNAME: Optional[str] = None
    INSTAGRAM_PASSWORD: Optional[str] = None
    INSTAGRAM_SESSION_FILE: Path = Path(__file__).parent.parent / "data" / ".instaloader_session"

    # Crawl4AI Settings
    CRAWL4AI_ENABLED: bool = False  # Toggle for real company scraping
    CRAWL4AI_MAX_DEPTH: int = 2
    CRAWL4AI_DELAY_MS: int = 1000
    CRAWL4AI_TIMEOUT: int = 30
    CRAWL4AI_USER_AGENTS: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/121.0.0.0,Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/537.36"
    CRAWL4AI_CACHE_ENABLED: bool = True
    CRAWL4AI_CACHE_EXPIRY_HOURS: int = 24

    # Ollama LLM Settings (for HTML parsing)
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "gemma3:4b"
    OLLAMA_TIMEOUT: int = 300  # Seconds for LLM generation
    OLLAMA_TEMPERATURE: float = 0.1  # Low temp for structured output
    OLLAMA_MAX_TOKENS: int = 4000

    # Video Download Settings
    DOWNLOAD_BASE_PATH: Path = Path(__file__).parent.parent / "data" / "downloads"
    YTDLP_MAX_FILESIZE: str = "500M"
    YTDLP_FORMAT: str = "best[height<=1080]"

    # Agent Parameters
    COMPANY_DISCOVERY_DEFAULT_LIMIT: int = 50
    VIDEO_FINDER_DAYS_BACK: int = 90
    VIDEO_FINDER_MIN_VIEWS: int = 100
    VIDEO_FINDER_TOP_N: int = 50  # Get top N best performing videos per profile
    VIDEO_SORT_BY: str = "views"  # "views", "engagement", "likes"
    VIDEO_DOWNLOAD_PER_COMPANY: int = 5  # Number of videos to download per company

    # API Keys (Future Use)
    YOUTUBE_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


# Singleton instance
settings = Settings()
