from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp, Receive, Scope, Send
from typing import Dict, Optional, Any, Callable, Type, List, Tuple
import logging
from pydantic import BaseModel, ValidationError, Field, validator
from starlette.requests import Request
from starlette.responses import JSONResponse
import re
from datetime import datetime
from typing import TypeVar

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=BaseModel)

class RequestValidationConfig(BaseModel):
    """Configuration for request validation"""
    # Validation settings
    strict_validation: bool = Field(default=True, description="Whether to enforce strict validation")
    allow_extra_fields: bool = Field(default=False, description="Whether to allow extra fields")
    
    # Error handling
    error_detail_level: str = Field(default="high", description="Level of error detail (low, medium, high)")
    error_status_code: int = Field(default=400, description="HTTP status code for validation errors")
    
    # Rate limiting
    max_validation_errors: int = Field(default=10, description="Maximum number of validation errors to return")
    
    @validator('error_detail_level')
    def validate_error_level(cls, v):
        """Validate error detail level"""
        if v not in ['low', 'medium', 'high']:
            raise ValueError('Error detail level must be one of: low, medium, high')
        return v

class RequestValidatorMiddleware(BaseHTTPMiddleware):
    """Middleware to validate incoming requests"""
    
    def __init__(self, app: ASGIApp, config: Optional[RequestValidationConfig] = None):
        super().__init__(app)
        self.config = config or RequestValidationConfig()
        self._validation_schemas = {}
        
    def register_schema(self, endpoint: str, schema: Type[T]):
        """Register a validation schema for an endpoint"""
        self._validation_schemas[endpoint] = schema
        
    async def dispatch(self, request: Request, call_next: Callable):
        """Validate incoming request"""
        try:
            # Get validation schema for endpoint
            endpoint = request.url.path
            schema = self._validation_schemas.get(endpoint)
            
            # Skip validation if no schema is registered
            if not schema:
                return await call_next(request)
                
            # Validate request body
            content_type = request.headers.get('Content-Type', '')
            if 'application/json' in content_type:
                body = await request.json()
            else:
                body = await request.form()
            
            try:
                # Validate against schema
                validated_data = schema.parse_obj(body)
                request.state.validated_data = validated_data
                
            except ValidationError as e:
                # Handle validation errors
                errors = self._format_validation_errors(e.errors())
                return JSONResponse(
                    {
                        "error": "Validation failed",
                        "detail": errors,
                        "errors": len(e.errors())
                    },
                    status_code=self.config.error_status_code
                )
            
            response = await call_next(request)
            return response
            
        except Exception as e:
            logger.error(f"Request validation error: {str(e)}", exc_info=True)
            return JSONResponse(
                {"error": "Internal server error", "detail": str(e)},
                status_code=500
            )
    
    def _format_validation_errors(self, errors: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format validation errors based on config"""
        formatted_errors = []
        
        for error in errors[:self.config.max_validation_errors]:
            loc = ' -> '.join(str(loc) for loc in error['loc'])
            msg = error['msg']
            
            if self.config.error_detail_level == 'high':
                formatted_errors.append({
                    'field': loc,
                    'message': msg,
                    'type': error['type']
                })
            elif self.config.error_detail_level == 'medium':
                formatted_errors.append({
                    'field': loc,
                    'message': msg
                })
            else:  # low
                formatted_errors.append({
                    'field': loc
                })
        
        return formatted_errors
    
    @staticmethod
    def validate_request(request: Request, schema: Type[T]) -> T:
        """Validate a request against a schema"""
        if not hasattr(request.state, 'validated_data'):
            raise ValueError("Request not validated")
            
        return request.state.validated_data
    
    @staticmethod
    def get_validated_data(request: Request) -> Dict[str, Any]:
        """Get validated data from request state"""
        if not hasattr(request.state, 'validated_data'):
            return {}
            
        return request.state.validated_data.dict()
    
    @staticmethod
    def validate_query_params(request: Request, schema: Type[T]) -> T:
        """Validate query parameters against a schema"""
        try:
            return schema.parse_obj(request.query_params)
        except ValidationError as e:
            raise ValueError(f"Invalid query parameters: {str(e)}")
    
    @staticmethod
    def validate_headers(request: Request, schema: Type[T]) -> T:
        """Validate headers against a schema"""
        try:
            return schema.parse_obj(request.headers)
        except ValidationError as e:
            raise ValueError(f"Invalid headers: {str(e)}")
