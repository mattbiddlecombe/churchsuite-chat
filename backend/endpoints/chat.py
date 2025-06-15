from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from backend.security.jwt_middleware_native import verify_token

router = APIRouter(tags=["chat"])

@router.get("/")
async def chat_endpoint(current_user=Depends(verify_token)) -> JSONResponse:
    """Protected chat endpoint that requires JWT authentication"""
    return JSONResponse({"message": "Chat endpoint", "user": current_user.dict()})
