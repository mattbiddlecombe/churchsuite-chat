import os
from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from backend.config import settings
from backend.endpoints import churchsuite, chat
from backend.endpoints.rate_limit import RateLimitMiddleware, RedisDependency, RateLimitConfig
from backend.security.redis_dependency import RedisSettings
from backend.security.input_sanitizer import add_input_sanitizer, XSSPatterns, SQLInjectionPatterns
from backend.security.security_headers import add_security_headers
from backend.security.csrf import add_csrf_protection
from backend.endpoints.auth import router as auth_router  # type: ignore


def create_app():
    """Create and configure the FastAPI application"""
    app = FastAPI(
        title="ChurchSuite Chatbot API",
        description="API for interacting with ChurchSuite chatbot",
        version="1.0.0"
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Initialize XSS and SQL patterns
    app.state.xss_patterns = XSSPatterns()
    app.state.sql_patterns = SQLInjectionPatterns()
    
    # Add input sanitizer middleware
    add_input_sanitizer(app)

    # Add routes
    app.include_router(churchsuite.router, prefix="/api/v1/churchsuite", tags=["churchsuite"])
    app.include_router(chat.router, prefix="/api/v1/chat", tags=["chat"])
    app.include_router(auth_router, prefix="/api/v1/auth", tags=["auth"])

    # Initialize Redis settings and dependency
    redis_settings = RedisSettings(redis_url="redis://localhost:6379/0")
    redis_dependency = RedisDependency(redis_settings)
    
    # Initialize rate limit config
    rate_limit_config = RateLimitConfig(
        default_limits=["100/minute"],
        redis_url="redis://localhost:6379/0"
    )

    # Add rate limiting middleware
    app.add_middleware(
        RateLimitMiddleware,
        redis_dependency=redis_dependency,
        config=rate_limit_config
    )

    # Add test router
    from backend.test_routes import router as test_router
    app.include_router(test_router)
    
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
    async def protected_endpoint(request: Request):
        """Protected endpoint for testing"""
        try:
            current_user = await verify_token(request)
            return {"message": "Welcome to protected endpoint", "user": current_user.dict()}
        except HTTPException as e:
            return {"error": e.detail}
    
    return app

# Create the main app instance
def get_app():
    """Get the FastAPI app instance"""
    return create_app()

if __name__ == "__main__":
    import uvicorn
    app = create_app()
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
