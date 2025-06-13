from typing import Dict, Any
from starlette.requests import Request
from starlette.datastructures import Headers

class MockRequest(Request):
    """Mock Request class for testing middleware"""
    
    def __init__(self, url: str, method: str = 'GET', headers: Dict[str, str] = None, json: Any = None):
        """Initialize mock request"""
        super().__init__(
            scope={
                'type': 'http',
                'method': method,
                'path': url,
                'headers': Headers(headers or {}).raw,
                'query_string': b'',
                'scheme': 'https',
                'server': ('localhost', 8000),
                'client': ('127.0.0.1', 12345),
            },
            receive=None,
            send=None,
        )
        self._json = json

    async def json(self) -> Any:
        """Return mock JSON data"""
        return self._json
