import re
from typing import Optional, Dict, Any, Callable, Awaitable
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp, Receive, Scope, Send, Message
from starlette.requests import Request
from starlette.responses import FileResponse, Response
from datetime import datetime, timedelta, timezone
import logging
from pydantic import BaseModel, Field, validator

logger = logging.getLogger(__name__)

class SecurityHeadersConfig(BaseModel):
    """Configuration for security headers"""
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
    
    @validator('content_security_policy')
    def validate_csp(cls, v):
        """Validate Content Security Policy format"""
        if not v.startswith('default-src'):
            raise ValueError('CSP must start with default-src')
        return v

    @validator('strict_transport_security')
    def validate_hsts(cls, v):
        """Validate HSTS format"""
        if not re.match(r'^max-age=\d+(?:;\s*includeSubDomains)?$', v):
            raise ValueError('Invalid HSTS format')
        return v


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to responses"""
    
    def __init__(self, app: ASGIApp, config: Optional[SecurityHeadersConfig] = None):
        super().__init__(app)
        self.config = config or SecurityHeadersConfig()
        self._last_config_update = datetime.now(timezone.utc)
        
    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Create send wrapper to add security headers
        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                existing_headers = message.get("headers", [])
                security_headers = [
                    [b"content-type", b"application/json"],
                    [b"x-content-type-options", b"nosniff"],
                    [b"x-frame-options", b"DENY"],
                    [b"x-xss-protection", b"1; mode=block"],
                    [b"referrer-policy", b"strict-origin-when-cross-origin"],
                    [b"content-security-policy", b"default-src 'self'"],
                    [b"x-permitted-cross-domain-policies", b"none"],
                    [b"strict-transport-security", b"max-age=31536000; includeSubDomains"],
                    [b"cache-control", b"no-cache, no-store, must-revalidate"],
                    [b"pragma", b"no-cache"],
                    [b"expires", b"0"],
                    [b"access-control-allow-origin", b"*"],
                    [b"access-control-allow-credentials", b"true"],
                    [b"access-control-allow-headers", b"content-type, authorization, x-csrf-token"],
                    [b"access-control-allow-methods", b"GET, POST, PUT, DELETE, OPTIONS"]
                ]
                message["headers"] = existing_headers + security_headers
            await send(message)

        await self.app(scope, receive, send_wrapper)

    @staticmethod
    def get_default_headers() -> Dict[str, str]:
        """Get default security headers configuration"""
        return {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; frame-ancestors 'none'",
            "X-Permitted-Cross-Domain-Policies": "none",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains"
        }

    @staticmethod
    def get_api_headers() -> Dict[str, str]:
        """Get additional security headers for API endpoints"""
        return {
            "X-API-Version": "1.0",
            "X-Rate-Limit-Limit": "60",
            "X-Rate-Limit-Remaining": "59",
            "X-Rate-Limit-Reset": str(int((datetime.now(timezone.utc) + timedelta(minutes=1)).timestamp()))
        }

    @staticmethod
    def get_cors_headers() -> Dict[str, str]:
        """Get CORS-related security headers"""
        return {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "Authorization, Content-Type, X-CSRF-Token",
            "Access-Control-Max-Age": "86400"
        }

    @staticmethod
    def get_cache_headers() -> Dict[str, str]:
        """Get cache-related security headers"""
        return {
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0"
        }

    def update_config(self, config: SecurityHeadersConfig):
        """Update the security headers configuration"""
        self.config = config
        self._last_config_update = datetime.now(timezone.utc)
        logger.info(f"Security headers configuration updated at {self._last_config_update}")
