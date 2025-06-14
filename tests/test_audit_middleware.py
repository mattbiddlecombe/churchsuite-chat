import pytest
from fastapi import FastAPI, Request, Response
from fastapi.testclient import TestClient
from backend.security.audit_middleware import audit_middleware
from backend.config.logging import AuditFormatter, get_audit_logger
import logging
import json
from datetime import datetime

@pytest.fixture
def test_client_with_handler():
    """Create a test client with audit middleware and capture logs"""
    app = FastAPI()
    
    # Set up audit logger first
    audit_logger = get_audit_logger()
    audit_logger.setLevel(logging.INFO)
    
    # Use a custom handler that captures logs
    class JSONLogCapture(logging.Handler):
        def __init__(self):
            super().__init__()
            self.logs = []
            self.formatter = AuditFormatter()

        def emit(self, record):
            # Get extra fields directly from record
            extra = getattr(record, "extra", {})
            
            # Format the record using our formatter
            log_entry = self.formatter.format(record)
            
            # Parse the JSON string back into a dictionary
            log_dict = json.loads(log_entry)
            
            # Add all extra fields to ensure they're present
            for key, value in extra.items():
                if key not in log_dict:
                    log_dict[key] = value
            
            # Add message from record if not present
            if "message" not in log_dict:
                log_dict["message"] = record.getMessage()
            
            self.logs.append(log_dict)

    handler = JSONLogCapture()
    audit_logger.addHandler(handler)
    
    # Add test routes
    async def test_endpoint(request):
        return Response(content="Test response", status_code=200)
    app.add_route("/test", test_endpoint, methods=["GET"])
    
    async def error_endpoint(request):
        raise ValueError("Test error")
    app.add_route("/error", error_endpoint, methods=["GET"])
    
    # Add middleware after routes are added
    app.middleware("http")(audit_middleware)
    
    yield TestClient(app), handler
    
    # Cleanup
    audit_logger.removeHandler(handler)

@pytest.fixture
def test_handler(test_client_with_handler):
    return test_client_with_handler[1]

@pytest.fixture
def test_client(test_client_with_handler):
    return test_client_with_handler[0]

def test_audit_middleware_request_logging(test_client_with_handler):
    """Test that audit middleware logs request details"""
    test_client, handler = test_client_with_handler
    
    # Make request
    response = test_client.get("/test")
    
    # Check response
    assert response.status_code == 200
    
    # Get JSON logs from handler
    log_records = handler.logs
    assert len(log_records) == 2  # Request and response logs
    
    # Print logs for debugging
    print("\nLogs:", log_records)
    
    request_log = log_records[0]
    assert request_log["event_type"] == "request"
    assert request_log["method"] == "GET"
    assert request_log["path"] == "/test"
    assert request_log["client"] != "-"
    assert "request_id" in request_log
    assert "headers" in request_log
    assert "user_id" in request_log

def test_audit_middleware_error_logging(test_client_with_handler):
    assert "request_id" in response_log
    assert "timestamp" in response_log
    
def test_audit_middleware_error_logging(test_client, test_handler):
    """Test that audit middleware logs error details"""
    # Make request
    with pytest.raises(ValueError):
        test_client.get("/error")
    
    # Get JSON logs from handler
    log_records = test_handler.logs
    assert len(log_records) == 2  # Request and error logs
    
    # Print logs for debugging
    print("\nLogs:", log_records)
    
    error_log = log_records[-1]  # Get the last error log
    assert error_log["event_type"] == "error"
    assert error_log["error_type"] == "ValueError"
    assert error_log["error_message"] == "Test error"
    assert "request_id" in error_log
    assert "timestamp" in error_log
    assert "method" in error_log
    assert "path" in error_log
    assert "timestamp" in error_log
