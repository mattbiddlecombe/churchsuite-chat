from typing import Callable, Awaitable, Any, Dict, Optional
from starlette.requests import Request
from starlette.datastructures import Headers

class MockRequest:
    def __init__(self, headers: dict = None, method: str = 'GET', url_path: str = '/', body: dict = None, query_params: dict = None, state: dict = None, scope: dict = None):
        # Convert headers to bytes
        self.headers = Headers({
            k: v 
            for k, v in (headers or {}).items()
        })
        # Convert headers to bytes format for ASGI
        self._asgi_headers = [
            (k.encode('latin-1'), v.encode('latin-1'))
            for k, v in self.headers.items()
        ]
        self.method = method
        self.url = type("URL", (), {"path": url_path})
        self.body_data = body
        self._query_params = query_params or {}
        self.state = state or {}
        self.scope = scope or {}
        self._receive = None
        self._send = None
        self.response = None
        self.body = None
        
        # For auth endpoints, ensure state is empty
        if url_path in ['/auth/start', '/auth/callback', '/auth/refresh']:
            self.state = {}

    async def receive(self):
        return {'type': 'http.request'}

    async def send(self, message):
        pass

    def __call__(self, receive, send):
        self._receive = receive
        self._send = send
        return self
        
    @property
    def query_params(self):
        return self._query_params

    @query_params.setter
    def query_params(self, value):
        self._query_params = value

    async def json(self):
        return self.body_data

    async def form(self):
        return self.body_data

    def __getitem__(self, key):
        return self.state[key]

    def get(self, key, default=None):
        return self.state.get(key, default)

    def __getattr__(self, name):
        if name == 'state':
            return self.state
        if name == 'scope':
            return self.scope
        if name == 'session':
            return {}  # Return empty dict instead of raising error
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")

    def __setattr__(self, name, value):
        if name == 'state':
            self.__dict__['state'] = value
        elif name == 'scope':
            self.__dict__['scope'] = value
        else:
            self.__dict__[name] = value

    def __contains__(self, key):
        return key in self.state

    def __iter__(self):
        return iter(self.state)

    def __len__(self):
        return len(self.state)
