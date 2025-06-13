from typing import Dict, List, Optional
from datetime import datetime
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp, Receive, Scope, Send
from jose import JWTError, jwt
from pydantic import BaseModel
from fastapi.security import HTTPBearer
from fastapi import HTTPException, status
from starlette.middleware.base import RequestResponseEndpoint
from backend.config import settings  # Import settings from existing config


class JWTSettings(BaseModel):
    secret_key: str
    algorithm: str = "HS256"
    access_token_expires_minutes: int = 30


class JWTMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, settings: JWTSettings):
        super().__init__(app)
        self.settings = settings
        self.security = HTTPBearer()

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        try:
            # Bypass auth endpoints
            if request.url.path in ["/auth/start", "/auth/callback", "/auth/refresh"]:
                return await call_next(request)

            # Get token from Authorization header
            auth_header = request.headers.get("Authorization")
            if not auth_header:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Missing Authorization header",
                )

            # Validate token
            token = auth_header.split(" ")[1] if " " in auth_header else auth_header
            try:
                payload = jwt.decode(
                    token,
                    self.settings.secret_key,
                    algorithms=[self.settings.algorithm]
                )
                # Add user info to request state
                request.state.user = payload
            except JWTError:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or expired token",
                )

            # Add security headers
            security_headers = [
                [b"x-content-type-options", b"nosniff"],
                [b"x-frame-options", b"DENY"],
                [b"x-xss-protection", b"1; mode=block"],
                [b"access-control-allow-origin", b"*"],
                [b"access-control-allow-credentials", b"true"],
                [b"access-control-allow-headers", b"content-type, authorization, x-csrf-token"],
            ]

            # Call next middleware
            response = await call_next(request)
            
            # Add security headers to response
            for header in security_headers:
                response.headers[header[0].decode()] = header[1].decode()

            return response

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e),
            )
