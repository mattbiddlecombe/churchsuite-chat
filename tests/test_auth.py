import pytest
from httpx import AsyncClient
from backend.schemas.requests import AuthRequest

@pytest.mark.asyncio
async def test_auth_start(async_client):
    """Test the auth start endpoint"""
    response = await async_client.get('/auth/start')
    assert response.status_code == 200
    assert response.headers['content-type'] == 'application/json'
    data = response.json()
    assert 'authorization_url' in data
    assert 'state' in data

@pytest.mark.asyncio
async def test_auth_callback_success(async_client):
    """Test successful auth callback"""
    response = await async_client.get(
        '/auth/callback',
        params={'code': 'test_code', 'state': 'test_state'}
    )
    assert response.status_code == 200
    assert response.headers['content-type'] == 'application/json'
    data = response.json()
    assert 'access_token' in data
    assert 'refresh_token' in data

@pytest.mark.asyncio
async def test_auth_callback_error(async_client):
    """Test auth callback with error"""
    response = await async_client.get(
        '/auth/callback',
        params={'error': 'access_denied'}
    )
    assert response.status_code == 400
    assert response.headers['content-type'] == 'application/json'
    data = response.json()
    assert 'error' in data
    assert 'detail' in data
