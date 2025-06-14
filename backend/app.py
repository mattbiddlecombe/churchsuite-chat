import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
import openai
import secrets
import logging
from collections import defaultdict
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware import Middleware
from fastapi.responses import JSONResponse, RedirectResponse, Response
from backend.security.middleware import InputValidationMiddleware, RateLimitMiddleware
from backend.routers import churchsuite, chat

# Load environment variables
load_dotenv()

# Create FastAPI app instance
app = FastAPI(
    title="ChurchSuite Chatbot API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Configure middleware stack
middleware = [
    Middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
        max_age=600
    ),
    Middleware(
        InputValidationMiddleware
    )
]

app = FastAPI(
    title="ChurchSuite Chatbot API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    middleware=middleware
)

# Use FastAPI's state management for user data
app.user_state = {}  # Store user state in memory (for development/testing)

# Function to get user state
async def get_user_state(request: Request):
    """Get user state from request"""
    token = request.headers.get("Authorization")
    if not token:
        return None
    
    try:
        # Verify token and get user data
        user_data = await verify_token(token)
        return user_data
    except HTTPException:
        return None

# Initialize logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize rate limiting storage
rate_limit_storage = defaultdict(lambda: {'count': 0, 'reset_time': datetime.now()})

# Initialize ChurchSuite client with app credentials
CHURCHSUITE_CLIENT_ID = os.getenv("CHURCHSUITE_CLIENT_ID", "mock_client_id")
CHURCHSUITE_CLIENT_SECRET = os.getenv("CHURCHSUITE_CLIENT_SECRET", "mock_client_secret")
CHURCHSUITE_BASE_URL = os.getenv("CHURCHSUITE_BASE_URL", "https://api.churchsuite.co.uk/v2")
CHURCHSUITE_REDIRECT_URI = os.getenv("CHURCHSUITE_REDIRECT_URI", "http://localhost:8000/auth/callback")

# Initialize the ChurchSuite client
app.churchsuite_client = None

# Helper function to get the client
def get_churchsuite_client():
    """Get or create the ChurchSuite client instance"""
    if hasattr(app, 'churchsuite_client') and app.churchsuite_client:
        return app.churchsuite_client
    
    return ChurchSuiteClient(
        client_id=CHURCHSUITE_CLIENT_ID,
        client_secret=CHURCHSUITE_CLIENT_SECRET,
        base_url=CHURCHSUITE_BASE_URL
    )

app.get_churchsuite_client = get_churchsuite_client

# Add debug logging for routes
logger.info("Registered routes:")
for route in app.routes:
    logger.info(f"Route: {route.path} - {route.endpoint.__name__}")

# Add debug logging for middleware
logger.info("Registered middleware:")
for mw in app.user_middleware:
    logger.info(f"Middleware: {mw.cls.__name__}")

# Authentication endpoints
async def auth_start(request: Request):
    """Start the OAuth2 flow by redirecting to ChurchSuite login"""
    try:
        # Generate a random state
        state = secrets.token_urlsafe(32)
        
        # Store the state in auth_states
        app.user_state[state] = {
            "timestamp": datetime.now().timestamp(),
            "redirect_url": request.url_for("auth_callback")
        }
        
        # Build the authorization URL
        auth_url = f"{CHURCHSUITE_BASE_URL}/oauth2/authorize"
        params = {
            "client_id": CHURCHSUITE_CLIENT_ID,
            "response_type": "code",
            "redirect_uri": CHURCHSUITE_REDIRECT_URI,
            "state": state,
            "scope": "read write"
        }
        
        # Redirect to authorization URL
        return RedirectResponse(
            f"{auth_url}?{urllib.parse.urlencode(params)}"
        )
    except Exception as e:
        logger.error(f"Error in auth_start: {str(e)}")
        return JSONResponse(
            {"error": "Failed to start authentication"},
            status_code=500
        )

async def auth_callback(request: Request):
    """Handle the OAuth2 callback from ChurchSuite"""
    try:
        # Get code and state from request
        code = request.query_params.get("code")
        state = request.query_params.get("state")
        
        # Validate state
        if not state or state not in app.user_state:
            return JSONResponse(
                {"error": "Invalid state parameter"},
                status_code=400
            )
            
        stored_state = app.user_state[state]
        del app.user_state[state]  # Remove state after use
        
        # Get redirect URL from stored state
        redirect_url = stored_state["redirect_url"]
        
        # Exchange code for tokens
        token_url = f"{CHURCHSUITE_BASE_URL}/oauth2/token"
        token_data = {
            "client_id": CHURCHSUITE_CLIENT_ID,
            "client_secret": CHURCHSUITE_CLIENT_SECRET,
            "code": code,
            "redirect_uri": CHURCHSUITE_REDIRECT_URI,
            "grant_type": "authorization_code"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(token_url, data=token_data)
            if response.status_code != 200:
                return JSONResponse(
                    {"error": "Failed to get access token"},
                    status_code=400
                )
                
            token_data = response.json()
            
            # Create JWT token
            jwt_data = {
                "sub": token_data["access_token"],
                "username": "churchsuite_user",
                "exp": int((datetime.now() + timedelta(minutes=30)).timestamp())
            }
            jwt_token = create_access_token(jwt_data, timedelta(minutes=30))
            
            # Get user info
            user_url = f"{CHURCHSUITE_BASE_URL}/api/v1/users/me"
            headers = {"Authorization": f"Bearer {token_data['access_token']}"}
            user_response = await client.get(user_url, headers=headers)
            if user_response.status_code == 200:
                user_data = user_response.json()
                
                # Store tokens and user data in state
                app.user_state["access_token"] = token_data["access_token"]
                app.user_state["refresh_token"] = token_data["refresh_token"]
                app.user_state["user"] = user_data
                
                # Set JWT token in response
                response = RedirectResponse(redirect_url)
                response.set_cookie(
                    "jwt_token",
                    jwt_token,
                    httponly=True,
                    secure=True,
                    samesite="lax",
                    expires=int((datetime.now() + timedelta(minutes=30)).timestamp())
                )
                return response
            else:
                return JSONResponse(
                    {"error": "Failed to get user data"},
                    status_code=400
                )
    except Exception as e:
        logger.error(f"Error in auth_callback: {str(e)}")
        return JSONResponse(
            {"error": "Authentication failed"},
            status_code=500
        )

async def refresh_token(request: Request):
    """Refresh the OAuth2 access token"""
    try:
        # Get refresh token from state
        refresh_token = app.user_state.get("refresh_token")
        if not refresh_token:
            return JSONResponse(
                {"error": "No refresh token available"},
                status_code=400
            )
            
        # Refresh token
        token_url = f"{CHURCHSUITE_BASE_URL}/oauth2/token"
        token_data = {
            "client_id": CHURCHSUITE_CLIENT_ID,
            "client_secret": CHURCHSUITE_CLIENT_SECRET,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(token_url, data=token_data)
            if response.status_code != 200:
                return JSONResponse(
                    {"error": "Failed to refresh token"},
                    status_code=500
                )
                
            token_data = response.json()
            
            # Update state with new tokens
            app.user_state["access_token"] = token_data["access_token"]
            app.user_state["refresh_token"] = token_data["refresh_token"]
            
            # Create new JWT token
            jwt_data = {
                "sub": token_data["access_token"],
                "username": "churchsuite_user",
                "exp": int((datetime.now() + timedelta(minutes=30)).timestamp())
            }
            jwt_token = create_access_token(jwt_data, timedelta(minutes=30))
            
            # Return new JWT token
            return JSONResponse(
                {"message": "Token refreshed successfully", "jwt_token": jwt_token}
            )
    except Exception as e:
        logger.error(f"Error in refresh_token: {str(e)}")
        return JSONResponse(
            {"error": "Failed to refresh token"},
            status_code=500
        )

# Test endpoint for rate limiting
async def test_rate_limit(request: Request):
    """Test endpoint for rate limiting and validation"""
    # Bypass auth_middleware for testing
    return JSONResponse({"message": "Rate limit test endpoint"})

# Remove RateLimitMiddleware since we'll use FastAPI's native rate limiting
# The rate limiting will be handled through FastAPI's dependency injection
# and middleware stack.

middleware = [
    Middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
        max_age=600
    ),
    Middleware(
        InputValidationMiddleware
    )
]

app = FastAPI(
    title="ChurchSuite Chatbot API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    middleware=middleware
)

# Initialize the ChurchSuite client
app.churchsuite_client = None

# Add a method to get the client
app.get_churchsuite_client = get_churchsuite_client

# Add debug logging for routes
logger.info("Registered routes:")
for route in app.routes:
    logger.info(f"Route: {route.path} - {route.endpoint.__name__}")

# Add debug logging for middleware
logger.info("Registered middleware:")
for mw in app.user_middleware:
    logger.info(f"Middleware: {mw.cls.__name__}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
