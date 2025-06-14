from typing import Optional
from pydantic import BaseSettings, Field
import os
import secrets

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

class Settings(BaseSettings):
    """Application settings"""
    
    # Core settings
    APP_NAME: str = Field(default="ChurchSuite Chatbot API", env="APP_NAME")
    API_V1_STR: str = Field(default="/api/v1", env="API_V1_STR")
    
    # API settings
    API_HOST: str = Field(default="0.0.0.0", env="API_HOST")
    API_PORT: int = Field(default=8000, env="API_PORT")
    
    # JWT settings
    JWT_SECRET: str = Field(default_factory=lambda: secrets.token_hex(32), env="JWT_SECRET")
    JWT_EXPIRATION: int = Field(default=3600, env="JWT_EXPIRATION")
    JWT_ALGORITHM: str = Field(default="HS256", env="JWT_ALGORITHM")
    
    # CORS settings
    CORS_ORIGINS: list[str] = Field(default=["http://localhost:3000"], env="CORS_ORIGINS")
    CORS_ALLOW_CREDENTIALS: bool = Field(default=True, env="CORS_ALLOW_CREDENTIALS")
    CORS_ALLOW_METHODS: list[str] = Field(default=["*"], env="CORS_ALLOW_METHODS")
    CORS_ALLOW_HEADERS: list[str] = Field(default=["*"], env="CORS_ALLOW_HEADERS")
    
    # OpenAPI settings
    OPENAPI_URL: str = Field(default="/openapi.json", env="OPENAPI_URL")
    
    # ChurchSuite settings
    CS_CLIENT_ID: Optional[str] = Field(default=None, env="CS_CLIENT_ID")
    CS_CLIENT_SECRET: Optional[str] = Field(default=None, env="CS_CLIENT_SECRET")
    CHURCHSUITE_BASE_URL: str = Field(default="https://api.churchsuite.co.uk/v2", env="CHURCHSUITE_BASE_URL")
    CHURCHSUITE_REDIRECT_URI: str = Field(default="http://localhost:8000/auth/callback", env="CHURCHSUITE_REDIRECT_URI")
    
    # OpenAI settings
    OPENAI_API_KEY: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    OPENAI_API_BASE: str = Field(default="https://api.openai.com/v1", env="OPENAI_API_BASE")
    OPENAI_MODEL: str = Field(default="gpt-3.5-turbo", env="OPENAI_MODEL")
    OPENAI_API_BASE: str = "https://api.openai.com/v1"
    OPENAI_MODEL: str = "gpt-3.5-turbo"
    
    # Vector DB settings
    VECTOR_DB_URL: str = "http://localhost:6333"
    
    # Rate limiting
    RATE_LIMIT_WINDOW: int = 60  # seconds
    RATE_LIMIT_MAX_REQUESTS: int = 100
    
    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=True
    )

# Initialize settings
settings = Settings()
