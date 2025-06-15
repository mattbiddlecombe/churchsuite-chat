import os
from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from backend.config import settings
from backend.routers import churchsuite, chat
from backend.security.jwt_middleware_native import JWTMiddleware, get_current_user
from backend.endpoints.rate_limit import RateLimitMiddleware, RedisDependency, RateLimitConfig
from backend.security.input_sanitizer import add_input_sanitizer
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from backend.security.security_headers import add_security_headers
from backend.security.csrf import add_csrf_protection
import uvicorn
import secrets

# Create a test app for testing purposes only
test_app = None

def create_app():
    """Create a new FastAPI application instance"""
    # Initialize Redis dependency
    redis_dependency = RedisDependency()
    
    # Initialize rate limit config
    rate_limit_config = RateLimitConfig()
    
    app = FastAPI(
        title=settings.APP_NAME,
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json"
    )
    
    # Initialize Redis dependency
    redis_dependency = RedisDependency()
    
    # Initialize rate limit config
    rate_limit_config = RateLimitConfig()
    
    # Add security headers middleware
    add_security_headers(app)
    
    # Add CSRF protection middleware
    add_csrf_protection(app)
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["Authorization", "X-CSRF-Token", "Content-Type"],
        expose_headers=["X-CSRF-Token"],
        max_age=600
    )
    
    # Add JWT middleware
    app.add_middleware(JWTMiddleware)
    
    # Add rate limit middleware
    app.add_middleware(
        RateLimitMiddleware,
        redis_dependency=redis_dependency,
        config=rate_limit_config
    )
    
    # Add input sanitizer middleware
    add_input_sanitizer(app)
    
    # Add routers
    from backend.test_routes import router as test_router
    app.include_router(test_router)
    app.include_router(churchsuite.router, prefix="/auth")
    app.include_router(chat.router, prefix="/chat")
    
    # Add root endpoint
    @app.get("/")
    async def root(request: Request):
        """Root endpoint with security headers"""
        return {"message": "Welcome to ChurchSuite Chatbot API"}
    
    # Add health check endpoint
    @app.get("/health")
    async def health_check():
        return {"status": "healthy"}
    
    # Add protected endpoint for testing
    @app.get("/protected")
    async def protected_endpoint(current_user: dict = Depends(get_current_user)):
        return {"message": "This is a protected endpoint", "user": current_user}
    
    return app

# Create the main app instance
app = create_app()

@app.get("/")
async def root(request: Request):
    """Root endpoint with security headers"""
    # Add security headers using request state
    return {"message": "Welcome to ChurchSuite Chatbot API"}
    return {"message": "Welcome to ChurchSuite Chatbot API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/protected")
async def protected_endpoint(current_user: dict = Depends(get_current_user)):
    return {"message": "This is a protected endpoint", "user": current_user}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
