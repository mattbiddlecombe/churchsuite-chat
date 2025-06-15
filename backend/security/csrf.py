from fastapi import FastAPI, Request, Response, HTTPException
from pydantic import BaseModel, ConfigDict, field_validator, Field
from typing import Optional, List, Dict, Any, Callable, Awaitable
import secrets
import logging
from datetime import datetime, timedelta, timezone
import json
import re

def generate_csrf_token() -> str:
    """Generate a secure CSRF token"""
    return secrets.token_urlsafe(32)

logger = logging.getLogger(__name__)

class CSRFConfig(BaseModel):
    """Configuration for CSRF protection"""
    # Request methods to protect
    protected_methods: List[str] = Field(
        default=["POST", "PUT", "PATCH", "DELETE"],
        description="HTTP methods that require CSRF protection"
    )
    
    # Expiration settings
    token_expiration: int = Field(
        default=3600,
        description="CSRF token expiration in seconds"
    )
    
    # Header names
    header_name: str = Field(
        default="X-CSRF-Token",
        description="Header name for CSRF token"
    )
    cookie_name: str = Field(
        default="csrf_token",
        description="Cookie name for CSRF token"
    )
    
    model_config = ConfigDict(
        validate_assignment=True
    )
    
    @field_validator('protected_methods')
    def validate_protected_methods(cls, v):
        allowed_methods = ["POST", "PUT", "PATCH", "DELETE"]
        for method in v:
            if method not in allowed_methods:
                raise ValueError(f"Invalid HTTP method: {method}")
        return v

def add_csrf_protection(app: FastAPI, config: Optional[CSRFConfig] = None):
    """Add CSRF protection to the FastAPI app"""
    config = config or CSRFConfig()
    
    @app.middleware("http")
    async def csrf_middleware(request: Request, call_next):
        try:
            # Skip CSRF protection for auth endpoints
            if request.url.path.startswith("/api/v1/auth"):
                return await call_next(request)
            
            # Generate CSRF token for GET requests (except auth endpoints)
            if request.method == "GET" and not request.url.path.startswith("/api/v1/auth"):
                csrf_token = secrets.token_urlsafe(32)
                response = await call_next(request)
                response.headers[config.header_name] = csrf_token
                response.set_cookie(
                    config.cookie_name,
                    csrf_token,
                    httponly=True,
                    secure=True,
                    samesite="lax",
                    max_age=config.token_expiration
                )
                return response
            
            # Validate CSRF token for protected methods
            if request.method in config.protected_methods:
                # Get CSRF token from header
                header_token = request.headers.get(config.header_name)
                
                # Get CSRF token from cookie
                cookie_token = request.cookies.get(config.cookie_name)
                
                # If either token is missing, return appropriate error
                if not header_token:
                    return Response(
                        content="CSRF token missing",
                        status_code=403
                    )
                
                if not cookie_token:
                    return Response(
                        content="CSRF token missing from cookie",
                        status_code=403
                    )
                
                # Validate tokens match
                if header_token != cookie_token:
                    return Response(
                        content="CSRF token mismatch",
                        status_code=403
                    )
                
                # If we reach here, both tokens exist and match
                return await call_next(request)

            # Pass through to next middleware
            return await call_next(request)
            
        except Exception as e:
            logger.error(f"CSRF middleware error: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="Internal server error"
            )

# Usage:
# app = FastAPI()
# add_csrf_protection(app)
# or with custom config:
# add_csrf_protection(app, CSRFConfig(...))
