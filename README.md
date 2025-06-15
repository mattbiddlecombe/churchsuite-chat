# ChurchSuite Chatbot

A secure AI chat assistant that integrates with ChurchSuite to provide read-only access to church data while respecting user permissions.

## Features

- Secure authentication using ChurchSuite OAuth2
- Read-only access to ChurchSuite data
- AI-powered chat interface using OpenAI's GPT-3.5-turbo
- Respect for user permissions and data access restrictions
- Optional vector store caching for improved performance
- Built with FastAPI for modern, high-performance API development
- Pure FastAPI-native JWT authentication
- Comprehensive security headers (including Cache-Control, Pragma, and Expires)
- CSRF protection with token validation
- Rate limiting per user
- Token blacklist for logout functionality
- Comprehensive audit logging
- Secure cookie handling with proper attributes (HttpOnly, Secure, SameSite=Lax)
- Input sanitization middleware protecting against XSS and SQL injection attacks

## Security Features

### Input Sanitizer Middleware

The application includes a robust input sanitizer middleware that:

1. Validates and sanitizes all incoming request inputs
2. Protects against Cross-Site Scripting (XSS) attacks by detecting and blocking script tags and event handlers
3. Prevents SQL injection by detecting and rejecting suspicious SQL patterns
4. Handles multiple input types:
   1. Query parameters
   2. Request headers (excluding sensitive headers like Authorization)
   3. JSON request bodies
   4. Form data (both URL-encoded and multipart)
5. Returns clear error messages for invalid inputs
6. Applies security headers to all responses:
   1. X-Content-Type-Options: nosniff
   2. X-Frame-Options: DENY
   3. X-XSS-Protection: 1; mode=block
   4. Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'

### Authentication & Authorization

The application implements a secure authentication system that:

1. Uses OAuth2 Authorization Code flow with ChurchSuite
2. Implements CSRF protection with state parameter validation
3. Uses JWT tokens for session management
4. Stores session state securely in Redis
5. Implements token blacklist for logout functionality
6. Adds proper error handling for invalid tokens
7. Uses secure cookie handling with proper attributes:
   - HttpOnly: true
   - Secure: true
   - SameSite: lax
   - Proper expiration handling

### Error Handling

The middleware provides consistent error messages for different types of validation failures:

1. "Invalid input detected in query parameter" for XSS in query parameters
2. "Invalid input detected in header" for XSS in headers
3. "Potential XSS attack detected" for script tag detection
4. "Potential SQL injection detected" for SQL pattern detection
5. "Invalid JSON data" for malformed JSON
6. "Invalid form data" for invalid form submissions
7. "Invalid JSON in request body" for JSON parsing errors

### Customization

The input sanitizer can be configured with custom patterns:

```python
from backend.security.input_sanitizer import XSSPatterns, SQLInjectionPatterns

# Custom XSS patterns
xss_patterns = XSSPatterns(script_tags=[
    r'<script>.*?</script>',
    r'on\w+\s*=.*?',
    # Add custom patterns here
])

# Custom SQL injection patterns
sql_patterns = SQLInjectionPatterns(patterns=[
    r'\b(SELECT|UPDATE|DELETE|DROP)\b',
    # Add custom patterns here
])

# Add to FastAPI app
from backend.security.input_sanitizer import add_input_sanitizer
add_input_sanitizer(app, xss_patterns, sql_patterns)
```

## Prerequisites

- Python 3.12+
- ChurchSuite account with appropriate permissions
- OpenAI API key
- (Optional) Qdrant vector database for caching

## Setup

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Copy `.env.example` to `.env` and fill in your configuration:

```bash
cp .env.example .env
```

3. Start the development server:

```bash
uvicorn backend.main:app --reload
```

4. Run tests to verify installation:

```bash
pytest tests/ -v
```

## Security Features

The application implements several security measures:

- **Authentication:** FastAPI-native JWT authentication with:
  - Proper middleware integration
  - Secure token validation
  - Proper error handling
  - CSRF protection integration
  - Security headers enforcement
- **CSRF Protection:** Token-based CSRF protection with secure cookie handling
- **Security Headers:** Comprehensive security headers including:
  - Content Security Policy
  - XSS Protection
  - Frame Options
  - Strict Transport Security
  - Cache Control
  - CORS Headers
- **Rate Limiting:** Per-user rate limiting to prevent abuse
- **Audit Logging:** Comprehensive logging of all security-relevant events
- **Secure Cookies:** Cookies are marked as HttpOnly, Secure, and use SameSite=Lax protection

## Project Structure

```
churchsuite-chat/
├── backend/           # FastAPI server
│   ├── churchsuite/   # ChurchSuite integration
│   │   ├── client.py  # API client
│   │   └── schemas.py # Pydantic models
│   ├── llm/          # LLM integration
│   │   ├── prompt.py # System prompts
│   │   └── tools.py  # Function schemas
│   ├── security/     # Authentication
│   │   ├── jwt_middleware_native.py # JWT utilities (FastAPI-native)
│   │   ├── middleware/      # FastAPI middleware
│   │   └── tests/          # Security tests
│   └── main.py       # FastAPI app
├── frontend/         # Next.js application
│   └── app/          # React components
├── tests/           # Test suite
│   ├── unit/        # Unit tests
│   └── integration/ # Integration tests
└── docs/            # Documentation
```

## Security

- Pure FastAPI-native JWT authentication
- Token verification with proper expiration handling
- CORS headers configured for secure cross-origin requests
- Token management follows security best practices
- Sensitive data is properly masked and sanitized
- Comprehensive audit logging is implemented
- CSRF protection implemented
- Rate limiting per user
- Token blacklist for logout functionality
- **Backend:** FastAPI (Python 3.13) server implemented
  - OpenAI integration with GPT-3.5-turbo complete
  - Basic chat endpoint with function calling operational
  - Structured JSON audit logging implemented
  - GitHub repository active at https://github.com/mattbiddlecombe/churchsuite-chat
  - Function calling with OpenAI integrated
  - OAuth2 Client Credentials authentication implemented
  - **Resolved:** Schema structure split issues
  - **Resolved:** Middleware implementation issues
    - Using FastAPI's native @app.middleware("http") pattern
    - Removed Starlette BaseHTTPMiddleware
    - Implemented proper async/await patterns
  - **Resolved:** Authentication system reimplementation
    - Migrated JWT middleware to FastAPI-native patterns
    - Integrated with security headers and CSRF protection
    - Added proper test coverage
  - **Resolved:** Test coverage restoration
  - **Resolved:** Audit logging implementation issues
  - **Resolved:** Rate limit middleware implementation issues
  - **Resolved:** Security middleware migration
    - Migrated from Starlette to FastAPI-native middleware
    - Implemented proper security headers
    - Added CSRF protection with token validation
    - Fixed cookie attribute validation
    - Added comprehensive test coverage

## Authentication Flow

1. User authenticates with ChurchSuite credentials using OAuth2
2. JWT token is generated with proper expiration
3. Token is verified on protected endpoints using FastAPI dependencies
4. User data is returned with proper CORS and security headers
5. Token refresh mechanism implemented using FastAPI state management
6. Comprehensive error handling for authentication failures
7. CSRF protection on all authenticated endpoints
8. Token blacklist for logout functionality
9. Comprehensive audit logging for security events
10. Rate limiting per user implemented

## Migration Status

The project has successfully completed its migration from Starlette to FastAPI-native patterns:

- All authentication now uses FastAPI's dependency injection
- All middleware has been updated to use FastAPI patterns
- All testing uses FastAPI's TestClient
- All security headers use FastAPI response patterns
- All session management uses FastAPI state
- All JWT handling uses FastAPI-native patterns

## Next Steps

- Complete FastAPI migration cleanup
- Finalize security enhancements
- Add comprehensive audit logging
- Improve rate limiting implementation
- Add end-to-end tests for OAuth2 flows
- Update all documentation to reflect FastAPI patterns

## Project Structure

```
churchsuite-chat/
├── backend/           # FastAPI server
│   ├── churchsuite/   # ChurchSuite integration
│   │   ├── client.py  # API client
│   │   └── schemas.py # Pydantic models
│   ├── llm/          # LLM integration
│   │   ├── prompt.py # System prompts
│   │   └── tools.py  # Function schemas
│   ├── security/     # Authentication
│   │   └── jwt_middleware_native.py # JWT utilities (FastAPI-native)
│   ├── routers/      # API routes
│   │   └── auth.py   # Authentication endpoints
│   └── main.py       # FastAPI app
├── frontend/         # Next.js application
│   └── app/          # React components
├── tests/           # Test suite
│   ├── unit/        # Unit tests
│   └── integration/ # Integration tests
└── docs/            # Documentation
```

## Development Setup

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Copy `.env.example` to `.env` and fill in your configuration:

```bash
cp .env.example .env
```

3. Start the development server:

```bash
uvicorn backend.main:app --reload
```

4. Run tests to verify installation:

```bash
pytest tests/ -v
```

## Testing

The project includes comprehensive tests for:

- JWT authentication flow
- Protected endpoints
- CORS header handling
- OpenAPI documentation
- Error handling

## Contributing

Please read the [CONTRIBUTING.md](CONTRIBUTING.md) file for guidelines on contributing to this project.

## Contributing

Please read the [CONTRIBUTING.md](CONTRIBUTING.md) file for guidelines on contributing to this project.
