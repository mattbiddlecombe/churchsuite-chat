from typing import Optional, List, Dict, Any
from pydantic import BaseModel

class ErrorResponse(BaseModel):
    error: str
    detail: str

class SuccessResponse(BaseModel):
    message: str
    data: Optional[Dict[str, Any]] = None
