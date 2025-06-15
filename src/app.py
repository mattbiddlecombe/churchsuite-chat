from fastapi import FastAPI
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from backend.security.jwt_middleware_native import JWTMiddleware
from backend.config import settings as JWTSettings
from src.endpoints.auth import router as auth_router

app = FastAPI(
    title="ChurchSuite Chatbot API",
    description="Secure API for ChurchSuite chatbot integration",
    version="0.1.0",
)

# Configure middleware
middleware = [
    Middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    ),
    Middleware(
        SessionMiddleware,
        secret_key="test-secret",  # Replace with actual secret in production
    ),
    Middleware(
        JWTMiddleware,
        settings=JWTSettings(
            secret_key="test-secret",
            algorithm="HS256",
            access_token_expires_minutes=30
        )
    ),
]

# Add middleware to app
app.middleware = middleware

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
