"""
Application configuration settings.

This module manages environment variables and default values using Pydantic Settings.
Automatically reads from .env file.

Database Architecture:
- MongoDB: Stores video analysis results (AnalysisResult, ViralStrategy)
- PostgreSQL: Stores video download jobs, companies, profiles (from Company Discovery Agent)
"""
from pathlib import Path
from typing import Literal
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings class.
    
    All configuration values are defined here. Environment variables are
    automatically read and merged with default values.
    
    Example .env file:
        # MongoDB (Analysis Results)
        MONGO_URL=mongodb://localhost:27017
        DB_NAME=ViralFlowDB
        
        # PostgreSQL (from main config/settings.py)
        DATABASE_URL=postgresql://postgres:admin123@localhost:5432/realestate_intel
        
        # AI Models
        OLLAMA_URL=http://localhost:11434/api/generate
        LLM_MODEL=deepseek-r1:8b
        WHISPER_MODEL_SIZE=medium
    """
    
    # ==================== PROJECT INFO ====================
    PROJECT_NAME: str = Field(
        default="ViralFlow Backend",
        description="Application name"
    )
    
    API_V1_STR: str = Field(
        default="/api/v1",
        description="API v1 endpoint prefix"
    )
    
    # ==================== MONGODB SETTINGS (Analysis Results) ====================
    MONGO_URL: str = Field(
        default="mongodb://localhost:27017",
        description="MongoDB connection URL for analysis results (env: MONGO_URL)"
    )
    
    DB_NAME: str = Field(
        default="ViralFlowDB",
        description="MongoDB database name for analysis results (env: DB_NAME)"
    )
    
    # NOTE: PostgreSQL settings are inherited from main project's config/settings.py
    # via database/session.py engine. No need to duplicate here.
    
    # ==================== AI MODEL SETTINGS ====================
    OLLAMA_URL: str = Field(
        default="http://localhost:11434/api/generate",
        description="Ollama API endpoint URL (env: OLLAMA_URL)"
    )
    
    LLM_MODEL: str = Field(
        default="deepseek-r1:8b",
        description="LLM model name to use (env: LLM_MODEL)"
    )
    
    WHISPER_MODEL_SIZE: Literal["tiny", "base", "small", "medium", "large"] = Field(
        default="medium",
        description="Whisper model size (env: WHISPER_MODEL_SIZE)"
    )
    
    # ==================== DIRECTORY PATHS ====================
    BASE_DIR: Path = Field(
        default_factory=lambda: Path(__file__).parent.parent.parent.parent,
        description="Project root directory (automatically calculated)"
    )
    
    VIDEO_DIR: Path = Field(
        default_factory=lambda: Path(__file__).parent.parent.parent.parent / "data" / "downloads",
        description="Directory for storing video files"
    )
    
    DATA_DIR: Path = Field(
        default_factory=lambda: Path(__file__).parent.parent.parent.parent / "data",
        description="Directory for storing data files"
    )
    
    # ==================== VALIDATION ====================
    @field_validator("OLLAMA_URL")
    @classmethod
    def validate_ollama_url(cls, v: str) -> str:
        """Validates Ollama URL format."""
        if not v.startswith(("http://", "https://")):
            raise ValueError("OLLAMA_URL must start with 'http://' or 'https://'")
        return v
    
    @field_validator("MONGO_URL")
    @classmethod
    def validate_mongo_url(cls, v: str) -> str:
        """Validates MongoDB URL format."""
        if not v.startswith("mongodb://") and not v.startswith("mongodb+srv://"):
            raise ValueError("MONGO_URL must start with 'mongodb://' or 'mongodb+srv://'")
        return v
    
    def model_post_init(self, __context) -> None:
        """Creates directories after settings are loaded."""
        self.VIDEO_DIR.mkdir(parents=True, exist_ok=True)
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    # ==================== PYDANTIC CONFIG ====================
    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).parent.parent.parent.parent / ".env"),  # Kök dizindeki .env dosyasını kullan
        env_ignore_empty=True,
        case_sensitive=False,
        extra="ignore"
    )


# Global settings instance - used throughout the application
settings = Settings()
