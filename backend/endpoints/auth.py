from fastapi import APIRouter, Request, Response, HTTPException, Depends, status, Query
from fastapi.responses import RedirectResponse
from backend.security.csrf import generate_csrf_token
from backend.security.jwt_middleware_native import verify_token
from backend.security.redis_dependency import RedisDependency
from typing import Optional
import secrets
from datetime import datetime, timedelta, timezone

# Create auth router
router = APIRouter(
    tags=["auth"]
)

__all__ = ["router"]

@router.get("/start")
async def auth_start(request: Request, redis_dependency: RedisDependency = Depends()):
    """Start the authentication process"""
    # Generate CSRF token
    csrf_token = generate_csrf_token()
    
    # Store state in Redis with expiration
    redis_key = f"auth_state:{csrf_token}"
    await redis_dependency._redis.setex(redis_key, 3600, csrf_token)  # Store the token itself
    
    # Set CSRF token in response
    response = Response(status_code=200)
    response.set_cookie(
        key="csrf_token",
        value=csrf_token,
        httponly=True,
        secure=True,
        samesite="lax"
    )
    
    # Include state parameter in callback URL
    callback_url = f"/api/v1/auth/callback?state={csrf_token}"
    response.headers["Location"] = callback_url
    
    return response

@router.get("/callback")
async def auth_callback(
    request: Request,
    state: str = Query(..., description="OAuth2 state parameter"),
    redis_dependency: RedisDependency = Depends()
):
    """Handle authentication callback"""
    try:
        print(f"Auth callback received state: {state}")
        
        # Verify state in Redis
        redis_key = f"auth_state:{state}"
        exists = await redis_dependency._redis.exists(redis_key)
        if not exists:
            print(f"Redis key {redis_key} not found")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid state parameter"
            )
            
        # Generate tokens
        access_token = secrets.token_urlsafe(32)
        refresh_token = secrets.token_urlsafe(32)
        print(f"Generating tokens: access={access_token[:5]}... refresh={refresh_token[:5]}...")
        
        # Set tokens in response
        response = Response(status_code=200)
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            secure=True,
            samesite="lax",
            expires=datetime.now(timezone.utc) + timedelta(hours=1)
        )
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            secure=True,
            samesite="lax",
            expires=datetime.now(timezone.utc) + timedelta(days=7)
        )
        
        # Clean up state
        await redis_dependency._redis.delete(redis_key)
        return response
            
        redis_key = f"auth_state:{state}"
        exists = await redis_dependency._redis.exists(redis_key)
        if not exists:
            print(f"Redis key {redis_key} not found")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid state parameter"
            )
            
        # Generate tokens
        access_token = secrets.token_urlsafe(32)
        refresh_token = secrets.token_urlsafe(32)
        print(f"Generating tokens: access={access_token[:5]}... refresh={refresh_token[:5]}...")
        
        # Set tokens in response
        response = Response(status_code=200)
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            secure=True,
            samesite="lax",
            expires=datetime.now(timezone.utc) + timedelta(hours=1)
        )
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            secure=True,
            samesite="lax",
            expires=datetime.now(timezone.utc) + timedelta(days=7)
        )
        
        # Clean up state
        await redis_dependency._redis.delete(redis_key)
        return response
        
    except HTTPException as e:
        # Re-raise any HTTP exceptions we want to handle
        raise e
    except Exception as e:
        # Log and return a generic error for other exceptions
        print(f"Error in auth callback: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )
    
    # Verify state in Redis
    redis_key = f"auth_state:{state}"
    exists = await redis_dependency._redis.exists(redis_key)
    print(f"Checking Redis key: {redis_key}")
    print(f"Redis key exists: {exists}")
    
    if not exists:
        print("Invalid state parameter")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid state parameter"
        )
    
    # Generate tokens
    access_token = secrets.token_urlsafe(32)
    refresh_token = secrets.token_urlsafe(32)
    print(f"Generating tokens: access={access_token[:5]}... refresh={refresh_token[:5]}...")
    
    # Set tokens as cookies
    response = Response(status_code=200)
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=True,
        samesite="lax",
        expires=datetime.now(timezone.utc) + timedelta(hours=1)
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="lax",
        expires=datetime.now(timezone.utc) + timedelta(days=7)
    )
    
    # Remove the state from Redis since it's been used
    await redis_dependency._redis.delete(redis_key)
    
    return response

@router.get("/refresh")
async def refresh_token(request: Request, current_user=Depends(verify_token)):
    """Refresh access token"""
    # Generate new tokens
    access_token = secrets.token_urlsafe(32)
    refresh_token = secrets.token_urlsafe(32)
    
    # Set tokens as cookies
    response = Response(status_code=200)
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=True,
        samesite="lax",
        expires=datetime.now(timezone.utc) + timedelta(hours=1)
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="lax",
        expires=datetime.now(timezone.utc) + timedelta(days=7)
    )
    
    return response
