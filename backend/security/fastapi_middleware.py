from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from typing import Callable, List
import logging

logger = logging.getLogger(__name__)

def setup_fastapi_middleware(app: FastAPI) -> None:
    """Configure FastAPI middleware stack with proper security headers, CORS, and audit logging"""
    # Add audit middleware
    app.middleware("http")(AuditMiddleware())
    
    # Add security headers middleware
    app.middleware("http")(security_headers)
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
        max_age=600
    )

async def security_headers(request: Request, call_next: Callable) -> Response:
    """Middleware to add comprehensive security headers to all responses"""
    try:
        # Handle CORS preflight requests
        if request.method == "OPTIONS":
            response = Response(content="", status_code=200)
            response.headers["Access-Control-Allow-Origin"] = "*"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "content-type, authorization, x-csrf-token"
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Expose-Headers"] = "content-type, authorization, x-csrf-token"
            return response

        response = await call_next(request)
        
        # Content Security Policy (CSP)
        response.headers["Content-Security-Policy"] = \
            "default-src 'self'; " \
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net; " \
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; " \
            "img-src 'self' data: https:; " \
            "connect-src 'self' https://api.openai.com; " \
            "font-src 'self' https: data:; " \
            "object-src 'none'; " \
            "frame-src 'none'; " \
            "form-action 'self'; " \
            "base-uri 'self'; " \
            "manifest-src 'self'; " \
            "media-src 'self'; " \
            "worker-src 'self' blob:; " \
            "frame-ancestors 'none'; " \
            "block-all-mixed-content"
        
        # Security Headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["X-Permitted-Cross-Domain-Policies"] = "none"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        # CORS Headers
        origin = request.headers.get("origin", "*")
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Headers"] = "content-type, authorization, x-csrf-token"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        response.headers["Access-Control-Expose-Headers"] = "content-type, authorization, x-csrf-token"
        
        # Cache Control
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        
        return response
        
    except Exception as e:
        logger.error(f"Error in security middleware: {str(e)}", exc_info=True)
        raise
