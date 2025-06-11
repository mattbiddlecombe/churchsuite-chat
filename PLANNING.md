# ChurchSuite Chatbot Planning Document

## Document Information
- **Last Updated:** 11 Jun 2025
- **Version:** v0 draft

## 1. Purpose & Vision

Create a secure, read-only AI chat assistant that answers staff and congregant questions using live ChurchSuite data, respecting each user's existing ChurchSuite permissions. Future versions will allow limited write operations behind additional safeguards.

## 2. Core Constraints

| Constraint | Rationale |
|------------|-----------|
| Must never expose data the caller cannot normally view in ChurchSuite | GDPR & pastoral privacy |
| Authenticate with ChurchSuite login (OAuth2 Authorisation Code flow) | Leverage built-in roles & permissions |
| Read-only for v0 | Simplifies risk profile while we validate UX |
| Files < 500 LOC | Maintainability |
| Python 3.12, FastAPI, Pydantic v2 | Modern, type-safe stack |
| Vector-RAG optional & per-user | Cache only what the current user is allowed to read |

## 3. Tech Stack

- Frontend: Next.js 14 + React Server Components + shadcn/ui chat widget (SSR, streamed)
- Gateway API: FastAPI running behind ASGI (uvicorn), handles auth, rate-limiting, logging
- LLM provider: OpenAI GPT-4o (function-calling) via Azure OpenAI
- Vector store (optional): Qdrant (Docker) with per-user namespaces
- CI/CD: GitHub Actions; Docker image pushed to GHCR; deployed on Railway
- Secrets: 1Password Connect or AWS Secrets Manager

## 4. High-Level Architecture

```
┌─────────────────────┐
│  Next.js Chat UI    │  ← user logs in via ChurchSuite SSO
└─────────┬───────────┘
          │ JWT (id token)
┌─────────▼───────────┐
│  FastAPI Gateway    │  ← exchanges code for CS access/refresh
│  • attaches user ⬆  │
│  • enforces RLS     │
└─────────┬───────────┘
          │ Function-calling
┌─────────▼───────────┐
│  GPT-4o (Azure)     │
│  • system prompt    │
│  • tools layer      │
└─────────┬───────────┘
          │ churchsuite.* functions
┌─────────▼───────────┐
│  ChurchSuite API v2 │  ← scoped to caller’s permissions
└─────────────────────┘
```

## 5. Authentication & Authorisation

- Flow: Browser → ChurchSuite SSO (Auth Code) → access_token + refresh_token
- Token propagation: UI stores tokens in http-only cookies; sends opaque session id to API. Gateway looks up tokens & injects user’s Authorization: Bearer header on every ChurchSuite call
- Role / Permission mapping: Rely solely on ChurchSuite modules, tags and site separation. Gateway never broadens scope
- Optional RLS shim: For modules without granular API permissions, gateway post-filters based on user’s available site_ids, ministry_ids, etc
- Write scopes: Disabled in Azure Key Vault until v1 milestone

## 6. Access-Control Enforcement Strategy

1. Preventive: All data calls go through ChurchSuiteClient which requires the caller’s access token
2. Detective: Audit log every request/response ID + truncated payload; store 90 days
3. Tests: Pytest suite includes permission-boundary tests using mocked API responses

## 7. LLM → Tool Schemas

| Tool | Description | Method | ChurchSuite Endpoint |
|------|-------------|--------|---------------------|
| churchsuite.search_people | Fuzzy search of address-book people visible to the caller | GET | /v2/addressbook/people |
| churchsuite.list_groups | List small groups the user can view | GET | /v2/smallgroups/groups |
| churchsuite.list_events | Upcoming events in a given date range | GET | /v2/calendar/events |
| churchsuite.get_my_profile | Caller’s own profile details | GET | /v2/addressbook/me |

Each schema includes user_token in x-headers (hidden from LLM) so the model never sees or stores raw tokens

## 8. Workspace Rules & Guidelines

### 8.1 Project Management
- **Documentation**
  - Use markdown files for project management (README.md, PLANNING.md, TASK.md)
  - Keep documentation up to date with changes
  - Include clear version history and changelogs
  - Maintain proper file structure and naming conventions

- **Code Organization**
  - Keep files under 500 lines. Split into logical modules when needed
  - Follow Python PEP 8 style guidelines
  - Use type hints consistently
  - Maintain clean, modular code structure

### 8.2 Development Practices
- **Code Quality**
  - Write unit tests for all new functionality
  - Implement integration tests for critical paths
  - Follow DRY (Don't Repeat Yourself) principle
  - Use descriptive variable and function names

- **API Development**
  - Document all endpoints with clear examples
  - Implement proper error handling and logging
  - Follow RESTful principles where applicable
  - Use proper HTTP status codes

### 8.3 AI & LLM Usage
- **Conversation Management**
  - Start fresh conversations often to maintain context
  - Keep interactions focused and specific
  - Avoid overloading the model with complex requests
  - Break down large tasks into smaller components

- **Prompt Engineering**
  - Provide clear, specific instructions
  - Include relevant context and examples
  - Use structured data formats when possible
  - Validate AI-generated code before implementation

### 8.4 Security & Compliance
- **Data Handling**
  - Never return fields not explicitly requested
  - Implement proper data masking and sanitization
  - Follow GDPR and privacy guidelines
  - Handle sensitive data with care

- **Access Control**
  - Respect user permissions at all times
  - Implement proper authentication flows
  - Follow ChurchSuite's permission model
  - Log security-relevant events

- **Error Handling**
  - Implement proper retry mechanisms
  - Handle authentication failures gracefully
  - Provide clear error messages to users
  - Log errors with appropriate severity levels

### 8.5 Code Review & Collaboration
- **Review Process**
  - All code changes require review
  - Document review decisions and rationale
  - Maintain consistent coding standards
  - Track and resolve review feedback

- **Collaboration**
  - Use clear commit messages
  - Maintain a clean git history
  - Document architectural decisions
  - Keep team communication open and transparent

## 9. File / Module Guidelines

```
backend/
  main.py              # FastAPI entrypoint (<200 LOC)
  auth.py              # OAuth helpers (token exchange, refresh)
  churchsuite/
    client.py          # API wrapper (<300 LOC)
    schemas.py         # Pydantic models
  llm/
    prompt.py          # System & user prompt builders
    tools.py           # JSONSchema for function-calling
frontend/
  app/                 # Next.js 14
  tests/
    unit/
    integration/
```

- Split FastAPI routers by feature; keep every file < 500 lines

## 10. Testing Strategy

- Unit: pytest for each wrapper & tool (mocks ChurchSuite replies)
- Integration: spin up local wire-mock server with canned ChurchSuite fixtures
- Security regression: test that a user with no "Rotas" module access receives 403

## 11. Security & Compliance

- PII scrubbing in logs except hashed IDs
- GDPR ROPA recorded in /docs/legal/ropa.md
- Data retention: No chat logs older than 30 days unless flagged

## 12. MVP Scope & Milestones

| Milestone | Description | Target |
|-----------|-------------|--------|
| v0-alpha | Read-only Q&A on people, groups, events with live permissions | Jul 2025 |
| v0-beta | RAG cache, per-user namespaces, basic admin dashboard | Aug 2025 |
| v1 | Write endpoints (profile update, event sign-up) gated behind confirmation | Q4 2025 |

## 13. Environment Variables

| Variable | Purpose |
|----------|---------|
| CS_CLIENT_ID | OAuth client id (machine-to-machine) |
| CS_CLIENT_SECRET | OAuth client secret |
| OPENAI_API_KEY | Azure OpenAI key |
| VECTOR_DB_URL | Qdrant connection string |
| JWT_SECRET | Sign UI session tokens |

## 14. Open Questions

1. Does ChurchSuite OAuth return granular scopes (e.g. per-module) or rely on role lookup?
2. Will small-group leaders need elevated write access for attendance notes in v1?
3. Preferred hosting region (EU-West vs UK-South) for data locality?

---

End of PLANNING.md (v0 draft)