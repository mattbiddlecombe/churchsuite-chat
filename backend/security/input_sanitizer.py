from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp, Receive, Scope, Send
from typing import Dict, List, Optional, Any, Callable
import logging
from pydantic import BaseModel, Field, validator
import re
from html import escape
import json
from urllib.parse import quote
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)

class XSSPatterns(BaseModel):
    """Common XSS patterns to detect and sanitize"""
    script_tags: List[str] = Field(
        default_factory=lambda: [
            r'<script[^>]*?>.*?</script>',
            r'on\w+\s*=\s*["\'].*?["\']',
            r'javascript:',
            r'eval\(',
            r'expression\(',
            r'vbscript:',
            r'jscript:',
            r'wscript:',
            r'vbs:',
            r'about:',
            r'data:',
            r'base64:'
        ],
        description="Patterns to detect script injection"
    )
    
    @validator('script_tags')
    def validate_patterns(cls, v):
        """Validate that patterns are valid regex patterns"""
        for pattern in v:
            try:
                re.compile(pattern)
            except re.error:
                raise ValueError(f'Invalid regex pattern: {pattern}')
        return v

class SQLInjectionPatterns(BaseModel):
    """Common SQL injection patterns to detect"""
    patterns: List[str] = Field(
        default_factory=lambda: [
            r'\b(SELECT|UPDATE|DELETE|DROP|INSERT|ALTER)\b',
            r'\b(AND|OR)\s*1=1',
            r'\b(AND|OR)\s*\d=\d',
            r'\bLIKE\s*%\w+%',
            r'\bIN\s*\([^)]*\)',
            r'\bIN\s*\(\s*\)',
            r'\bIN\s*\(\s*NULL\s*\)',
            r'\bIN\s*\(\s*0\s*\)',
            r'\bIN\s*\(\s*1\s*\)'
        ],
        description="Patterns to detect SQL injection"
    )
    
    @validator('patterns')
    def validate_patterns(cls, v):
        """Validate that patterns are valid regex patterns"""
        for pattern in v:
            try:
                re.compile(pattern)
            except re.error:
                raise ValueError(f'Invalid regex pattern: {pattern}')
        return v

class InputSanitizerMiddleware(BaseHTTPMiddleware):
    """Middleware to sanitize input and prevent XSS/SQL injection"""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.xss_patterns = XSSPatterns()
        self.sql_patterns = SQLInjectionPatterns()
        
    async def dispatch(self, request: Request, call_next: Callable):
        """Sanitize input and prevent XSS/SQL injection"""
        try:
            # Sanitize query parameters
            sanitized_query = self.sanitize_query_params(request.query_params)
            request.scope['query_string'] = sanitized_query
            
            # Sanitize headers
            sanitized_headers = self.sanitize_headers(request.headers)
            request.scope['headers'] = [(k.encode(), v.encode()) for k, v in sanitized_headers.items()]
            
            # Sanitize body for POST/PUT requests
            if request.method in ['POST', 'PUT']:
                content_type = request.headers.get('content-type', '').lower()
                if 'application/json' in content_type:
                    await self.sanitize_json_body(request)
                elif 'application/x-www-form-urlencoded' in content_type:
                    await self.sanitize_form_body(request)
                
            response = await call_next(request)
            return response
            
        except Exception as e:
            logger.error(f"Input sanitization error: {str(e)}", exc_info=True)
            return JSONResponse(
                {"error": "Invalid input", "detail": str(e)},
                status_code=400
            )
    
    def sanitize_query_params(self, params: Dict[str, str]) -> Dict[str, str]:
        """Sanitize query parameters"""
        sanitized = {}
        for key, value in params.items():
            sanitized[key] = self.sanitize_text(value)
        return sanitized
    
    def sanitize_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        """Sanitize headers"""
        sanitized = {}
        for key, value in headers.items():
            # Skip security-sensitive headers
            if key.lower() in ['authorization', 'cookie', 'x-csrf-token']:
                sanitized[key] = value
                continue
            sanitized[key] = self.sanitize_text(value)
        return sanitized
    
    async def sanitize_json_body(self, request: Request):
        """Sanitize JSON request body"""
        body = await request.body()
        try:
            data = json.loads(body)
            sanitized_data = self.sanitize_dict(data)
            request._body = json.dumps(sanitized_data).encode()
        except json.JSONDecodeError:
            raise ValueError("Invalid JSON in request body")
    
    async def sanitize_form_body(self, request: Request):
        """Sanitize form-encoded request body"""
        body = await request.body()
        try:
            data = {}
            for pair in body.decode().split('&'):
                if '=' in pair:
                    key, value = pair.split('=', 1)
                    data[key] = self.sanitize_text(quote(value))
            request._body = '&'.join(f'{k}={v}' for k, v in data.items()).encode()
        except Exception:
            raise ValueError("Invalid form data")
    
    def sanitize_dict(self, data: Dict) -> Dict:
        """Recursively sanitize dictionary values"""
        sanitized = {}
        for key, value in data.items():
            if isinstance(value, dict):
                sanitized[key] = self.sanitize_dict(value)
            elif isinstance(value, list):
                sanitized[key] = [self.sanitize_item(item) for item in value]
            else:
                sanitized[key] = self.sanitize_item(value)
        return sanitized
    
    def sanitize_item(self, value: Any) -> Any:
        """Sanitize a single value"""
        if isinstance(value, str):
            return self.sanitize_text(value)
        elif isinstance(value, (int, float, bool, type(None))):
            return value
        elif isinstance(value, (list, dict)):
            return self.sanitize_dict(value)
        else:
            return str(value)
    
    def sanitize_text(self, text: str) -> str:
        """Sanitize text for XSS and SQL injection"""
        # Check for XSS patterns
        for pattern in self.xss_patterns.script_tags:
            if re.search(pattern, text, re.IGNORECASE):
                raise ValueError("Potential XSS attack detected")
                
        # Check for SQL injection patterns
        for pattern in self.sql_patterns.patterns:
            if re.search(pattern, text, re.IGNORECASE):
                raise ValueError("Potential SQL injection detected")
                
        # HTML escape the text
        escaped = escape(text)
        
        # URL encode special characters
        return quote(escaped, safe='')
