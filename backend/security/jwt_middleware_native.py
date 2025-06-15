from typing import Dict, Optional, Any, Callable, TypeVar
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI, Request, Response, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError, ExpiredSignatureError
from pydantic import BaseModel, ConfigDict
from backend.config import settings
import logging

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

class TokenData(BaseModel):
    """Model for decoded JWT token data"""
    sub: str
    username: str
    exp: int  # Unix timestamp
    
    model_config = ConfigDict(from_attributes=True)

def create_access_token(data: dict, expires_delta: timedelta) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": int(expire.timestamp())})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt

class JWTMiddleware:
    """FastAPI-native JWT authentication middleware"""
    
    def __init__(self, app: FastAPI):
        """Initialize middleware with FastAPI app"""
        self.app = app
        
    async def __call__(self, request: Request, call_next: Callable) -> Response:
        """Middleware dispatch method"""
        try:
            # Skip auth endpoints
            if request.url.path in ['/auth/start', '/auth/callback', '/auth/refresh']:
                return await call_next(request)
                
            # Get token from Authorization header
            auth_header = request.headers.get("authorization")
            if not auth_header:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Missing Authorization header",
                    headers={"WWW-Authenticate": "Bearer"}
                )
                
            token = auth_header.split(" ")[-1]
            
            # Validate token
            try:
                payload = jwt.decode(
                    token,
                    settings.JWT_SECRET,
                    algorithms=[settings.JWT_ALGORITHM],
                    options={"verify_exp": True}
                )
                
                # Set user data in request state
                request.state.user = payload
                
                # Add security headers
                response = await call_next(request)
                response.headers["WWW-Authenticate"] = "Bearer"
                return response
                
            except ExpiredSignatureError:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has expired",
                    headers={"WWW-Authenticate": "Bearer"}
                )
            except JWTError as e:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"Invalid token: {str(e)}",
                    headers={"WWW-Authenticate": "Bearer"}
                )
                
        except Exception as e:
            logger.error(f"JWT middleware error: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error"
            )

def get_current_user(token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
    """FastAPI dependency to get current authenticated user"""
    try:
        # First try to decode token with expiration verification
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET,
                algorithms=[settings.JWT_ALGORITHM],
                options={"verify_exp": True}
            )
            
            # Validate required fields
            if not all(key in payload for key in ['sub', 'exp']):
                raise ValueError("Missing required fields in token")
            
            return payload
            
        except ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"}
            )
            
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"}
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"}
        )
