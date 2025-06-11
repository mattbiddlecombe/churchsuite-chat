# ChurchSuite Chatbot

A secure AI chat assistant that integrates with ChurchSuite to provide read-only access to church data while respecting user permissions.

## Features

- Secure authentication using ChurchSuite OAuth2
- Read-only access to ChurchSuite data
- AI-powered chat interface using OpenAI's GPT-4
- Respect for user permissions and data access restrictions
- Optional vector store caching for improved performance

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
│   ├── auth.py       # Authentication
│   └── main.py       # FastAPI app
├── frontend/         # Next.js application
│   └── app/          # React components
├── tests/           # Test suite
│   ├── unit/        # Unit tests
│   └── integration/ # Integration tests
└── docs/            # Documentation
```

## Security

- All data access is scoped to the user's ChurchSuite permissions
- Token management follows security best practices
- Sensitive data is properly masked and sanitized
- Comprehensive audit logging is implemented

## Contributing

Please read the [CONTRIBUTING.md](CONTRIBUTING.md) file for guidelines on contributing to this project.
