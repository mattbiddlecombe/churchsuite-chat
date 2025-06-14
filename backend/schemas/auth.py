from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class Token(BaseModel):
    """Token response schema"""
    access_token: str
    token_type: str

class TokenData(BaseModel):
    """Token data schema"""
    username: Optional[str] = None
    exp: Optional[datetime] = None
