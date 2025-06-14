from typing import Type, Dict, Any, Optional
from fastapi import Depends, HTTPException, status
from pydantic import BaseModel, ValidationError
from backend.schemas.requests import (
    ChatRequest,
    AuthRequest,
    TokenRefreshRequest,
    RateLimitRequest
)
import logging

logger = logging.getLogger(__name__)

# Define endpoint schemas
ENDPOINT_SCHEMAS: Dict[str, Type[BaseModel]] = {
    '/chat': ChatRequest,
    '/auth/start': AuthRequest,
    '/auth/callback': AuthRequest,
    '/auth/refresh': TokenRefreshRequest,
    '/test/rate-limit': RateLimitRequest
}

def validate_request(
    request_body: Dict[str, Any],
    endpoint: str,
    skip_validation: bool = False
) -> Dict[str, Any]:
    """Validate request data against appropriate schema."""
    try:
        if skip_validation:
            return request_body

        schema = ENDPOINT_SCHEMAS.get(endpoint)
        if not schema:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No validation schema defined for endpoint: {endpoint}"
            )

        # Validate the request data
        validated_data = schema(**request_body)
        return validated_data.dict()
    except ValidationError as e:
        logger.error(f"Validation error for endpoint {endpoint}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error validating request for endpoint {endpoint}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to validate request"
        )
