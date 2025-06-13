from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
import re

class GivingAccountFilter(BaseModel):
    """Filter parameters for listing giving accounts"""
    page: int = Field(1, ge=1)
    per_page: int = Field(20, ge=1, le=100)
    search: Optional[str] = None
    
    @validator('search')
    def validate_search(cls, v):
        """Validate search term format"""
        if v and len(v) < 3:
            raise ValueError('Search term must be at least 3 characters long')
        return v

class GivingTransactionFilter(BaseModel):
    """Filter parameters for listing giving transactions"""
    page: int = Field(1, ge=1)
    per_page: int = Field(20, ge=1, le=100)
    account_id: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    
    @validator('account_id')
    def validate_account_id(cls, v):
        """Validate account ID format"""
        if v and not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('Invalid account ID format')
        return v
    
    @validator('end_date')
    def validate_dates(cls, v, values):
        """Validate date range"""
        if v and 'start_date' in values and values['start_date']:
            if v < values['start_date']:
                raise ValueError('End date cannot be before start date')
        return v

class GivingSummaryFilter(BaseModel):
    """Filter parameters for giving summary"""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    
    @validator('end_date')
    def validate_dates(cls, v, values):
        """Validate date range"""
        if v and 'start_date' in values and values['start_date']:
            if v < values['start_date']:
                raise ValueError('End date cannot be before start date')
        return v
