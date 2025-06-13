from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, List, Dict, Any, Literal, TypeVar, Generic
from datetime import datetime, timezone
from enum import Enum
from uuid import UUID
from fastapi import HTTPException
import re

T = TypeVar('T')

class MessageType(str, Enum):
    """Enum for different message types"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    FUNCTION = "function"



class Message(BaseModel):
    """Base message model"""
    type: MessageType
    content: str = Field(..., max_length=4096, min_length=1)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator('content')
    def validate_content(cls, v):
        """Validate message content for XSS and SQL injection"""
        if not isinstance(v, str):
            raise ValueError('Content must be a string')
        if len(v) < 1 or len(v) > 4096:
            raise ValueError('Content must be between 1 and 4096 characters')
        return v

class ChatRequest(BaseModel):
    """Request schema for chat endpoint"""
    messages: List[Message]
    functions: Optional[List[Dict[str, Any]]] = None
    model: Literal["gpt-3.5-turbo"] = "gpt-3.5-turbo"
    temperature: float = Field(default=0.7, ge=0, le=2, description="Temperature for response randomness")
    max_tokens: Optional[int] = Field(default=None, ge=1, le=4096, description="Maximum tokens in response")
    session_id: UUID = Field(..., description="Unique session identifier")
    user_id: UUID = Field(..., description="User identifier")

    @model_validator(mode='after')
    def validate_messages(cls, values):
        """Validate that messages list is not empty and contains at least one user message"""
        messages = values.get('messages', [])
        if not messages:
            raise ValueError('Messages list cannot be empty')
        if not any(msg.type == MessageType.USER for msg in messages):
            raise ValueError('Messages must contain at least one user message')
        return values

class AuthRequest(BaseModel):
    """Request schema for authentication endpoints"""
    code: Optional[str] = Field(None, min_length=1)
    state: Optional[str] = Field(None, min_length=1)
    error: Optional[str] = None

    @field_validator('code')
    def validate_code(cls, v):
        """Validate OAuth code format"""
        if v and not re.match(r'^[a-zA-Z0-9-_.]+$', v):
            raise ValueError('Invalid code format')
        return v

class TokenRefreshRequest(BaseModel):
    """Request schema for token refresh endpoint"""
    refresh_token: str = Field(..., min_length=1)

    @field_validator('refresh_token')
    def validate_refresh_token(cls, v):
        """Validate refresh token format"""
        if not re.match(r'^[a-zA-Z0-9-_.]+$', v):
            raise ValueError('Invalid refresh token format')
        return v

class RateLimitRequest(BaseModel):
    """Request schema for rate limit test endpoint"""
    pass

class ResponseModel(BaseModel):
    """Base response model with type safety"""
    success: bool = True
    message: Optional[str] = Field(None, max_length=1024)
    data: Optional[T] = None

class ErrorResponse(BaseModel):
    """Error response model with enhanced security"""
    error: str = Field(..., max_length=1024)
    detail: Optional[str] = Field(None, max_length=1024)
    code: Optional[int] = Field(None, ge=100, le=599)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
