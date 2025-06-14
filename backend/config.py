from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field
import secrets


class Settings(BaseSettings):
    # Core settings
    APP_NAME: str = "ChurchSuite Chatbot API"
    API_V1_STR: str = "/api/v1"
    
    # API settings
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    
    # JWT settings
    JWT_SECRET: str = Field(default_factory=lambda: secrets.token_hex(32))
    JWT_EXPIRATION: int = 3600
    JWT_ALGORITHM: str = "HS256"
    
    # CORS settings
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: list[str] = ["*"]
    CORS_ALLOW_HEADERS: list[str] = ["*"]
    
    # OpenAPI settings
    OPENAPI_URL: str = "/openapi.json"
    
    # ChurchSuite settings
    CS_CLIENT_ID: Optional[str] = None
    CS_CLIENT_SECRET: Optional[str] = None
    CHURCHSUITE_BASE_URL: str = "https://api.churchsuite.co.uk/v2"
    CHURCHSUITE_REDIRECT_URI: str = "http://localhost:8000/auth/callback"
    
    # OpenAI settings
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_API_BASE: str = "https://api.openai.com/v1"
    OPENAI_MODEL: str = "gpt-3.5-turbo"
    
    # Vector DB settings
    VECTOR_DB_URL: str = "http://localhost:6333"
    
    # Rate limiting
    RATE_LIMIT_WINDOW: int = 60  # seconds
    RATE_LIMIT_MAX_REQUESTS: int = 100
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
