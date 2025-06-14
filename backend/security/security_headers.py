from typing import Optional, Dict, Any, Callable, Awaitable
from fastapi import FastAPI, Request, Response
from datetime import datetime, timedelta, timezone
import logging
import re
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)

class SecurityConfig(BaseModel):
    content_security_policy: str = Field(
        default="default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; frame-ancestors 'none'",
        description="Content Security Policy"
    )
    
    x_content_type_options: str = Field(
        default="nosniff",
        description="X-Content-Type-Options header"
    )
    
    x_frame_options: str = Field(
        default="DENY",
        description="X-Frame-Options header"
    )
    
    x_xss_protection: str = Field(
        default="1; mode=block",
        description="X-XSS-Protection header"
    )
    
    referrer_policy: str = Field(
        default="strict-origin-when-cross-origin",
        description="Referrer-Policy header"
    )
    
    strict_transport_security: str = Field(
        default="max-age=31536000; includeSubDomains",
        description="Strict-Transport-Security header"
    )
    
    permitted_cross_domain_policies: str = Field(
        default="none",
        description="X-Permitted-Cross-Domain-Policies header"
    )
    
    cache_control: str = Field(
        default="no-cache, no-store, must-revalidate",
        description="Cache-Control header"
    )
    
    pragma: str = Field(
        default="no-cache",
        description="Pragma header"
    )
    
    expires: str = Field(
        default="0",
        description="Expires header"
    )
    
    @field_validator('content_security_policy')
    def validate_csp(cls, v):
        required_parts = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'",
            "style-src 'self' 'unsafe-inline'"
        ]
        for part in required_parts:
            if part not in v:
                raise ValueError(f"CSP must include {part}")
        return v
    
    @field_validator('strict_transport_security')
    def validate_hsts(cls, v):
        if not v.startswith("max-age="):
            raise ValueError("HSTS must start with max-age=")
        return v

def add_security_headers(app: FastAPI, config: Optional[SecurityConfig] = None):
    """Add security headers to all responses"""
    config = config or SecurityConfig()

    @app.middleware("http")
    async def add_headers(request: Request, call_next):
        response = await call_next(request)
        
        # Add security headers
        response.headers["Content-Security-Policy"] = config.content_security_policy
        response.headers["X-Content-Type-Options"] = config.x_content_type_options
        response.headers["X-Frame-Options"] = config.x_frame_options
        response.headers["X-XSS-Protection"] = config.x_xss_protection
        response.headers["Referrer-Policy"] = config.referrer_policy
        response.headers["Strict-Transport-Security"] = config.strict_transport_security
        response.headers["X-Permitted-Cross-Domain-Policies"] = config.permitted_cross_domain_policies
        
        # Add cache control headers
        response.headers["Cache-Control"] = config.cache_control
        response.headers["Pragma"] = config.pragma
        response.headers["Expires"] = config.expires
        
        # Add CORS headers
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Headers"] = "content-type, authorization, x-csrf-token"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        
        return response

# Usage:
# app = FastAPI()
# add_security_headers(app)
# or with custom config:
# add_security_headers(app, SecurityHeadersConfig(...))
