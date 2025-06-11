import httpx
from typing import Dict, Any, Optional
from datetime import datetime
import logging
from datetime import timedelta

logger = logging.getLogger(__name__)

class ChurchSuiteClient:
    def __init__(self, client_id: str, client_secret: str, base_url: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.base_url = base_url
        self.access_token: Optional[str] = None
        self.token_expires_at: Optional[datetime] = None
        self.client = httpx.AsyncClient()

    async def get_access_token(self) -> str:
        """Get OAuth2 access token from ChurchSuite"""
        if not self.access_token or datetime.now() >= self.token_expires_at:
            auth_data = {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "grant_type": "client_credentials"
            }
            
            response = await self.client.post(
                f"{self.base_url}/oauth/token",
                data=auth_data
            )
            
            if response.status_code != 200:
                raise Exception(f"Failed to get access token: {response.text}")
                
            token_data = response.json()
            self.access_token = token_data["access_token"]
            self.token_expires_at = datetime.now() + timedelta(seconds=token_data["expires_in"])
            
        return self.access_token

    async def make_request(self, method: str, endpoint: str, 
                         params: Optional[Dict] = None, 
                         headers: Optional[Dict] = None) -> Dict:
        """Make a request to the ChurchSuite API"""
        if not headers:
            headers = {}
            
        headers["Authorization"] = f"Bearer {await self.get_access_token()}"
        headers["Accept"] = "application/json"

        response = await self.client.request(
            method,
            f"{self.base_url}/{endpoint}",
            params=params,
            headers=headers
        )

        if response.status_code != 200:
            logger.error(f"ChurchSuite API error: {response.status_code} - {response.text}")
            raise Exception(f"ChurchSuite API error: {response.status_code} - {response.text}")

        return response.json()

    async def search_people(self, query: str, user_token: str) -> Dict:
        """Search for people in the address book"""
        headers = {
            "x-user-token": user_token
        }
        return await self.make_request(
            "GET",
            "addressbook/people",
            params={"search": query},
            headers=headers
        )

    async def list_groups(self, user_token: str) -> Dict:
        """List groups visible to the user"""
        headers = {
            "x-user-token": user_token
        }
        return await self.make_request(
            "GET",
            "smallgroups/groups",
            headers=headers
        )

    async def list_events(self, start_date: str, end_date: str, user_token: str) -> Dict:
        """List events within a date range"""
        headers = {
            "x-user-token": user_token
        }
        return await self.make_request(
            "GET",
            "calendar/events",
            params={"start_date": start_date, "end_date": end_date},
            headers=headers
        )

    async def get_my_profile(self, user_token: str) -> Dict:
        """Get the current user's profile"""
        headers = {
            "x-user-token": user_token
        }
        return await self.make_request(
            "GET",
            "people/me",
            headers=headers
        )
        headers = {
            "x-user-token": user_token
        }
        return await self.make_request(
            "GET",
            "addressbook/me",
            headers=headers
        )

    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()
