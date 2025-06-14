from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Any
from jose import jwt, JWTError, ExpiredSignatureError
from fastapi import Depends, HTTPException, status
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
        to_encode.update({"exp": int(expire.timestamp())})
        
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

def get_current_user(token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
    """FastAPI dependency to get current authenticated user"""
    try:
        # First try to decode token with expiration verification
        try:
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
        except ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"}
            )
        except JWTError as e:
            # Try to decode without expiration to get more details
            try:
                payload = jwt.decode(
                    token,
                    settings.JWT_SECRET,
                    algorithms=[settings.JWT_ALGORITHM],
                    options={
                        "verify_exp": False,
                        "verify_signature": True,
                        "verify_aud": False
                    }
                )
                if not payload.get("sub"):
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Invalid token: Missing subject",
                        headers={"WWW-Authenticate": "Bearer"}
                    )
                if "exp" not in payload:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Invalid token: Missing expiration",
                        headers={"WWW-Authenticate": "Bearer"}
                    )
            except JWTError:
                logger.error(f"Invalid JWT token: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token",
                    headers={"WWW-Authenticate": "Bearer"}
                )

        # Validate required claims
        if not payload.get("sub"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: Missing subject",
                headers={"WWW-Authenticate": "Bearer"}
            )
        if "exp" not in payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: Missing expiration",
                headers={"WWW-Authenticate": "Bearer"}
            )

        logger.debug(f"Successfully verified JWT token for user: {payload.get('sub')}")
        return {"sub": payload.get("sub"), "username": payload.get("sub")}
        
    except Exception as e:
        logger.error(f"JWT verification error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"}
        )
