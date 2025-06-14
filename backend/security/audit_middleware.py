from fastapi import Request, Response
import logging
import uuid
from datetime import datetime
from typing import Callable

from backend.config.logging import get_audit_logger

audit_logger = get_audit_logger()

async def audit_middleware(request: Request, call_next: Callable) -> Response:
    """Middleware to log security-relevant events"""
    try:
        # Generate request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        # Log request event with all fields
        audit_logger.info(
            "Request received",
            extra={
                "event_type": "request",
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "client": request.client.host if request.client else "-",
                "headers": dict(request.headers),
                "user_id": getattr(request.state, "user_id", "-"),
                "timestamp": datetime.utcnow().isoformat()
            }
        )

        # Process the request
        response = await call_next(request)

        # Log response event with all fields
        audit_logger.info(
            "Response sent",
            extra={
                "event_type": "response",
                "request_id": request_id,
                "status_code": response.status_code,
                "timestamp": datetime.utcnow().isoformat()
            }
        )

        return response

    except Exception as e:
        # Log error event with all fields
        audit_logger.error(
            "Request processing error",
            extra={
                "event_type": "error",
                "request_id": getattr(request.state, "request_id", "-"),
                "method": request.method,
                "path": request.url.path,
                "error_type": type(e).__name__,
                "error_message": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        raise
