import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import openai
from starlette.applications import Starlette
from starlette.responses import JSONResponse, RedirectResponse, Response
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from backend.security.middleware import InputValidationMiddleware
from backend.security.jwt_middleware import JWTMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Dict, Optional, List, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
from starlette.routing import Route
from starlette.requests import Request
from starlette.exceptions import HTTPException
import logging
import urllib.parse
import secrets
import uvicorn
from backend.churchsuite.client import ChurchSuiteClient
from backend.llm.tools import get_llm_tools

# Load environment variables
load_dotenv()

# Create app instance first
app = Starlette()

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize session secret
SESSION_SECRET = os.getenv("SESSION_SECRET", secrets.token_hex(32))

# In-memory rate limiting storage
rate_limit_storage = defaultdict(lambda: {'count': 0, 'reset_time': datetime.now()})

# Initialize ChurchSuite client with app credentials
CHURCHSUITE_CLIENT_ID = os.getenv("CHURCHSUITE_CLIENT_ID", "mock_client_id")
CHURCHSUITE_CLIENT_SECRET = os.getenv("CHURCHSUITE_CLIENT_SECRET", "mock_client_secret")
CHURCHSUITE_BASE_URL = os.getenv("CHURCHSUITE_BASE_URL", "https://api.churchsuite.co.uk/v2")
CHURCHSUITE_REDIRECT_URI = os.getenv("CHURCHSUITE_REDIRECT_URI", "http://localhost:8000/auth/callback")

# Create app instance first
app = Starlette()

# Configure middleware stack
middleware = [
    Middleware(SessionMiddleware, secret_key=SESSION_SECRET, max_age=3600 * 24, https_only=True, same_site="strict"),
    Middleware(CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Requested-With", "X-CSRF-Token"],
        expose_headers=["*"]
    ),
    Middleware(JWTMiddleware),
    Middleware(InputValidationMiddleware)
]

# Add middleware to app
for mw in middleware:
    app.add_middleware(mw.cls, **mw.options)

# Define route handlers
async def test_rate_limit(request):
    """Test endpoint for rate limiting"""
    return JSONResponse({"message": "Rate limit test endpoint"})

async def chat_endpoint(request):
    """Chat endpoint handler"""
    try:
        # Parse request body
        body = await request.json()
        
        # Validate request
        try:
            chat_request = ChatRequest(**body)
        except Exception as e:
            logger.error(f"Chat request validation error: {str(e)}", exc_info=True)
            # Return 400 for validation errors
            return JSONResponse(
                {"error": f"Invalid request: {str(e)}"},
                status_code=400
            )
        
        # Get tools
        tools = get_llm_tools()
        
        # Process chat request
        response = await process_chat_request(chat_request, tools)
        
        return JSONResponse(response)
    except Exception as e:
        logger.error(f"Chat endpoint error: {str(e)}", exc_info=True)
        return JSONResponse(
            {"error": f"Error processing request: {str(e)}"},
            status_code=500
        )

# Routes
routes = [
    Route('/test/rate-limit', test_rate_limit, methods=['GET']),
    Route('/chat', chat_endpoint, methods=['POST'])
]

# Register routes
app.routes.extend(routes)

# Configure session middleware
app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET,
    max_age=3600 * 24,  # 24 hours
    https_only=True,
    same_site="strict"
)

# Store OAuth2 states to prevent CSRF
app.auth_states = {}

# Create ChurchSuite client instance (will be replaced in tests)
app.churchsuite_client = None

# Create ChurchSuite client instance (will be replaced in tests)
app.churchsuite_client = None

# Helper function to get the client
get_churchsuite_client = lambda: app.churchsuite_client or ChurchSuiteClient(
    client_id=CHURCHSUITE_CLIENT_ID,
    client_secret=CHURCHSUITE_CLIENT_SECRET,
    base_url=CHURCHSUITE_BASE_URL
)

def get_churchsuite_client():
    """Get or create the ChurchSuite client instance"""
    if hasattr(app, 'churchsuite_client') and app.churchsuite_client:
        return app.churchsuite_client
    
    return ChurchSuiteClient(
        client_id=CHURCHSUITE_CLIENT_ID,
        client_secret=CHURCHSUITE_CLIENT_SECRET,
        base_url=CHURCHSUITE_BASE_URL
    )

# Authentication endpoints
async def auth_start(request):
    """Start the OAuth2 flow by redirecting to ChurchSuite login"""
    try:
        # Get the client instance
        client = get_churchsuite_client()
        
        # Validate client ID
        if not client.client_id:
            return RedirectResponse(
                url='/error?message=Invalid+client+configuration',
                status_code=307
            )
        
        # Generate a secure state token
        state = secrets.token_urlsafe(32)
        
        # Store state with timestamp and expiration
        if not hasattr(app, 'auth_states'):
            app.auth_states = {}
        
        app.auth_states[state] = {
            "timestamp": datetime.now(),
            "expires_in": timedelta(minutes=5),
            "client_id": client.client_id
        }
        
        # Get authorization URL
        auth_url = await client.get_authorization_url(
            redirect_uri=CHURCHSUITE_REDIRECT_URI,
            state=state
        )
        
        # Store state in session for CSRF protection
        request.session["oauth_state"] = state
        
        # Return redirect response
        return RedirectResponse(url=auth_url, status_code=307)
        
    except Exception as e:
        logger.error(f"Error starting auth: {str(e)}", exc_info=True)
        return RedirectResponse(
            url='/error?message=Failed+to+start+authentication',
            status_code=307
        )

async def auth_callback(request):
    """Handle the OAuth2 callback from ChurchSuite"""
    try:
        code = request.query_params.get("code")
        state = request.query_params.get("state")
        
        if not code or not state:
            return JSONResponse(
                {"error": "Missing required parameters"},
                status_code=400
            )
            
        # Verify state matches session state
        session_state = request.session.get("oauth_state")
        if state != session_state:
            return JSONResponse(
                {"error": "Invalid or mismatched state parameter"},
                status_code=400
            )
            
        # Get the client instance
        client = get_churchsuite_client()
        
        # Exchange code for tokens
        token_data = await client.exchange_code_for_tokens(
            code=code,
            redirect_uri=CHURCHSUITE_REDIRECT_URI
        )
        
        # Store tokens in session
        request.session["access_token"] = token_data["access_token"]
        request.session["refresh_token"] = token_data["refresh_token"]
        request.session["token_expires_at"] = str(datetime.now() + timedelta(seconds=token_data["expires_in"]))
        request.session["user_id"] = token_data.get("user_id")
        
        # Clean up state
        del app.auth_states[state]
        del request.session["oauth_state"]
        
        return JSONResponse({"success": True})
        
    except Exception as e:
        logger.error(f"Error in auth callback: {str(e)}", exc_info=True)
        return JSONResponse(
            {"error": "Authentication failed"},
            status_code=500
        )

async def refresh_token(request):
    """Refresh the OAuth2 access token"""
    try:
        refresh_token = request.session.get("refresh_token")
        if not refresh_token:
            return JSONResponse(
                {"error": "No refresh token available"},
                status_code=401
            )
            
        client = get_churchsuite_client()
        token_data = await client.refresh_access_token(refresh_token)
        
        # Update session
        request.session["access_token"] = token_data["access_token"]
        request.session["refresh_token"] = token_data["refresh_token"]
        request.session["token_expires_at"] = str(datetime.now() + timedelta(seconds=token_data["expires_in"]))
        
        return JSONResponse({"success": True})
        
    except Exception as e:
        logger.error(f"Error refreshing token: {str(e)}", exc_info=True)
        return JSONResponse(
            {"error": "Failed to refresh token"},
            status_code=500
        )

# Middleware to check authentication for protected routes
class AuthMiddleware(BaseHTTPMiddleware):
    """Middleware to check authentication for protected routes"""
    async def dispatch(self, request: Request, call_next):
        try:
            logger.debug("AuthMiddleware dispatch called")
            logger.debug(f"Request path: {request.url.path}")
            
            # Allow auth endpoints and session setup
            if request.url.path.startswith('/auth/') or request.url.path == '/set-session':
                logger.debug("Auth endpoint or session setup detected, passing through")
                return await call_next(request)

            # Get session data from request
            try:
                session = request.session
                logger.debug(f"Session data: {dict(session)}")
            except Exception:
                logger.debug("No session middleware installed")
                return JSONResponse({"error": "Not authenticated"}, status_code=401)
            
            # Get user data
            user_data = session.get('user')
            logger.debug(f"User data from session: {user_data}")
            
            if not user_data:
                logger.debug("No user data found in session")
                return JSONResponse({"error": "Not authenticated"}, status_code=401)

            if not user_data.get('token'):
                logger.debug("No valid token found")
                return JSONResponse({"error": "Invalid authentication token"}, status_code=401)

            logger.debug("Auth check passed, continuing request")
            return await call_next(request)

        except Exception as e:
            logger.error(f"Auth middleware error: {str(e)}")
            return JSONResponse({"error": "Internal server error"}, status_code=500)

# Rate limiting middleware
class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for auth endpoints
        if request.url.path.startswith('/auth/'):
            return await call_next(request)

        # Get user ID from session or use IP
        user_id = request.session.get('user_id')
        if not user_id:
            user_id = request.client.host if request.client else 'unknown'

        # Create rate limit key
        key = f"rate_limit:{user_id}:{request.url.path}"
        
        # Get or create rate limit entry
        entry = rate_limit_storage[key]
        
        # Check if we need to reset the window
        now = datetime.now()
        if now >= entry['reset_time']:
            entry['count'] = 0
            entry['reset_time'] = now + RATE_LIMIT_WINDOW

        # Check if we've exceeded the limit
        if entry['count'] >= RATE_LIMIT_REQUESTS:
            return JSONResponse(
                {"error": "Rate limit exceeded. Please try again later."},
                status_code=429
            )

        # Increment the count
        entry['count'] += 1
        
        return await call_next(request)

# Test endpoint for rate limiting
async def test_rate_limit(request: Request):
    """Test endpoint for rate limiting and validation"""
    # Bypass auth_middleware for testing
    return JSONResponse({"message": "Rate limit test endpoint"})

# Chat endpoint
async def chat_endpoint(request: Request):
    """Handle chat messages using OpenAI API"""
    try:
        # Get user data from session
        user_data = request.session.get('user')
        if not user_data:
            return JSONResponse(
                {"error": "Not authenticated"},
                status_code=401
            )

        # Get request data
        try:
            data = await request.json()
        except json.JSONDecodeError:
            return JSONResponse(
                {"error": "Invalid JSON"},
                status_code=400
            )
        
        # Basic validation
        if not isinstance(data, dict) or 'message' not in data:
            return JSONResponse(
                {"error": "Request must contain a 'message' field"},
                status_code=400
            )

        # For testing, just return the message back
        return JSONResponse({"response": f"Echo: {data['message']}"})
        
        # TODO: Actual OpenAI processing code here
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        return JSONResponse(
            {"error": "Internal server error"},
            status_code=500
        )

        # Get ChurchSuite client
        client = get_churchsuite_client()
        if not client:
            return JSONResponse(
                {"error": "Failed to initialize ChurchSuite client"},
                status_code=500
            )

        # Get LLM tools
        llm_tools = get_llm_tools(client)
        if not llm_tools:
            return JSONResponse(
                {"error": "Failed to initialize LLM tools"},
                status_code=500
            )

        # Process message using OpenAI
        try:
            response = await process_message(data['message'], llm_tools)
            return JSONResponse({"response": response})
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            return JSONResponse(
                {"error": "Failed to process message"},
                status_code=500
            )

    except Exception as e:
        logger.error(f"Chat endpoint error: {str(e)}")
        return JSONResponse(
            {"error": "Internal server error"},
            status_code=500
        )

# Initialize app with routes and middleware
routes = [
    Route('/test/rate-limit', test_rate_limit, methods=['GET']),
    Route('/chat', chat_endpoint, methods=['POST']),
    Route('/auth/start', auth_start, methods=['GET']),
    Route('/auth/callback', auth_callback, methods=['GET']),
    Route('/auth/refresh', refresh_token, methods=['POST'])
]

middleware = [
    Middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=True
    ),
    Middleware(
        SessionMiddleware,
        secret_key=SESSION_SECRET,
        max_age=3600 * 24,  # 24 hours
        https_only=True,
        same_site="strict"
    ),
    Middleware(
        InputValidationMiddleware
    )
]

# Add rate limiting middleware to the middleware list
middleware.append(Middleware(RateLimitMiddleware))

# Create the app instance
app = Starlette(
    debug=True,
    routes=routes,
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
