from pydantic import BaseModel
from typing import Dict, Any

class BaseRequestModel(BaseModel):
    """Base model for request validation"""
    
    @classmethod
    def validate_string_length(cls, v: Any) -> Any:
        """Validate string length to prevent DoS attacks"""
        if isinstance(v, str) and len(v) > 1000:
            raise ValueError("Input too long")
        return v

    @classmethod
    def sanitize_input(cls, v: Any) -> Any:
        """Sanitize input to prevent XSS"""
        if isinstance(v, str):
            # Replace dangerous characters
            v = v.replace('<', '&lt;').replace('>', '&gt;')
        return v

    @classmethod
    def validate_user_token(cls, v: str) -> str:
        """Validate user token format"""
        if not v or len(v) < 10:
            raise ValueError("Invalid user token")
        return v

    @classmethod
    def validate_message(cls, v: str) -> str:
        """Validate message content"""
        if not v or len(v) < 1:
            raise ValueError("Message cannot be empty")
        return v

class ChatRequest(BaseRequestModel):
    """Model for chat endpoint requests"""
    user_token: str
    message: str

    @classmethod
    def validate_user_token(cls, v: str) -> str:
        """Validate user token format"""
        if not v or len(v) < 10:
            raise ValueError("Invalid user token")
        return v

    @classmethod
    def validate_message(cls, v: str) -> str:
        """Validate message content"""
        if not v or len(v) < 1:
            raise ValueError("Message cannot be empty")
        return v
