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
- Comprehensive security headers
- CSRF protection
- Rate limiting per user
- Token blacklist for logout functionality
- Comprehensive audit logging

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
│   │   ├── jwt_middleware.py # JWT utilities
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
│   │   └── jwt_middleware.py # JWT utilities
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
