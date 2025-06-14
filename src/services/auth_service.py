from typing import Dict, Optional
import httpx
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel
from starlette.requests import Request

# OAuth2 Configuration
class OAuth2Config(BaseModel):
    token_url: str = "https://login.churchsuite.com/oauth2/token"
    client_id: str
    client_secret: str
    
    @classmethod
    def from_env(cls):
        """Create config from environment variables"""
        return cls(
            client_id="CS_CLIENT_ID",
            client_secret="CS_CLIENT_SECRET"
        )

class OAuth2Token(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    
    @property
    def expires_at(self) -> datetime:
        return datetime.now(timezone.utc) + timedelta(seconds=self.expires_in)

    @classmethod
    def from_response(cls, response: dict):
        """Create OAuth2Token from API response"""
        return cls(
            access_token=str(response["access_token"]),
            token_type=str(response["token_type"]),
            expires_in=int(response["expires_in"])
        )

class AuthService:
    def __init__(self, config: OAuth2Config):
        self.config = config
        self._token: Optional[OAuth2Token] = None

    async def get_token(self) -> OAuth2Token:
        """Get a valid access token, refreshing if necessary"""
        if self._token and self._token.expires_at > datetime.now(timezone.utc):
            return self._token
            
        # Request new token
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.config.token_url,
                    auth=(self.config.client_id, self.config.client_secret),
                    headers={"Content-Type": "application/json"},
                    json={"grant_type": "client_credentials", "scope": "full_access"}
                )
                await response.raise_for_status()
                
                token_data = await response.json()
                self._token = OAuth2Token.from_response(token_data)
                return self._token
        except Exception as e:
            raise Exception(f"Failed to get token: {str(e)}") from e

    async def validate_token(self, token: str) -> bool:
        """Validate an access token"""
        try:
            # For now, we'll just check if we can get a new token
            await self.get_token()
            return True
        except Exception:
            return False

    async def validate_token(self, token: str) -> bool:
        """Validate an access token"""
        # For now, we'll just check if we can get a new token
        try:
            await self.get_token()
            return True
        except Exception:
            return False
