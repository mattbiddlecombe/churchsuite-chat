import os
from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from backend.config import settings
from backend.routers import churchsuite, chat
from backend.security.jwt_middleware import get_current_user
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from backend.security.middleware import InputValidationMiddleware, RateLimitMiddleware
import uvicorn
import secrets
app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Configure FastAPI middleware
from backend.security.fastapi_middleware import setup_fastapi_middleware
setup_fastapi_middleware(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=600
)

# Add input validation and rate limiting middleware
# Add FastAPI middleware
from backend.security.middleware import InputValidationMiddleware, RateLimitMiddleware
app.add_middleware(InputValidationMiddleware)
app.add_middleware(RateLimitMiddleware)

# Routers
app.include_router(churchsuite.router, prefix="/auth")
app.include_router(chat.router, prefix="/chat")

@app.get("/")
async def root():
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
