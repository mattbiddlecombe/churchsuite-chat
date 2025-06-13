# ChurchSuite Chatbot Task List

## Document Information

- **Last Updated:** 11 Jun 2025
- **Version:** v0.1

## Completed Tasks

- [x] Set up project structure with proper package organization
- [x] Implement basic Starlette server
- [x] Configure OpenAI integration with GPT-3.5-turbo
- [x] Create basic chat endpoint
- [x] Add logging infrastructure
- [x] Set up GitHub repository
- [x] Update documentation
- [x] Implement function calling with OpenAI
- [x] Integrate ChurchSuite API endpoints
- [x] Add proper error handling
- [x] Implement request validation

## Task Discipline Policy

- All tasks must be completed and tested before progressing to the next one.
- Unit tests should be included for all new or modified functionality.
- Exceptions must be clearly logged in `DECISIONS.md` with a plan for follow-up.
- Partial or exploratory implementations should be flagged and isolated.

## Current Tasks

- [x] Add ChurchSuite OAuth2 authentication
  - Implemented OAuth2 flow with ChurchSuite
  - Added comprehensive unit tests for authentication endpoints
  - Added session management and token validation
  - Added error handling for invalid client configurations
  - Created test_auth.py with passing authentication tests
- [x] Add rate limiting
  - Implemented in-memory rate limiting with 60 requests per minute
  - Added test endpoint and unit tests
  - Configurable rate limits and window sizes
  - Skips auth endpoints
- [x] Set up CI/CD pipeline
- GitHub Actions workflow for main/master branches
- Automated testing with coverage
- Linting with pylint
- Code coverage reporting to Codecov
- Deployment to Railway
- Enforce that all merged PRs must include passing tests for the task implemented
- [ ] Implement security measures
  - [ ] Add JWT token validation middleware
  - [ ] Implement request validation schemas
  - [ ] Add input sanitization for all endpoints
  - [ ] Implement CORS policy configuration
  - [ ] Add security headers (X-Content-Type-Options, X-Frame-Options, etc.)
  - [ ] Implement rate limiting per user
  - [ ] Add secure cookie handling
  - [ ] Implement CSRF protection
  - [ ] Validate `.env.example` consistency
- [ ] Chat Endpoint Integration Tests

  - [ ] Create test_chat_endpoint.py
  - [ ] Test message processing
  - [ ] Test function call integration
  - [ ] Test error handling
  - [ ] Test permission boundaries

- [ ] Security Tests
  - [ ] Create test_security.py
  - [ ] Test JWT validation
    - [ ] Confirm test passes in CI
  - [ ] Test session management
    - [ ] Confirm test passes in CI
  - [ ] Test rate limiting
    - [ ] Confirm test passes in CI
  - [ ] Test input validation
    - [ ] Confirm test passes in CI
  - [ ] Test CSRF protection
    - [ ] Confirm test passes in CI

## Future Tasks

- [ ] ChurchSuite API Integrations

  - [ ] Add attendance tracking
  - [ ] Add giving history
  - [ ] Add ministry management
  - [ ] Add site management

- [ ] Write Operations (v1+)

  - [ ] Add attendance recording
  - [ ] Add note creation
  - [ ] Add event registration
  - [ ] Add group membership changes

- [ ] Frontend UI

  - [ ] Set up Next.js project
  - [ ] Implement chat interface
  - [ ] Add authentication UI
  - [ ] Add error handling
  - [ ] Add loading states

- [ ] Deployment

  - [ ] Set up Railway deployment
  - [ ] Configure environment variables
  - [ ] Set up secrets management
  - [ ] Add deployment pipeline
  - [ ] Integrate test coverage enforcement in CI (e.g. fail build if coverage drops)

- [ ] Monitoring & Analytics
  - [ ] Add logging configuration
  - [ ] Set up error tracking
  - [ ] Add performance monitoring
  - [ ] Add usage analytics

## Technical Stack

- Backend: Starlette (Python 3.13)
- OpenAI: GPT-3.5-turbo
- HTTP Client: HTTPX
- Testing: Pytest with async support
- Logging: Structured logging with audit trails
- Database: Optional vector store (Qdrant)
