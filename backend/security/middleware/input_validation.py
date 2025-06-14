from fastapi import FastAPI, Request, Response, HTTPException, status
from typing import Dict, Any
import logging
from datetime import datetime
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from backend.security.dependencies import validate_request, ENDPOINT_SCHEMAS

logger = logging.getLogger(__name__)

def input_validation_middleware(app: FastAPI):
    """Input validation middleware."""
    @app.middleware("http")
    async def dispatch(request: Request, call_next):
        """Middleware dispatch method."""
        try:
            logger.debug(f"Processing request to {request.url.path}")
            logger.debug(f"Request method: {request.method}")
            
            # Skip validation for auth endpoints
            if request.url.path in ['/auth/start', '/auth/callback', '/auth/refresh']:
                response = await call_next(request)
                return response
            
            # Parse request body or query params
            try:
                if request.method in ['POST', 'PUT', 'PATCH']:
                    body = await request.json()
                else:
                    body = dict(request.query_params)
            except Exception as parse_error:
                logger.error(f"Error parsing request body: {str(parse_error)}", exc_info=True)
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={
                        "detail": "Invalid request data",
                        "error": f"Failed to parse request: {str(parse_error)}"
                    }
                )
            
            # Validate request
            try:
                validated_data = validate_request(
                    request_body=body,
                    endpoint=request.url.path,
                    skip_validation=False
                )
                request.state.validated_data = validated_data
                response = await call_next(request)
                return response
            except ValidationError as validation_error:
                logger.error(f"Validation error for endpoint {request.url.path}: {validation_error.errors()}", exc_info=True)
                error_details = []
                for error in validation_error.errors():
                    error_details.append({
                        "loc": error["loc"],
                        "msg": error["msg"],
                        "type": error["type"]
                    })
                return JSONResponse(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    content={
                        "detail": "Validation error",
                        "errors": error_details
                    }
                )
            except Exception as validation_error:
                logger.error(f"Validation error: {str(validation_error)}", exc_info=True)
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={
                        "detail": "Invalid request data",
                        "error": str(validation_error)
                    }
                )
            
            # If we get here, request should be allowed
            response = await call_next(request)
            return response
            
        except Exception as e:
            logger.error(f"Input validation error: {str(e)}", exc_info=True)
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "detail": "Internal server error",
                    "error": str(e)
                }
            )
