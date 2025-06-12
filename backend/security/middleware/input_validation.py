from typing import Callable, Awaitable, Dict, Any, Optional
from starlette.responses import JSONResponse
from backend.schemas.responses import ErrorResponse
import logging
from pydantic import ValidationError
from backend.schemas.requests import (
    ChatRequest,
    AuthRequest,
    TokenRefreshRequest,
    RateLimitRequest
)
from backend.tests.test_utils import MockRequest

logger = logging.getLogger(__name__)

# Define endpoint schemas
ENDPOINT_SCHEMAS = {
    '/chat': ChatRequest,
    '/auth/start': AuthRequest,
    '/auth/callback': AuthRequest,
    '/auth/refresh': TokenRefreshRequest,
    '/test/rate-limit': RateLimitRequest
}

class InputValidationMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = MockRequest(
            method=scope.get('method', 'GET'),
            url_path=scope.get('path', '/'),
            headers=scope.get('headers', {}),
            query_params=dict(scope.get('query_string', {}).items()),
            state=scope.get('state', {}),
            scope=scope
        )
        response = await self.dispatch(request, self.app)
        await response(scope, receive, send)

    async def dispatch(self, request: MockRequest, app) -> JSONResponse:
        """Middleware dispatch method."""
        try:
            logger.debug(f"Processing request to {request.url_path}")
            logger.debug(f"Request method: {request.method}")
            logger.debug(f"Request state: {dict(request.state)}")  # Convert state to dict for logging
            logger.debug(f"Request query params: {dict(request.query_params)}")
            logger.debug(f"Headers: {dict(request.headers)}")

            # Skip validation and authentication for auth endpoints
            if request.url.path in ['/auth/start', '/auth/callback', '/auth/refresh']:
                logger.debug(f"Skipping validation and auth for auth endpoint: {request.url.path}")
                logger.debug(f"State after skipping: {dict(request.state)}")
                # For auth endpoints, just pass through without any checks
                return JSONResponse(
                    {
                        "message": "success",
                        "error": None,
                        "detail": None
                    },
                    status_code=200
                )

            # Get the appropriate schema for this endpoint
            schema = ENDPOINT_SCHEMAS.get(request.url.path)
            if not schema:
                logger.debug(f"No schema found for endpoint: {request.url.path}")
                return JSONResponse(
                    {
                        "error": "No validation schema found",
                        "detail": f"No validation schema defined for endpoint: {request.url.path}"
                    },
                    status_code=400
                )

            # Get the request body or query parameters based on request method
            try:
                if request.method in ['POST', 'PUT', 'PATCH']:
                    body = await request.json()
                else:
                    body = request.query_params
            except Exception as e:
                logger.debug(f"Error parsing request body: {str(e)}")
                return JSONResponse(
                    {
                        "error": "Invalid request",
                        "detail": f"Failed to parse request body: {str(e)}"
                    },
                    status_code=400
                )

            # Validate the request data
            try:
                if isinstance(schema, type) and issubclass(schema, BaseModel):
                    # If schema is a Pydantic model
                    validated_data = schema(**body)
                    logger.debug(f"Validation successful: {validated_data}")
                else:
                    # If schema is a callable validator
                    validated_data = schema(body)
                    logger.debug(f"Validation successful: {validated_data}")
            except ValidationError as e:
                logger.debug(f"Validation error: {str(e)}")
                return JSONResponse(
                    {
                        "error": "Validation error",
                        "detail": e.errors()
                    },
                    status_code=400
                )
                    return JSONResponse(
                        ErrorResponse(
                            error="Not authenticated",
                            detail="Invalid user information"
                        ).dict(),
                        status_code=401
                    )
                logger.debug(f"Authentication passed for endpoint: {request.url.path}")
                # For authenticated requests, add user to request state
                request.state.user = user
                return await app(request.scope, request.receive, request.send)

            logger.debug(f"Request passed all checks for endpoint: {request.url.path}")
            # If we get here, validation has passed
            return await app(request.scope, request.receive, request.send)

        except Exception as e:
            logger.error(f"Input validation error: {str(e)}", exc_info=True)
            return JSONResponse(
                ErrorResponse(
                    error="Internal server error",
                    detail=str(e)
                ).dict(),
                status_code=500
            )
