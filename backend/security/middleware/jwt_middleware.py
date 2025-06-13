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
from backend.security.security_headers import SecurityHeadersConfig


class JWTSettings(BaseModel):
    secret_key: str
    algorithm: str = "HS256"
    access_token_expires_minutes: int = 30


class JWTMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, settings: JWTSettings):
        super().__init__(app)
        self.settings = settings
        self.security = HTTPBearer()
        self.security_headers = SecurityHeadersConfig()

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

            # Call next middleware
            response = await call_next(request)
            
            # Add security headers using existing config
            for header, value in self.security_headers.dict().items():
                if header.startswith("x_"):
                    header = header.replace("x_", "X-").upper()
                    response.headers[header] = value

            return response

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e),
            )
