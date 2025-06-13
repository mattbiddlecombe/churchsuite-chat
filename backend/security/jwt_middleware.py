from datetime import datetime, timedelta
from typing import Dict, Optional, Any
from jose import jwt, JWTError
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import Scope, Receive, Send
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
    def __init__(self, app):
        self.app = app
        if not hasattr(app, "__await__"):
            raise ValueError("App must be an async callable")

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        # Store the send function for later use
        original_send = send
        
        if scope["type"] != "http":
            await self.app(scope, receive, original_send)
            return

        # Skip auth endpoints
        if scope["path"] in ["/auth/start", "/auth/callback", "/auth/refresh"]:
            await self.app(scope, receive, original_send)
            return

        # Get token from Authorization header
        auth_header = None
        for header in scope["headers"]:
            if header[0] == b"authorization":
                auth_header = header[1]
                break
        if not auth_header:
            await self._send_error(original_send, "Missing Authorization header")
            return

        try:
            # Extract token from header
            auth_str = auth_header.decode()
            if not auth_str.startswith("Bearer "):
                raise ValueError("Invalid token format: Missing Bearer prefix")

            token = auth_str.split(" ")[1]
            if not token:
                raise ValueError("Invalid token format: Empty token")

            # Verify token
            try:
                payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
                
                # Add user info to scope
                scope["user"] = payload
                
                # Check token expiration
                exp = payload.get("exp")
                if exp and datetime.fromtimestamp(exp, timezone.utc) < datetime.now(timezone.utc):
                    await self._send_error(original_send, "Token has expired")
                    return

                # Token is valid, pass to downstream app
                await self.app(scope, receive, original_send)
                return

            except JWTError as e:
                raise ValueError(f"Invalid token: {str(e)}")
            except Exception as e:
                logging.error(f"JWT Middleware Error: {str(e)}")
                raise ValueError(f"Unexpected error: {str(e)}")

        except ValueError as e:
            await self._send_error(original_send, str(e))
            return

    async def _send_error(self, send: Send, error_message: str):
        await send({
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
        })
        await send({
            "type": "http.response.body",
            "body": json.dumps({"error": error_message}).encode(),
            "more_body": False
        })
