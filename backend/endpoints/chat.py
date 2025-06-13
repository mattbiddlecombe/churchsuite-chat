from starlette.requests import Request
from starlette.responses import JSONResponse
from backend.security.jwt_middleware import JWTMiddleware

async def chat_endpoint(request: Request) -> JSONResponse:
    """Protected chat endpoint that requires JWT authentication"""
    # This endpoint is protected by the JWT middleware
    # The middleware will validate the token and add user info to request.state
    return JSONResponse({"message": "Chat endpoint"})
