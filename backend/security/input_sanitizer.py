from fastapi import FastAPI, Request, Response, HTTPException, Form
from fastapi.responses import JSONResponse
from typing import Dict, List, Optional, Any, Callable, Union
import logging
import re
from html import escape
from urllib.parse import quote
import json
from pydantic import BaseModel, Field, field_validator, ConfigDict

logger = logging.getLogger(__name__)

class XSSPatterns(BaseModel):
    """Common XSS patterns to detect"""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    script_tags: List[str] = Field(
        default_factory=lambda: [
            r'<script>.*?</script>',
            r'on\w+\s*=.*?',
            r'javascript:',
            r'eval\(',
            r'about:',
            r'data:',
            r'base64:'
        ],
        description="Patterns to detect script injection"
    )
    
    @field_validator('script_tags')
    def validate_xss_patterns(cls, patterns: List[str]) -> List[str]:
        if not isinstance(patterns, list):
            raise ValueError('Invalid XSS patterns: Must be a list of strings')
        
        for pattern in patterns:
            try:
                re.compile(pattern)
            except re.error as e:
                raise ValueError(f"Invalid XSS pattern: {pattern}") from e
        return patterns

class SQLInjectionPatterns(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    patterns: List[str] = Field(
        default_factory=lambda: [
            r'\b(SELECT|UPDATE|DELETE|DROP|INSERT|ALTER)\b',
            r'\bFROM\b.*\bWHERE\b.*\bOR\b.*=',
            r'\bUNION\b.*\bSELECT\b',
            r'\bDROP\b.*\bTABLE\b'
        ],
        description="Patterns to detect SQL injection"
    )
    
    @field_validator('patterns')
    def validate_patterns(cls, patterns: List[str]) -> List[str]:
        if not isinstance(patterns, list):
            raise ValueError('Invalid SQL injection patterns: Must be a list of strings')
        
        for pattern in patterns:
            if not isinstance(pattern, str):
                raise ValueError(f"Invalid SQL injection pattern: {pattern}. Must be a string.")
            if len(pattern) == 0:
                raise ValueError(f"Invalid SQL injection pattern: {pattern}. Must not be empty.")
            try:
                re.compile(pattern)
            except re.error as e:
                raise ValueError(f"Invalid SQL pattern: {pattern}. Error: {e}") from e
        return patterns

def add_input_sanitizer(app: FastAPI):
    """Add input sanitizer middleware to the FastAPI app"""
    @app.middleware("http")
    async def input_sanitizer(request: Request, call_next):
        """Sanitize all incoming request inputs"""
        try:
            xss_patterns = request.app.state.xss_patterns
            sql_patterns = request.app.state.sql_patterns
            query_params = dict(request.query_params)
            if query_params:
                sanitized_query = sanitize_query_params(query_params, xss_patterns, sql_patterns)
                request.scope["query_string"] = f"?{sanitized_query}".encode("utf-8")
            headers = dict(request.headers)
            if headers:
                sanitized_headers = sanitize_headers(headers, xss_patterns, sql_patterns)
                request.scope["headers"] = [(k.encode(), v.encode()) for k, v in sanitized_headers.items()]
            if request.method in ["POST", "PUT", "PATCH"]:
                content_type = request.headers.get("Content-Type", "")
                if "application/json" in content_type:
                    await sanitize_json_body(request, xss_patterns, sql_patterns)
                elif "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
                    await sanitize_form_data(request, xss_patterns, sql_patterns)
            response = await call_next(request)
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["X-XSS-Protection"] = "1; mode=block"
            response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'"
            return response
        except ValueError as e:
            error_message = str(e)
            logger.error(f"Input sanitization error: {error_message}", exc_info=True)
            return JSONResponse(
                status_code=400,
                content={"detail": error_message}
            )
        except Exception as e:
            logger.error(f"Unexpected error in input sanitizer: {str(e)}", exc_info=True)
            return JSONResponse(
                status_code=400,
                content={"detail": "Invalid input"}
            )

def sanitize_query_params(params: Dict[str, str], xss_patterns: XSSPatterns, sql_patterns: SQLInjectionPatterns) -> str:
    """Sanitize query parameters"""
    if not params:
        return ""
    
    sanitized_params = []
    for key, value in params.items():
        if value == "":
            sanitized_params.append(f"{key}=")
            continue
        
        if any(re.search(pattern, key, re.IGNORECASE) for pattern in xss_patterns.script_tags) or \
           any(re.search(pattern, value, re.IGNORECASE) for pattern in xss_patterns.script_tags):
            raise ValueError("Invalid input detected in query parameter")
        if any(re.search(pattern, value, re.IGNORECASE) for pattern in sql_patterns.patterns):
            raise ValueError("Invalid input detected in query parameter")
        sanitized_value = escape(value)
        sanitized_params.append(f"{key}={sanitized_value}")
    return "&".join(sanitized_params)

def sanitize_headers(headers: Dict[str, str], xss_patterns: XSSPatterns, sql_patterns: SQLInjectionPatterns) -> Dict[str, str]:
    """Sanitize headers"""
    if not headers:
        return {}
    
    sanitized_headers = {}
    for key, value in headers.items():
        # Skip security-sensitive headers
        if key.lower() in ['authorization', 'cookie', 'x-csrf-token']:
            sanitized_headers[key] = value
            continue
        
        if any(re.search(pattern, key, re.IGNORECASE) for pattern in xss_patterns.script_tags) or \
           any(re.search(pattern, value, re.IGNORECASE) for pattern in xss_patterns.script_tags):
            raise ValueError("Invalid input detected in header")
        if any(re.search(pattern, value, re.IGNORECASE) for pattern in sql_patterns.patterns):
            raise ValueError("Invalid input detected in header")
        sanitized_headers[key] = escape(value)
    return sanitized_headers

async def sanitize_form_data(request: Request, xss_patterns: XSSPatterns, sql_patterns: SQLInjectionPatterns):
    """Sanitize form data request body"""
    try:
        # Get form data
        form_data = await request.form()
        
        # Convert form data to dictionary
        data = {key: value for key, value in form_data.items()}
        
        # Sanitize the data
        sanitized_data = sanitize_dict(data, xss_patterns, sql_patterns)
        
        # Replace the request body with sanitized data
        request.scope["_body"] = json.dumps(sanitized_data).encode("utf-8")
        
        # Update form data in request scope
        request.scope["form_data"] = sanitized_data
    except Exception as e:
        logger.error(f"Error sanitizing form data: {str(e)}", exc_info=True)
        raise ValueError("Invalid form data")

async def sanitize_json_body(request: Request, xss_patterns: XSSPatterns, sql_patterns: SQLInjectionPatterns):
    """Sanitize JSON request body"""
    try:
        # Get the request body
        body = await request.body()
        
        # Parse JSON
        data = json.loads(body)
        
        # Sanitize the data
        sanitized_data = sanitize_dict(data, xss_patterns, sql_patterns)
        
        # Replace the request body with sanitized data
        request.scope["_body"] = json.dumps(sanitized_data).encode("utf-8")
    except json.JSONDecodeError:
        raise ValueError("Invalid JSON in request body")
    except ValueError as e:
        logger.error(f"Error sanitizing JSON body: {str(e)}", exc_info=True)
        raise
    except Exception as e:
        logger.error(f"Unexpected error sanitizing JSON body: {str(e)}", exc_info=True)
        raise ValueError("Invalid JSON data")

async def sanitize_form_body(request: Request, xss_patterns: XSSPatterns, sql_patterns: SQLInjectionPatterns):
    """Sanitize form-encoded request body"""
    try:
        # Get the form data
        form = await request.form()
        sanitized_form = {}
        for key, value in form.items():
            # Sanitize both key and value
            sanitized_key = escape(quote(str(key)))
            sanitized_value = escape(quote(str(value)))
            sanitized_form[sanitized_key] = sanitized_value
        
        # Convert back to URL-encoded form data
        request._body = '&'.join(f'{k}={v}' for k, v in sanitized_form.items()).encode()
    except Exception as e:
        logger.error(f"Error sanitizing form data: {str(e)}", exc_info=True)
        raise ValueError("Invalid form data")

def sanitize_dict(data: Dict, xss_patterns: XSSPatterns, sql_patterns: SQLInjectionPatterns) -> Dict:
    """Recursively sanitize dictionary values"""
    sanitized = {}
    for key, value in data.items():
        if isinstance(value, dict):
            sanitized[key] = sanitize_dict(value, xss_patterns, sql_patterns)
        elif isinstance(value, list):
            sanitized[key] = [sanitize_item(item, xss_patterns, sql_patterns) for item in value]
        else:
            sanitized[key] = sanitize_item(value, xss_patterns, sql_patterns)
    return sanitized

def sanitize_item(value: Any, xss_patterns: XSSPatterns, sql_patterns: SQLInjectionPatterns) -> Any:
    """Sanitize a single value"""
    if isinstance(value, str):
        return sanitize_text(value, xss_patterns, sql_patterns)
    elif isinstance(value, (int, float, bool, type(None))):
        return value
    elif isinstance(value, (list, dict)):
        return sanitize_dict(value, xss_patterns, sql_patterns)
    else:
        return str(value)

def sanitize_text(text: str, xss_patterns: XSSPatterns, sql_patterns: SQLInjectionPatterns) -> str:
    """Sanitize text for XSS and SQL injection"""
    # Check for XSS patterns
    for pattern in xss_patterns.script_tags:
        if re.search(pattern, text, re.IGNORECASE):
            raise ValueError("Potential XSS attack detected")
            
    # Check for SQL injection patterns
    for pattern in sql_patterns.patterns:
        if re.search(pattern, text, re.IGNORECASE):
            raise ValueError("Potential SQL injection detected")
            
    # HTML escape the text
    escaped = escape(text)
    
    # URL encode special characters
    return quote(escaped, safe='')
