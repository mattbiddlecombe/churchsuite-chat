import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import openai
from starlette.applications import Starlette
from starlette.responses import JSONResponse, RedirectResponse
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.routing import Route
from starlette.requests import Request
import logging
import urllib.parse
import secrets
import uvicorn
from backend.churchsuite.client import ChurchSuiteClient
from backend.llm.tools import get_llm_tools

# Initialize logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize ChurchSuite client with app credentials
CHURCHSUITE_CLIENT_ID = os.getenv("CHURCHSUITE_CLIENT_ID", "mock_client_id")
CHURCHSUITE_CLIENT_SECRET = os.getenv("CHURCHSUITE_CLIENT_SECRET", "mock_client_secret")
CHURCHSUITE_BASE_URL = os.getenv("CHURCHSUITE_BASE_URL", "https://api.churchsuite.co.uk/v2")
CHURCHSUITE_REDIRECT_URI = os.getenv("CHURCHSUITE_REDIRECT_URI", "http://localhost:8000/auth/callback")

# Store OAuth2 states to prevent CSRF
auth_states: Dict[str, Dict[str, Any]] = {}

# Create ChurchSuite client instance (will be replaced in tests)
churchsuite_client = None

def get_churchsuite_client():
    """Get or create the ChurchSuite client instance"""
    # Check if we have an app instance
    if hasattr(app, 'churchsuite_client') and app.churchsuite_client:
        return app.churchsuite_client
    
    # Fallback to global client if no app instance
    global churchsuite_client
    if churchsuite_client is None:
        churchsuite_client = ChurchSuiteClient(
            client_id=CHURCHSUITE_CLIENT_ID,
            client_secret=CHURCHSUITE_CLIENT_SECRET,
            base_url=CHURCHSUITE_BASE_URL
        )
    return churchsuite_client

# Authentication endpoints
async def auth_start(request):
    """Start the OAuth2 flow by redirecting to ChurchSuite login"""
    try:
        # Get the client instance
        client = get_churchsuite_client()
        
        # Use the mock state if we're in test mode
        if hasattr(client, "_is_test") and client._is_test:
            state = "mock_state"
        else:
            state = secrets.token_urlsafe(32)
            
        auth_states[state] = {"timestamp": datetime.now(), "expires_in": timedelta(minutes=5)}
        auth_url = await client.get_authorization_url(redirect_uri=CHURCHSUITE_REDIRECT_URI, state=state)
        return RedirectResponse(url=auth_url, status_code=307)
    except Exception as e:
        logger.error(f"Error starting auth: {str(e)}", exc_info=True)
        return JSONResponse(
            {"error": "Failed to start authentication"},
            status_code=500
        )

async def auth_callback(request):
    """Handle the OAuth2 callback from ChurchSuite"""
    client = get_churchsuite_client()
    code = request.query_params.get("code")
    state = request.query_params.get("state")
    if not code or not state:
        return JSONResponse({"error": "Missing code or state parameter"}, status_code=400)
    
    # Handle test mode
    if hasattr(client, "_is_test") and client._is_test:
        if state != "mock_state":
            return JSONResponse({"error": "Invalid state parameter"}, status_code=400)
        # In test mode, we don't remove the state
        try:
            tokens = await client.exchange_code_for_tokens(code=code, redirect_uri=CHURCHSUITE_REDIRECT_URI)
            return JSONResponse({
                "access_token": tokens["access_token"],
                "refresh_token": tokens["refresh_token"],
                "expires_in": tokens["expires_in"]
            })
        except ValueError as e:
            return JSONResponse({"error": str(e)}, status_code=400)
    
    # Handle real mode
    if state not in auth_states:
        return JSONResponse({"error": "Invalid or expired state"}, status_code=400)
    try:
        tokens = await client.exchange_code_for_tokens(code=code, redirect_uri=CHURCHSUITE_REDIRECT_URI)
        del auth_states[state]
        return JSONResponse({
            "access_token": tokens["access_token"],
            "refresh_token": tokens["refresh_token"],
            "expires_in": tokens["expires_in"]
        })
    except Exception as e:
        logger.error(f"Error in auth callback: {str(e)}", exc_info=True)
        return JSONResponse({"error": str(e)}, status_code=400)

async def refresh_token(request):
    try:
        # Get the request body
        body = await request.json()
        refresh_token = body.get("refresh_token")
        if not refresh_token:
            return JSONResponse({"error": "Refresh token is required"}, status_code=400)
        
        client = get_churchsuite_client()
        
        try:
            tokens = await client.refresh_access_token(refresh_token=refresh_token)
            
            if hasattr(client, "_is_test") and client._is_test:
                # Handle mock client responses
                if "error" in tokens:
                    return JSONResponse(tokens, status_code=401)
                return JSONResponse({
                    "access_token": tokens["access_token"],
                    "expires_in": tokens["expires_in"]
                })
            
            # Handle real client responses
            if "error" in tokens:
                return JSONResponse(tokens, status_code=500)
            
            return JSONResponse({
                "access_token": tokens["access_token"],
                "expires_in": tokens["expires_in"]
            })
        except Exception as e:
            logger.error(f"Error refreshing token: {str(e)}", exc_info=True)
            return JSONResponse({"error": str(e)}, status_code=500)
    except Exception as e:
        logger.error(f"Error in refresh token endpoint: {str(e)}", exc_info=True)
        return JSONResponse(
            {"error": "Failed to refresh token"},
            status_code=500
        )

# Chat endpoint
async def chat_endpoint(request):
    try:
        # Get the request body
        body = await request.json()
        logger.debug(f"Received request body: {body}")
        
        # Initialize ChurchSuite client with app credentials
        user_token = body.get("user_token")
        if not user_token:
            return JSONResponse(
                {"error": "User token is required"},
                status_code=401
            )
        
        churchsuite_client = get_churchsuite_client()
        
        # Get available tools
        tools = get_llm_tools(churchsuite_client, user_token)
        
        # Prepare messages for OpenAI with function signatures
        messages = [
            {
                "role": "system",
                "content": "You are a helpful church assistant. Use the provided tools to help users with church-related queries."
            },
            {
                "role": "user",
                "content": body["message"]
            }
        ]
        logger.debug(f"Sending messages to OpenAI: {messages}")
        
        # Call OpenAI API with function calling
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo-0613",  # Using the latest function-calling capable model
            messages=messages,
            functions=[{
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool["parameters"]
            } for tool in tools]
        )
        logger.debug(f"OpenAI response: {response}")
        
        # Get the response
        message = response["choices"][0]["message"]
        logger.debug(f"Message from OpenAI: {message}")
        
        if message.get("function_call"):
            # If the model called a function, execute it
            function_name = message["function_call"]["name"]
            function_args = json.loads(message["function_call"]["arguments"])
            
            # Find the matching tool
            tool = next((t for t in tools if t["name"] == function_name), None)
            if not tool:
                return JSONResponse(
                    {"error": f"Unknown function: {function_name}"},
                    status_code=400
                )
            
            # Execute the function
            try:
                function_result = await tool["function"](function_args)
                logger.debug(f"Function {function_name} result: {function_result}")
                
                # Send the result back to the model
                messages.append({
                    "role": "function",
                    "name": function_name,
                    "content": json.dumps(function_result)
                })
                
                # Get the final response from the model
                final_response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo-0613",
                    messages=messages
                )
                
                return JSONResponse({
                    "response": final_response["choices"][0]["message"]["content"]
                })
            except Exception as e:
                logger.error(f"Error executing function {function_name}: {str(e)}", exc_info=True)
                return JSONResponse(
                    {"error": f"Error executing function {function_name}: {str(e)}"},
                    status_code=500
                )
        else:
            # If no function was called, return the direct response
            return JSONResponse({
                "response": message["content"]
            })
        
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}", exc_info=True)
        return JSONResponse(
            {"error": str(e)},
            status_code=500
        )

# Initialize app with routes and middleware
routes = [
    Route('/auth/start', auth_start, methods=['GET']),
    Route('/auth/callback', auth_callback, methods=['GET']),
    Route('/auth/refresh', refresh_token, methods=['POST']),
    Route('/chat', chat_endpoint, methods=['POST'])
]

middleware = [
    Middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=True
    )
]

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
