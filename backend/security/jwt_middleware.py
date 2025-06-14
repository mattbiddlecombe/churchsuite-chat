from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Any, Union
from jose import jwt, JWTError, ExpiredSignatureError
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from backend.config import settings
import logging

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

class TokenData(BaseModel):
    sub: str
    username: str
    exp: int  # Unix timestamp

def create_access_token(data: dict, expires_delta: timedelta) -> str:
    """Create a JWT access token with proper expiration"""
    try:
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + expires_delta
        to_encode.update({"exp": int(expire.timestamp())})  # Store timestamp as integer
        
        encoded_jwt = jwt.encode(
            to_encode,
            settings.JWT_SECRET,
            algorithm=settings.JWT_ALGORITHM
        )
        logger.debug(f"Created JWT token for user: {data.get('sub')}")
        return encoded_jwt
    except Exception as e:
        logger.error(f"Error creating JWT token: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create JWT token"
        )

async def verify_token(token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
    """Verify JWT token and return user data"""
    try:
        logger.debug(f"Verifying JWT token: {token[:10]}...")  # Log partial token for security
        
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
            options={
                "verify_exp": True,
                "verify_signature": True,
                "verify_aud": False
            }
        )
        
        # Validate token expiration
        if "exp" not in payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: Missing expiration claim",
                headers={"WWW-Authenticate": "Bearer"}
            )
            
        current_time = int(datetime.now(timezone.utc).timestamp())
        if current_time > payload["exp"]:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"}
            )
            
        # Validate subject
        if not payload.get("sub"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: Missing subject",
                headers={"WWW-Authenticate": "Bearer"}
            )
            
        logger.debug(f"Successfully verified JWT token for user: {payload.get('sub')}")
        return {"sub": payload.get("sub"), "username": payload.get("sub")}
        
    except ExpiredSignatureError:
        logger.warning("Expired JWT token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"}
        )
        
    except JWTError as e:
        logger.error(f"Invalid JWT token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"}
        )
        
    except Exception as e:
        logger.error(f"JWT verification error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"}
        )
    except Exception as e:
        logger.error(f"Unexpected error in token verification: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"}
        )

# FastAPI dependency for protected endpoints
async def get_current_user(token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
    """FastAPI dependency for protected endpoints"""
    try:
        return await verify_token(token)
    except HTTPException as e:
        logger.error(f"Authentication error: {e.detail}")
        raise e

class JWTBearer:
    """FastAPI dependency for JWT token validation"""
    def __init__(self):
        pass

    async def __call__(self, token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
        return await verify_token(token)

# Remove JWTMiddleware class as it's no longer needed
