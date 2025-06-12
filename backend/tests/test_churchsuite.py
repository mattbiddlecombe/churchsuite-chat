import pytest
import httpx
from unittest.mock import AsyncMock, patch
from datetime import datetime, timedelta
from backend.churchsuite.client import ChurchSuiteClient

# Mock responses
MOCK_ACCESS_TOKEN = "mock_access_token"
MOCK_REFRESH_TOKEN = "mock_refresh_token"
MOCK_TOKEN_EXPIRES_IN = 3600
MOCK_USER_TOKEN = "mock_user_token"
MOCK_QUERY = "John Doe"
MOCK_START_DATE = "2025-06-01"
MOCK_END_DATE = "2025-06-30"

@pytest.fixture
def mock_client():
    return ChurchSuiteClient(
        client_id="test_client_id",
        client_secret="test_client_secret",
        base_url="https://api.churchsuite.co.uk/v2"
    )

@pytest.fixture
def mock_response():
    mock = AsyncMock()
    mock.status_code = 200
    mock.json.return_value = {
        "access_token": MOCK_ACCESS_TOKEN,
        "refresh_token": MOCK_REFRESH_TOKEN,
        "expires_in": MOCK_TOKEN_EXPIRES_IN
    }
    return mock

@pytest.fixture
def mock_httpx_client(mock_response):
    with patch("httpx.AsyncClient") as mock:
        mock.return_value = AsyncMock()
        mock.return_value.post.return_value = mock_response
        mock.return_value.request.return_value = mock_response
        yield mock

async def test_get_authorization_url(mock_client):
    redirect_uri = "https://example.com/callback"
    state = "test_state"
    url = await mock_client.get_authorization_url(redirect_uri, state)
    assert f"client_id={mock_client.client_id}" in url
    assert f"redirect_uri={redirect_uri}" in url
    assert f"state={state}" in url
    assert "scope=read" in url

async def test_exchange_code_for_tokens(mock_httpx_client, mock_client, mock_response):
    code = "test_code"
    redirect_uri = "https://example.com/callback"
    
    result = await mock_client.exchange_code_for_tokens(code, redirect_uri)
    
    mock_httpx_client.return_value.post.assert_called_once()
    assert result["access_token"] == MOCK_ACCESS_TOKEN
    assert result["refresh_token"] == MOCK_REFRESH_TOKEN
    assert result["expires_in"] == MOCK_TOKEN_EXPIRES_IN

async def test_refresh_access_token(mock_httpx_client, mock_client, mock_response):
    mock_client.refresh_token = MOCK_REFRESH_TOKEN
    
    result = await mock_client.refresh_access_token()
    
    mock_httpx_client.return_value.post.assert_called_once()
    assert result["access_token"] == MOCK_ACCESS_TOKEN
    assert result["expires_in"] == MOCK_TOKEN_EXPIRES_IN

async def test_get_access_token(mock_httpx_client, mock_client, mock_response):
    mock_client.refresh_token = MOCK_REFRESH_TOKEN
    token = await mock_client.get_access_token()
    assert token == MOCK_ACCESS_TOKEN

async def test_search_people(mock_httpx_client, mock_client, mock_response):
    mock_client.access_token = MOCK_ACCESS_TOKEN
    result = await mock_client.search_people(MOCK_QUERY, MOCK_USER_TOKEN)
    
    mock_httpx_client.return_value.request.assert_called_once_with(
        "GET",
        f"{mock_client.base_url}/addressbook/people",
        params={"search": MOCK_QUERY},
        headers={
            "Authorization": f"Bearer {MOCK_ACCESS_TOKEN}",
            "Accept": "application/json",
            "x-user-token": MOCK_USER_TOKEN
        }
    )

async def test_list_groups(mock_httpx_client, mock_client, mock_response):
    mock_client.access_token = MOCK_ACCESS_TOKEN
    result = await mock_client.list_groups(MOCK_USER_TOKEN)
    
    mock_httpx_client.return_value.request.assert_called_once()
    args, kwargs = mock_httpx_client.return_value.request.call_args
    assert args[0] == "GET"
    assert args[1] == f"{mock_client.base_url}/smallgroups/groups"
    assert kwargs["headers"]["Authorization"] == f"Bearer {MOCK_ACCESS_TOKEN}"
    assert kwargs["headers"]["Accept"] == "application/json"
    assert kwargs["headers"]["x-user-token"] == MOCK_USER_TOKEN

async def test_list_events(mock_httpx_client, mock_client, mock_response):
    mock_client.access_token = MOCK_ACCESS_TOKEN
    result = await mock_client.list_events(MOCK_START_DATE, MOCK_END_DATE, MOCK_USER_TOKEN)
    
    mock_httpx_client.return_value.request.assert_called_once_with(
        "GET",
        f"{mock_client.base_url}/calendar/events",
        params={"start_date": MOCK_START_DATE, "end_date": MOCK_END_DATE},
        headers={
            "Authorization": f"Bearer {MOCK_ACCESS_TOKEN}",
            "Accept": "application/json",
            "x-user-token": MOCK_USER_TOKEN
        }
    )

async def test_token_refresh(mock_httpx_client, mock_client, mock_response):
    # Make first request fail with 401
    mock_httpx_client.return_value.request.return_value = AsyncMock()
    mock_httpx_client.return_value.request.return_value.status_code = 401
    mock_httpx_client.return_value.request.return_value.json.return_value = {"error": "Unauthorized"}
    
    # Make second request succeed
    mock_httpx_client.return_value.request.return_value = mock_response
    
    mock_client.refresh_token = MOCK_REFRESH_TOKEN
    mock_client.access_token = "expired_token"
    mock_client.token_expires_at = datetime.now() - timedelta(seconds=1)
    
    await mock_client.search_people(MOCK_QUERY, MOCK_USER_TOKEN)
    
    # Verify token was refreshed
    assert mock_client.access_token == MOCK_ACCESS_TOKEN
    
    # Verify refresh token was called
    mock_httpx_client.return_value.post.assert_called_with(
        f"{mock_client.base_url}/oauth/token",
        data={
            "client_id": mock_client.client_id,
            "client_secret": mock_client.client_secret,
            "grant_type": "refresh_token",
            "refresh_token": MOCK_REFRESH_TOKEN
        }
    )
