from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp, Receive, Scope, Send
from typing import Dict, Optional, Any, Callable
import logging
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel, Field, validator
import secrets
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)

class CookieConfig(BaseModel):
    """Configuration for secure cookies"""
    session_cookie_name: str = Field(default="session_id", description="Name of the session cookie")
    csrf_cookie_name: str = Field(default="csrf_token", description="Name of the CSRF token cookie")
    
    # Security flags
    secure: bool = Field(default=True, description="Whether cookies should only be sent over HTTPS")
    httponly: bool = Field(default=True, description="Whether cookies should be inaccessible to JavaScript")
    samesite: str = Field(default="Strict", description="Cookie SameSite policy")
    
    # Expiration settings
    session_lifetime: int = Field(default=3600, description="Session cookie lifetime in seconds")
    csrf_lifetime: int = Field(default=3600, description="CSRF token lifetime in seconds")
    
    # Domain settings
    domain: Optional[str] = Field(default=None, description="Domain to set cookies for")
    path: str = Field(default="/", description="Path for which cookies are valid")
    
    @validator('samesite')
    def validate_samesite(cls, v):
        """Validate SameSite value"""
        if v not in ['Strict', 'Lax', 'None']:
            raise ValueError('SameSite must be one of: Strict, Lax, None')
        return v

class SecureCookieMiddleware(BaseHTTPMiddleware):
    """Middleware to handle secure cookie management"""
    
    def __init__(self, app: ASGIApp, config: Optional[CookieConfig] = None):
        super().__init__(app)
        self.config = config or CookieConfig()
        self._cookie_config = self._build_cookie_config()
        
    def _build_cookie_config(self) -> Dict[str, Dict[str, Any]]:
        """Build cookie configuration dictionary"""
        return {
            'session': {
                'name': self.config.session_cookie_name,
                'lifetime': self.config.session_lifetime,
                'secure': self.config.secure,
                'httponly': self.config.httponly,
                'samesite': self.config.samesite,
                'domain': self.config.domain,
                'path': self.config.path
            },
            'csrf': {
                'name': self.config.csrf_cookie_name,
                'lifetime': self.config.csrf_lifetime,
                'secure': self.config.secure,
                'httponly': False,  # CSRF token needs to be accessible to JavaScript
                'samesite': self.config.samesite,
                'domain': self.config.domain,
                'path': self.config.path
            }
        }
    
    async def dispatch(self, request: Request, call_next: Callable):
        """Handle cookie management"""
        try:
            # Generate CSRF token if not present
            csrf_token = request.cookies.get(self.config.csrf_cookie_name)
            if not csrf_token:
                csrf_token = secrets.token_urlsafe(32)
                request.state.csrf_token = csrf_token
            
            response = await call_next(request)
            
            # Set or update cookies
            self._set_cookies(response)
            
            return response
            
        except Exception as e:
            logger.error(f"Cookie handling error: {str(e)}", exc_info=True)
            return JSONResponse(
                {"error": "Internal server error", "detail": str(e)},
                status_code=500
            )
    
    def _set_cookies(self, response: Response):
        """Set secure cookies on the response"""
        # Set session cookie
        session_id = secrets.token_urlsafe(32)
        self._set_cookie(
            response,
            self._cookie_config['session']['name'],
            session_id,
            self._cookie_config['session']
        )
        
        # Set CSRF cookie
        if hasattr(response.request, 'state') and hasattr(response.request.state, 'csrf_token'):
            csrf_token = response.request.state.csrf_token
            self._set_cookie(
                response,
                self._cookie_config['csrf']['name'],
                csrf_token,
                self._cookie_config['csrf']
            )
    
    def _set_cookie(self, response: Response, name: str, value: str, config: Dict[str, Any]):
        """Set a secure cookie"""
        expires = datetime.now(timezone.utc) + timedelta(seconds=config['lifetime'])
        
        response.set_cookie(
            key=name,
            value=value,
            max_age=config['lifetime'],
            expires=expires,
            path=config['path'],
            domain=config['domain'],
            secure=config['secure'],
            httponly=config['httponly'],
            samesite=config['samesite'],
            # Add additional security headers
            **{
                'SameSite': config['samesite'],
                'HttpOnly': str(config['httponly']).lower(),
                'Secure': str(config['secure']).lower()
            }
        )
    
    def clear_cookies(self, response: Response):
        """Clear all cookies"""
        for cookie_type in self._cookie_config:
            config = self._cookie_config[cookie_type]
            response.delete_cookie(
                key=config['name'],
                path=config['path'],
                domain=config['domain']
            )
    
    @staticmethod
    def validate_cookie(request: Request, cookie_name: str) -> bool:
        """Validate a cookie's security properties"""
        cookie = request.cookies.get(cookie_name)
        if not cookie:
            return False
            
        # Check for common security issues
        if len(cookie) < 32:  # Minimum secure length
            return False
            
        # Check for unsafe characters
        if not re.match(r'^[a-zA-Z0-9-_]+$', cookie):
            return False
            
        return True
    
    @staticmethod
    def get_csrf_token(request: Request) -> Optional[str]:
        """Get the CSRF token from the request"""
        return getattr(request.state, 'csrf_token', None)
    
    @staticmethod
    def validate_csrf_token(request: Request, token: str) -> bool:
        """Validate a CSRF token"""
        stored_token = SecureCookieMiddleware.get_csrf_token(request)
        if not stored_token:
            return False
            
        return secrets.compare_digest(stored_token, token)
    
    @staticmethod
    def generate_csrf_token() -> str:
        """Generate a new CSRF token"""
        return secrets.token_urlsafe(32)
