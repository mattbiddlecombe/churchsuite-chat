from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import jwt, JWTError
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from backend.security.jwt_middleware import create_access_token, verify_token, get_current_user
from backend.schemas.auth import Token, TokenData
from backend.config import settings

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

@router.post("/token", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    # Validate credentials
    if form_data.username != "test" or form_data.password != "test":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Create access token
    access_token = create_access_token(
        data={"sub": form_data.username},
        expires_delta=timedelta(minutes=30)
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=TokenData)
async def read_users_me(current_user: Dict = Depends(get_current_user)):
    # Return user data from token
    user_data = {"sub": current_user.get("sub"), "username": current_user.get("sub")}
    # Remove any None values and ensure we have a valid sub
    if not user_data.get("sub"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"}
        )
    # Ensure we only return valid data
    valid_data = {k: v for k, v in user_data.items() if v is not None}
    if not valid_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token data",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return TokenData(**valid_data)

@router.get("/refresh", response_model=Token)
async def refresh_token(current_user: Dict = Depends(get_current_user)):
    access_token = create_access_token(
        data={"sub": current_user["sub"]},
        expires_delta=timedelta(seconds=settings.JWT_EXPIRATION)
    )
    return {"access_token": access_token, "token_type": "bearer"}
