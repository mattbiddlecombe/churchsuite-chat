from typing import Dict, Any
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from backend.security.models import BaseRequestModel, ChatRequest
import json
from datetime import datetime, timedelta

# Rate limiting constants
RATE_LIMIT_WINDOW = timedelta(minutes=1)
RATE_LIMIT_REQUESTS = 100

import logging

logger = logging.getLogger(__name__)

class InputValidationMiddleware(BaseHTTPMiddleware):
    """Middleware for input validation and sanitization"""

    def _sanitize_value(self, value: str) -> str:
        """Sanitize value by replacing dangerous characters to prevent XSS"""
        # Replace dangerous characters with HTML entities
        sanitized = value
        for char, entity in (
            ('<', '&lt;'),
            ('>', '&gt;'),
            ('"', '&quot;'),
            ("'", '&#39;')
        ):
            sanitized = sanitized.replace(char, entity)
        return sanitized

    def _validate_header(self, header: str, value: str) -> bool:
        """Validate HTTP header value"""
        # Sanitize header value
        sanitized = self._sanitize_value(value)
        if sanitized != value:
            return True
        return False

    def _validate_query_param(self, param: str, value: str) -> bool:
        """Validate query parameter value"""
        # Sanitize query parameter value
        sanitized = self._sanitize_value(value)
        if sanitized != value:
            logger.warning(f"Sanitized query parameter {param}: {value} -> {sanitized}")
            return True
        return False

    async def dispatch(self, request: Request, call_next):
        try:
            logger.info(f"Processing request: {request.method} {request.url.path}")
            logger.debug(f"Headers: {dict(request.headers)}")
            logger.debug(f"Query params: {dict(request.query_params)}")

            # Initialize session if not present
            session = request.scope.get('session', {})
            user_id = session.get('user_id')
            
            # Skip authentication check for auth endpoints
            if request.url.path.startswith('/auth/'):
                pass
            elif not user_id:
                # If this is a chat endpoint, return 401 with error message
                if request.url.path == '/chat':
                    return JSONResponse(
                        {"error": "Not authenticated"},
                        status_code=401
                    )
                # For other endpoints, return 400 with validation error
                return JSONResponse(
                    {"error": "Not authenticated"},
                    status_code=400
                )

            # Validate headers
            for header, value in request.headers.items():
                if self._validate_header(header, value):
                    logger.warning(f"Invalid header: {header}={value}")
                    return JSONResponse(
                        {"error": f"Invalid header: {header}"},
                        status_code=400
                    )

            # Validate query parameters
            for param, value in request.query_params.items():
                if self._validate_query_param(param, value):
                    logger.warning(f"Invalid query param: {param}={value}")
                    return JSONResponse(
                        {"error": f"Invalid query parameter: {param}"},
                        status_code=400
                    )

            # Handle JSON body if present
            if request.method in ["POST", "PUT", "PATCH"]:
                try:
                    if request.headers.get('content-type') == 'application/json':
                        logger.debug("Reading request body...")
                        # Get the body as a string
                        body = await request.json()
                        logger.debug(f"Parsed body: {body}")
                        
                        # Store the parsed body in request scope
                        request.scope["parsed_body"] = body
                        
                        # Only validate if we have a dictionary
                        if isinstance(body, dict):
                            logger.debug("Validating request body...")
                            # Try to validate with appropriate model
                            if request.url.path == '/chat':
                                logger.debug("Using ChatRequest model for validation")
                                ChatRequest(**body)
                            else:
                                logger.debug("Using BaseRequestModel for validation")
                                BaseRequestModel(**body)
                except json.JSONDecodeError as e:
                    logger.error(f"JSON decode error: {str(e)}")
                    return JSONResponse(
                        {"error": f"Invalid JSON: {str(e)}"},
                        status_code=400
                    )
                except Exception as e:
                    logger.error(f"Validation error: {str(e)}")
                    # Customize error message for Pydantic validation errors
                    if hasattr(e, 'errors') and callable(e.errors):
                        validation_errors = e.errors()
                        error_details = "\n".join([
                            f"{error['loc'][-1]}: {error['msg']}" 
                            for error in validation_errors
                        ])
                        return JSONResponse(
                            {"error": f"Invalid request body:\n{error_details}"},
                            status_code=400
                        )
                    return JSONResponse(
                        {"error": f"Invalid request body: {str(e)}"},
                        status_code=400
                    )
            
            logger.info("Request processing completed successfully")
            # Only proceed to next middleware if processing passed
            response = await call_next(request)
            
            return response
        except Exception as e:
            logger.error(f"Middleware error: {str(e)}", exc_info=True)
            return JSONResponse(
                {"error": f"Error processing request: {str(e)}"},
                status_code=400
            )

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        # Initialize rate limit storage
        self.rate_limit_storage = {}

    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for auth endpoints
        if request.url.path.startswith('/auth/'):
            return await call_next(request)
    
        # Get user ID from session or use IP
        user_id = request.session.get('user_id')
        if not user_id:
            user_id = request.client.host if request.client else 'unknown'
    
        # Create rate limit key
        key = f"rate_limit:{user_id}:{request.url.path}"
    
        # Get or create rate limit entry
        if key not in self.rate_limit_storage:
            self.rate_limit_storage[key] = {
                'count': 0,
                'reset_time': datetime.now() + RATE_LIMIT_WINDOW
            }
        
        entry = self.rate_limit_storage[key]
        now = datetime.now()
        if now >= entry['reset_time']:
            entry['count'] = 0
            entry['reset_time'] = now + RATE_LIMIT_WINDOW
    
        if entry['count'] >= RATE_LIMIT_REQUESTS:
            return JSONResponse({"error": "Rate limit exceeded. Please try again later."}, status_code=429)
    
        entry['count'] += 1
        return await call_next(request)

    async def cleanup(self):
        """Cleanup expired rate limit entries"""
        now = datetime.datetime.now()
        keys_to_remove = []
        
        for key, entry in self.rate_limit_storage.items():
            if now >= entry['reset_time']:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self.rate_limit_storage[key]
