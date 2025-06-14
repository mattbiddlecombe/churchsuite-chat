# ChurchSuite Chatbot Task List

## Document Information

- **Last Updated:** 14 Jun 2025
- **Version:** v0.1.2

## Completed Tasks

- [x] Set up project structure with proper package organization
- [x] Configure OpenAI integration with GPT-3.5-turbo
- [x] Create basic chat endpoint
- [x] Add logging infrastructure
- [x] Set up GitHub repository
- [x] Update documentation
- [x] Implement function calling with OpenAI
- [x] Integrate ChurchSuite API endpoints
- [x] Add proper error handling
- [x] Implement request validation
- [x] Reimplement JWT authentication with FastAPI
- [x] Add comprehensive unit tests for authentication endpoints
- [x] Add session management and token validation
- [x] Add error handling for invalid client configurations
- [x] Create test_auth.py with passing authentication tests
- [x] Implement proper CORS headers
- [x] Add token refresh mechanism
- [x] Fix timezone handling in token expiration
- [x] Add proper error handling for OpenAPI endpoints
- [x] Set up FastAPI project structure
- [x] Migrate core dependencies
- [x] Implement FastAPI middleware system
- [x] Set up proper testing infrastructure
- [x] Migrate authentication endpoints
- [x] Migrate rate limiting
- [x] Migrate security middleware
- [x] Update endpoint schemas
- [x] Add JWT token validation middleware
- [x] Add proper security headers
- [x] Add CSRF protection
- [x] Implement request validation schemas
- [x] Add input sanitization for all endpoints
- [x] Implement CORS policy configuration
- [x] Add security headers
- [x] Implement rate limiting per user
- [x] Add secure cookie handling
- [x] Validate `.env.example` consistency
- [x] Add comprehensive audit logging
- [x] Add proper error handling for OpenAPI endpoints
- [x] Create test_security.py
- [x] Test JWT validation
- [x] Test session management
- [x] Test rate limiting
- [x] Test input validation
- [x] Test CSRF protection

## Current Tasks

### FastAPI Migration Cleanup

- [ ] Remove SessionMiddleware completely
- [ ] Update middleware to use FastAPI's Middleware class
- [ ] Replace BaseHTTPMiddleware with FastAPI patterns
- [ ] Update security headers to use FastAPI response headers
- [ ] Replace Starlette test client with FastAPI TestClient
- [ ] Update test fixtures to use FastAPI async patterns
- [ ] Remove Starlette types (ASGIApp, Receive, Scope, Send)
- [ ] Update auth endpoints to use FastAPI state management
- [ ] Remove JWTMiddleware class (using FastAPI dependency instead)

### Task Discipline Policy

- All tasks must be completed and tested before progressing to the next one.
- Unit tests should be included for all new or modified functionality.
- Exceptions must be clearly logged in `DECISIONS.md` with a plan for follow-up.
- Partial or exploratory implementations should be flagged and isolated.
- All FastAPI migration tasks must be completed before proceeding with new features.

### Security Enhancements

- [ ] Implement token blacklist for logout functionality
- [ ] Finalize security headers configuration
- [ ] Add comprehensive audit logging (enhanced)
- [ ] Add rate limiting per user (enhanced)

### CI/CD Pipeline

- [ ] GitHub Actions workflow for main/master branches
- [ ] Automated testing with coverage
- [ ] Linting with pylint
- [ ] Code coverage reporting to Codecov
- [ ] Deployment to Railway
- [ ] Enforce that all merged PRs must include passing tests for the task implemented

### Chat Endpoint Integration Tests

- [ ] Create test_chat_endpoint.py
- [ ] Test message processing
- [ ] Test function call integration
- [ ] Test error handling
- [ ] Test permission boundaries

## Future Tasks

### ChurchSuite API Integrations

- [ ] Add attendance tracking
- [ ] Add giving history
- [ ] Add ministry management
- [ ] Add site management
- [ ] Add attendance recording (v1+)
- [ ] Add note creation (v1+)

### Frontend Development

- [ ] Set up Next.js project
- [ ] Implement chat interface
- [ ] Add authentication UI
- [ ] Add loading states

### Deployment & Monitoring

- [ ] Set up Railway deployment
- [ ] Configure environment variables
- [ ] Set up secrets management
- [ ] Add deployment pipeline
- [ ] Integrate test coverage enforcement in CI
- [ ] Add logging configuration
- [ ] Set up error tracking
- [ ] Add performance monitoring
- [ ] Add usage analytics

## Technical Stack

- Backend: FastAPI (Python 3.13)
- OpenAI: GPT-3.5-turbo
- HTTP Client: HTTPX
- Testing: Pytest with async support
- Logging: Structured logging with audit trails
- Database: Optional vector store (Qdrant)
