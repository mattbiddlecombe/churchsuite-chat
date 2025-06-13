from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
import re

class PersonSearchFilter(BaseModel):
    """Filter parameters for searching people"""
    query: str = Field(..., min_length=2, max_length=100)
    page: int = Field(1, ge=1)
    per_page: int = Field(20, ge=1, le=100)
    include_inactive: bool = False
    
    @validator('query')
    def validate_query(cls, v):
        """Validate search query format"""
        if not re.match(r'^[a-zA-Z0-9\s-]+$', v):
            raise ValueError('Search query contains invalid characters')
        return v

class PersonUpdate(BaseModel):
    """Schema for updating person information"""
    first_name: Optional[str] = Field(None, min_length=1, max_length=50)
    last_name: Optional[str] = Field(None, min_length=1, max_length=50)
    email: Optional[str] = None
    phone: Optional[str] = None
    
    @validator('email')
    def validate_email(cls, v):
        """Validate email format"""
        if v and not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', v):
            raise ValueError('Invalid email format')
        return v
    
    @validator('phone')
    def validate_phone(cls, v):
        """Validate phone number format"""
        if v and not re.match(r'^\+?[0-9\s-]{10,20}$', v):
            raise ValueError('Invalid phone number format')
        return v
