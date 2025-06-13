from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp, Receive, Scope, Send
from typing import Dict, Optional, Any, Callable
import logging
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel, Field, validator
import secrets
from starlette.requests import Request
from starlette.responses import JSONResponse
import re
from typing import List
import json
from starlette.datastructures import Headers

def generate_csrf_token() -> str:
    """Generate a secure CSRF token"""
    return secrets.token_urlsafe(32)

logger = logging.getLogger(__name__)

class CSRFConfig(BaseModel):
    """Configuration for CSRF protection"""
    # Token generation
    token_length: int = Field(default=32, description="Length of CSRF token")
    token_bytes: int = Field(default=32, description="Number of bytes for token")
    
    # Header names
    header_name: str = Field(default="X-CSRF-Token", description="Header name for CSRF token")
    cookie_name: str = Field(default="csrf_token", description="Cookie name for CSRF token")
    
    # Request methods to protect
    protected_methods: List[str] = Field(
        default_factory=lambda: ['POST', 'PUT', 'DELETE', 'PATCH'],
        description="HTTP methods to protect"
    )
    
    # Expiration settings
    token_lifetime: int = Field(default=3600, description="Token lifetime in seconds")
    
    # Validation settings
    strict_token_validation: bool = Field(default=True, description="Whether to strictly validate tokens")
    
    @validator('protected_methods')
    def validate_methods(cls, v):
        """Validate HTTP methods"""
        valid_methods = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS', 'HEAD']
        for method in v:
            if method.upper() not in valid_methods:
                raise ValueError(f'Invalid HTTP method: {method}')
        return [method.upper() for method in v]

class CSRFProtectionMiddleware(BaseHTTPMiddleware):
    """Middleware to protect against CSRF attacks"""
    
    def __init__(self, app: ASGIApp, config: Optional[CSRFConfig] = None):
        super().__init__(app)
        self.config = config or CSRFConfig()
        self._token_pattern = re.compile(r'^[a-zA-Z0-9-_]+$')
        
    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope)
        
        # Generate CSRF token for GET requests
        if request.method == "GET":
            csrf_token = self.generate_csrf_token()
            request.state.csrf_token = csrf_token
            
            # Create wrapper for send to add headers and cookies
            async def send_wrapper(message: dict) -> None:
                if message["type"] == "http.response.start":
                    message["headers"] = [
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
                        [b"x-csrf-token", csrf_token.encode()],
                        [b"set-cookie", f"csrf_token={csrf_token}; httponly; secure; samesite=lax; path=/".encode()],
                    ]
                await send(message)
            
            await self.app(scope, receive, send_wrapper)
            return

        # Validate CSRF token for non-GET requests
        csrf_header = request.headers.get("x-csrf-token")
        if not csrf_header:
            logger.error("Missing CSRF token in header")
            await send({
                "type": "http.response.start",
                "status": 403,
                "headers": [
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
                ],
            })
            await send({
                "type": "http.response.body",
                "body": json.dumps({"detail": "CSRF validation failed", "error": "Missing CSRF token"}).encode(),
            })
            return

        # Get CSRF token from cookies
        cookie_csrf = request.cookies.get("csrf_token")
        if not cookie_csrf:
            logger.error("Missing CSRF token in cookie")
            await send({
                "type": "http.response.start",
                "status": 403,
                "headers": [
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
                ],
            })
            await send({
                "type": "http.response.body",
                "body": json.dumps({"detail": "CSRF validation failed", "error": "Missing CSRF token"}).encode(),
            })
            return

        # Validate token format
        if not self._is_valid_token_format(csrf_header) or not self._is_valid_token_format(cookie_csrf):
            logger.error("Invalid CSRF token format")
            await send({
                "type": "http.response.start",
                "status": 403,
                "headers": [
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
                ],
            })
            await send({
                "type": "http.response.body",
                "body": json.dumps({"detail": "CSRF validation failed", "error": "Invalid token format"}).encode(),
            })
            return

        # Compare tokens
        if csrf_header != cookie_csrf:
            logger.error("CSRF token mismatch")
            await send({
                "type": "http.response.start",
                "status": 403,
                "headers": [
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
                ],
            })
            await send({
                "type": "http.response.body",
                "body": json.dumps({"detail": "CSRF validation failed", "error": "Tokens do not match"}).encode(),
            })
            return

        # Create wrapper for send to add CSRF token to cookies
        async def send_wrapper(message: dict) -> None:
            if message["type"] == "http.response.start":
                # Add CSRF token to cookies
                message["headers"].append(
                    [b"set-cookie", f"csrf_token={csrf_header}; httponly; secure; samesite=lax".encode()]
                )
            await send(message)
        
        await self.app(scope, receive, send_wrapper)
    
    def _generate_csrf_token(self) -> str:
        """Generate a secure CSRF token"""
        return secrets.token_urlsafe(self.config.token_bytes)
    
    def _is_valid_token_format(self, token: str) -> bool:
        """Validate token format"""
        if not isinstance(token, str):
            return False
            
        # Check length
        if len(token) < self.config.token_length:
            return False
            
        # Check format
        if not self._token_pattern.match(token):
            return False
            
        return True
    
    @staticmethod
    def get_csrf_token(request: Request) -> Optional[str]:
        """Get CSRF token from request state"""
        return getattr(request.state, 'csrf_token', None)
    
    @staticmethod
    def set_csrf_token(request: Request, token: str):
        """Set CSRF token in response headers"""
        headers = Headers(scope=request.scope)
        headers.raw.append([b"X-CSRF-Token", token.encode()])
    
    @staticmethod
    def generate_csrf_token() -> str:
        """Generate a new CSRF token"""
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def validate_token(token: str) -> bool:
        """Validate token format and security"""
        if not isinstance(token, str):
            return False
            
        # Check for common vulnerabilities
        if len(token) < 32:  # Minimum secure length
            return False
            
        # Check for unsafe characters
        if not re.match(r'^[a-zA-Z0-9-_]+$', token):
            return False
            
        # Check for predictable patterns
        if re.search(r'^(\d+|\w+|[-_]+)$', token):
            return False
            
        return True
