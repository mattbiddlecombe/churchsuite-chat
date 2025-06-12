from datetime import datetime, timedelta
from typing import Dict, Optional, Any
from jose import jwt, JWTError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import Message
import os
from dotenv import load_dotenv
import secrets
from datetime import timezone
import logging
from typing import Callable, Awaitable
from starlette.types import Receive, Scope, Send, Message
from starlette.datastructures import Headers
from starlette.routing import Match
import json

load_dotenv()

# Load JWT secret from environment
JWT_SECRET = os.getenv("JWT_SECRET", secrets.token_hex(32))
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_MINUTES = 30

class JWTMiddleware(BaseHTTPMiddleware):
    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)
        response = await self.dispatch(request, self.app)
        await response(scope, receive, send)

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[JSONResponse]]) -> JSONResponse:
        try:
            # Skip auth endpoints
            if request.url.path in ["/auth/start", "/auth/callback", "/auth/refresh"]:
                response = call_next(request)
                if isinstance(response, JSONResponse):
                    return response
                return JSONResponse(response, status_code=200)

            # Get token from Authorization header
            auth_header = request.headers.get("Authorization")
            if not auth_header:
                return JSONResponse(
                    {"error": "Missing Authorization header"},
                    status_code=401
                )

            try:
                token = auth_header.split(" ")[1]
            except IndexError:
                return JSONResponse(
                    {"error": "Invalid Authorization header format"},
                    status_code=401
                )

            # Verify token
            try:
                payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
                
                # Add user info to request state
                request.state = {"user": payload}
                
                # Check token expiration
                exp = payload.get("exp")
                if exp and datetime.fromtimestamp(exp, timezone.utc) < datetime.now(timezone.utc):
                    return JSONResponse(
                        {"error": "Token has expired"},
                        status_code=401
                    )

            except JWTError as e:
                if "Not enough segments" in str(e):
                    return JSONResponse(
                        {"error": "Invalid token: Not enough segments"},
                        status_code=401
                    )
                elif "Signature has expired" in str(e):
                    return JSONResponse(
                        {"error": "Token has expired"},
                        status_code=401
                    )
                else:
                    return JSONResponse(
                        {"error": f"Invalid token: {str(e)}"},
                        status_code=401
                    )

            # Handle the next middleware
            response = call_next(request)
            if isinstance(response, JSONResponse):
                return response
            return JSONResponse(response, status_code=200)

            # Get token from Authorization header
            auth_header = request.headers.get("Authorization")
            if not auth_header:
                return JSONResponse(
                    {"error": "Missing Authorization header"},
                    status_code=401
                )

            try:
                token = auth_header.split(" ")[1]
            except IndexError:
                return JSONResponse(
                    {"error": "Invalid Authorization header format"},
                    status_code=401
                )

            # Verify token
            try:
                payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
                
                # Add user info to request state
                request.state = {"user": payload}
                
                # Check token expiration
                exp = payload.get("exp")
                if exp and datetime.fromtimestamp(exp, timezone.utc) < datetime.now(timezone.utc):
                    return JSONResponse(
                        {"error": "Token has expired"},
                        status_code=401
                    )

            except JWTError as e:
                if "Not enough segments" in str(e):
                    return JSONResponse(
                        {"error": "Invalid token: Not enough segments"},
                        status_code=401
                    )
                elif "Signature has expired" in str(e):
                    return JSONResponse(
                        {"error": "Token has expired"},
                        status_code=401
                    )
                else:
                    return JSONResponse(
                        {"error": f"Invalid token: {str(e)}"},
                        status_code=401
                    )

            return await call_next(request)

        except Exception as e:
            logging.error(f"Authentication error: {str(e)}", exc_info=True)
            return JSONResponse(
                {"error": str(e)},
                status_code=500
            )
