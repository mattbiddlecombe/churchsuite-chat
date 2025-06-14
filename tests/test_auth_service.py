import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta, timezone
import httpx
from httpx import AsyncClient
from src.services.auth_service import AuthService, OAuth2Config, OAuth2Token

@pytest.fixture
def mock_auth_service():
    return AuthService(OAuth2Config(
        token_url="https://login.churchsuite.com/oauth2/token",
        client_id="test_client_id",
        client_secret="test_client_secret"
    ))

@pytest.fixture
def mock_token_data():
    return {
        "access_token": "test_token",
        "token_type": "Bearer",
        "expires_in": 3600
    }

@pytest.fixture
def mock_http_client(raise_exception: bool = False):
    class MockResponse:
        def __init__(self, raise_exception: bool = False):
            self.json_data = {
                "access_token": "test_token",
                "token_type": "Bearer",
                "expires_in": 3600
            }
            self.raise_exception = raise_exception
            self.status_code = 200 if not raise_exception else 401
            self.reason_phrase = "OK" if not raise_exception else "Unauthorized"
            self.url = "https://login.churchsuite.com/oauth2/token"
            self.headers = {}
            
        async def json(self):
            return self.json_data
            
        async def raise_for_status(self):
            if self.raise_exception:
                raise httpx.HTTPStatusError(
                    f"Client error '{self.status_code} {self.reason_phrase}' for url '{self.url}'\nFor more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/{self.status_code}",
                    request=httpx.Request("POST", self.url),
                    response=self
                )

    class MockClient:
        def __init__(self, raise_exception: bool = False):
            self._response = MockResponse(raise_exception)
            self.post_called = False
            
        async def post(self, *args, **kwargs):
            self.post_called = True
            return self._response
            
        async def __aenter__(self):
            return self
            
        async def __aexit__(self, *args):
            pass
            
        def reset(self):
            self.post_called = False

    def create_mock_client(raise_exception: bool = False):
        return MockClient(raise_exception)

    return create_mock_client

@pytest.fixture
def mock_token_data():
    return {
        "access_token": "test_token",
        "token_type": "Bearer",
        "expires_in": 3600
    }

@pytest.mark.asyncio
async def test_get_token_success(mock_auth_service, mock_http_client, mock_token_data):
    # Test
    with patch('httpx.AsyncClient', return_value=mock_http_client(raise_exception=False)):
        token = await mock_auth_service.get_token()
        
        # Verify
        assert token.access_token == mock_token_data["access_token"]
        assert token.token_type == mock_token_data["token_type"]
        assert token.expires_in == mock_token_data["expires_in"]
        assert token.expires_at > datetime.now(timezone.utc)

@pytest.mark.asyncio
async def test_get_token_failure(mock_auth_service, mock_http_client):
    # Test
    with patch('httpx.AsyncClient', return_value=mock_http_client(raise_exception=True)):
        with pytest.raises(Exception) as exc_info:
            await mock_auth_service.get_token()
        assert str(exc_info.value) == "Failed to get token: Client error '401 Unauthorized' for url 'https://login.churchsuite.com/oauth2/token'\nFor more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/401"

@pytest.mark.asyncio
async def test_token_caching(mock_auth_service, mock_http_client, mock_token_data):
    # First call should get new token
    mock_client = mock_http_client(raise_exception=False)
    with patch('httpx.AsyncClient', return_value=mock_client):
        token1 = await mock_auth_service.get_token()
        assert mock_client.post_called
        mock_client.reset()

    # Second call should return cached token
    mock_client = mock_http_client(raise_exception=False)
    with patch('httpx.AsyncClient', return_value=mock_client):
        token2 = await mock_auth_service.get_token()
        assert token1 == token2
        assert not mock_client.post_called

    # Force token refresh by setting expiry
    mock_auth_service._token.expires_in = -60
    mock_client = mock_http_client(raise_exception=False)
    with patch('httpx.AsyncClient', return_value=mock_client):
        token3 = await mock_auth_service.get_token()
        assert token3 != token1
        assert mock_client.post_called

@pytest.mark.asyncio
async def test_token_validation(mock_auth_service):
    # Test successful validation
    mock_auth_service._token = OAuth2Token(
        access_token="test_token",
        token_type="Bearer",
        expires_in=3600
    )
    assert await mock_auth_service.validate_token("test_token")
    
    # Test failed validation
    mock_auth_service._token = None
    assert not await mock_auth_service.validate_token("invalid_token")
