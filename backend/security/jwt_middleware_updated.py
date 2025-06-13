from datetime import datetime, timedelta
from typing import Dict, Optional, Any, Callable, TypeVar
from jose import jwt, JWTError
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import Scope, Receive, Send, ASGIApp
import os
from dotenv import load_dotenv
import secrets
from datetime import timezone
import logging
import json

load_dotenv()

# Load JWT secret from environment
JWT_SECRET = os.getenv("JWT_SECRET", secrets.token_hex(32))
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_MINUTES = 30

class JWTMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        # Store the send function for later use
        original_send = send
        
        # Create a wrapped send function that uses original_send
        async def wrapped_send(message):
            await original_send(message)
        
        if scope["type"] != "http":
            await self.app(scope, receive, wrapped_send)
            return

        # Skip auth endpoints
        if scope["path"] in ["/auth/start", "/auth/callback", "/auth/refresh"]:
            await self.app(scope, receive, wrapped_send)
            return

        # Get token from Authorization header
        headers = dict(scope.get("headers", []))
        auth_header = headers.get(b"authorization") or headers.get("authorization")
        
        if not auth_header:
            await self._send_error(wrapped_send, "Missing Authorization header")
            return
            
        try:
            # Extract token from header
            if not auth_header.startswith(b"Bearer "):
                await self._send_error(wrapped_send, "Invalid token format")
                return
            
            token = auth_header[7:]  # Remove "Bearer " prefix
            
            # Validate token
            try:
                payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
                scope["user"] = payload
                await self.app(scope, receive, wrapped_send)
                return
            except jwt.ExpiredSignatureError:
                await self._send_error(wrapped_send, "Token has expired")
                return
            except jwt.JWTError as e:
                await self._send_error(wrapped_send, f"Invalid token: {str(e)}")
                return
        except Exception as e:
            await self._send_error(wrapped_send, f"Invalid token: {str(e)}")
            return

    async def _send_error(self, send: Send, error_message: str):
        error_response = {
            "type": "http.response.start",
            "status": 401,
            "headers": [
                [b"content-type", b"application/json"],
                [b"x-content-type-options", b"nosniff"],
                [b"x-frame-options", b"DENY"],
                [b"x-xss-protection", b"1; mode=block"],
                [b"access-control-allow-origin", b"*"],
                [b"access-control-allow-credentials", b"true"],
                [b"access-control-allow-headers", b"content-type, authorization, x-csrf-token"]
            ]
        }
        await send(error_response)
        await send({
            "type": "http.response.body",
            "body": json.dumps({"error": error_message}).encode(),
            "more_body": False
        })
        return
