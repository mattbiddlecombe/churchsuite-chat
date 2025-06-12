from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class MessageType(str, Enum):
    """Enum for different message types"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    FUNCTION = "function"


class Message(BaseModel):
    """Base message model"""
    type: MessageType
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ChatRequest(BaseModel):
    """Request schema for chat endpoint"""
    messages: List[Message]
    functions: Optional[List[Dict[str, Any]]] = None
    model: str = "gpt-3.5-turbo"
    temperature: float = Field(default=0.7, ge=0, le=2)
    max_tokens: Optional[int] = Field(default=None, ge=1, le=4096)

    @validator('messages')
    def validate_messages(cls, v):
        """Validate that messages list is not empty and contains at least one user message"""
        if not v:
            raise ValueError('Messages list cannot be empty')
        if not any(msg.type == MessageType.USER for msg in v):
            raise ValueError('At least one user message is required')
        return v


class AuthRequest(BaseModel):
    """Request schema for authentication endpoints"""
    code: Optional[str] = None
    state: Optional[str] = None
    error: Optional[str] = None

    @validator('error')
    def validate_error(cls, v):
        """Ensure error is not present when code is provided"""
        if v and v != 'none':
            raise ValueError(f'Authentication error: {v}')
        return v


class TokenRefreshRequest(BaseModel):
    """Request schema for token refresh endpoint"""
    refresh_token: str


class RateLimitRequest(BaseModel):
    """Request schema for rate limit test endpoint"""
    pass  # Currently empty, but can be extended for future parameters


class ResponseModel(BaseModel):
    """Base response model"""
    success: bool
    message: Optional[str] = None
    data: Optional[Any] = None


class ErrorResponse(BaseModel):
    """Error response model"""
    error: str
    detail: Optional[str] = None
