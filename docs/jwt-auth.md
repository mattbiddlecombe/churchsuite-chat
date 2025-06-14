# JWT Authentication Implementation

## Overview

The ChurchSuite Chatbot implements secure JWT-based authentication using FastAPI's dependency injection system. This document outlines the implementation details of the authentication system.

## Key Components

### JWT Middleware
Located in `backend/security/jwt_middleware.py`, this module provides:

- Token creation with proper expiration handling
- Token verification with error handling
- FastAPI dependency injection for protected endpoints
- Proper timezone handling for token expiration

### Authentication Router
Located in `backend/routers/auth.py`, this router provides:

- `/token` endpoint for obtaining JWT tokens
- `/me` endpoint for getting user data
- `/refresh` endpoint for refreshing tokens
- Proper error handling and response formats

### CORS Configuration
CORS headers are configured in `backend/main.py` to:

- Allow cross-origin requests
- Support credentials
- Expose necessary headers
- Include proper Vary header

## Token Flow

1. User authenticates with valid credentials
2. `/token` endpoint generates JWT with:
   - `sub` claim for user identifier
   - Proper expiration timestamp
   - Secure signature
3. Protected endpoints use `get_current_user` dependency
4. Token verification checks:
   - Token signature
   - Token expiration
   - Required claims
5. Token refresh mechanism allows secure token renewal

## Security Features

- Tokens have proper expiration
- Token verification is strict
- CORS headers are secure
- Error handling is consistent
- All endpoints are properly protected

## Testing

The authentication system is thoroughly tested in:

- `tests/test_auth.py`
- `tests/test_main.py`

Tests cover:
- Token creation
- Token verification
- Protected endpoints
- Error handling
- CORS headers
- Token refresh

## Configuration

JWT configuration is managed through environment variables in `backend/config.py`:

- JWT_SECRET: Secret key for token signing
- JWT_ALGORITHM: Algorithm used for signing
- JWT_EXPIRATION: Token expiration time

## Error Handling

All authentication endpoints return proper HTTP error codes:

- 401 Unauthorized for invalid tokens
- 403 Forbidden for insufficient permissions
- 400 Bad Request for invalid input
- 500 Internal Server Error for unexpected issues

## Future Improvements

- Add token blacklist for logout functionality
- Implement token refresh rotation
- Add rate limiting for authentication endpoints
- Add more detailed logging for security events
