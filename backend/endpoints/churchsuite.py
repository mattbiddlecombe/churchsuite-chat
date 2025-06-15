from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import RedirectResponse
from backend.config import settings
from backend.churchsuite.client import ChurchSuiteClient
from typing import Optional
from datetime import datetime
import logging
import urllib.parse
import secrets

router = APIRouter()
logger = logging.getLogger(__name__)

# Store OAuth2 states to prevent CSRF
auth_states = {}

def get_churchsuite_client():
    """Get or create the ChurchSuite client instance"""
    return ChurchSuiteClient(
        client_id=settings.CS_CLIENT_ID,
        client_secret=settings.CS_CLIENT_SECRET,
        base_url=settings.CHURCHSUITE_BASE_URL
    )

@router.get("/cs/start")
async def auth_start(request: Request):
    """Start the OAuth2 flow by redirecting to ChurchSuite login"""
    try:
        state = secrets.token_hex(16)
        auth_states[state] = datetime.now()
        
        client = get_churchsuite_client()
        auth_url = client.get_authorization_url(
            redirect_uri=settings.CHURCHSUITE_REDIRECT_URI,
            state=state
        )
        
        return RedirectResponse(auth_url)
    except Exception as e:
        logger.error(f"Auth start error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/cs/callback")
async def auth_callback(request: Request):
    """Handle the OAuth2 callback from ChurchSuite"""
    try:
        code = request.query_params.get("code")
        state = request.query_params.get("state")
        
        if not state or state not in auth_states:
            raise HTTPException(status_code=400, detail="Invalid state")
            
        client = get_churchsuite_client()
        token = await client.exchange_code_for_tokens(
            code=code,
            redirect_uri=settings.CHURCHSUITE_REDIRECT_URI
        )
        
        # Store token in session
        request.session["churchsuite_token"] = token
        
        return RedirectResponse("/")
    except Exception as e:
        logger.error(f"Auth callback error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/cs/refresh")
async def refresh_token(request: Request):
    """Refresh the OAuth2 access token"""
    try:
        # Get token from session
        session_data = request.cookies.get("session")
        if not session_data:
            raise HTTPException(status_code=401, detail="No token found")
            
        # Parse session data
        try:
            session_data = json.loads(session_data)
            token_data = session_data.get("churchsuite_token")
        except (json.JSONDecodeError, TypeError):
            raise HTTPException(status_code=401, detail="Invalid session data")
            
        if not token_data:
            raise HTTPException(status_code=401, detail="No token found")
            
        # Refresh token
        client = get_churchsuite_client()
        token = await client.refresh_access_token(
            refresh_token=token_data["refresh_token"]
        )
        
        # Return new token
        return token
    except Exception as e:
        logger.error(f"Token refresh error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
