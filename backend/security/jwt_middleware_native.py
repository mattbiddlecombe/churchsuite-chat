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

def verify_token(request: Request) -> TokenData:
    """Verify JWT token from Authorization header"""
    try:
        # Skip auth endpoints
        auth_paths = ['/api/v1/auth/start', '/api/v1/auth/callback', '/api/v1/auth/refresh']
        if request.url.path in auth_paths:
            return TokenData(sub='test_user', username='test_user', exp=int(datetime.now(timezone.utc).timestamp()) + 3600)
            
        # Get token from Authorization header
        auth_header = request.headers.get("authorization")
        if not auth_header:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing Authorization header",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        # Extract token
        scheme, token = auth_header.split()
        if scheme.lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication scheme",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        # Verify token
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET,
                algorithms=[settings.JWT_ALGORITHM]
            )
            token_data = TokenData(**payload)
            
            # Check token expiration
            if datetime.now(timezone.utc) > datetime.fromtimestamp(token_data.exp, timezone.utc):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has expired",
                    headers={"WWW-Authenticate": "Bearer"}
                )
            
            # Set user data in request state
            request.state.user = token_data
            return token_data
            
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
