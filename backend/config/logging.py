import logging
import json
from datetime import datetime
from typing import Any, Dict

class AuditFormatter(logging.Formatter):
    """Formatter for audit logs"""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        # Get all record attributes
        record_attrs = vars(record)
        
        # Create base log entry
        log_entry = {
            "level": record.levelname,
            "event": "audit",
            "message": record.getMessage(),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Add all record attributes that aren't standard logging attributes
        standard_attrs = ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 'filename', 
                         'module', 'exc_info', 'exc_text', 'stack_info', 'lineno', 'funcName',
                         'created', 'msecs', 'relativeCreated', 'thread', 'threadName',
                         'processName', 'process', 'taskName']
        
        for key, value in record_attrs.items():
            if key not in standard_attrs:
                log_entry[key] = value
        
        # If event_type is not explicitly set in extra, try to infer it from the message
        if "event_type" not in log_entry:
            if record.getMessage().startswith("Request received"):
                log_entry["event_type"] = "request"
            elif record.getMessage().startswith("Response sent"):
                log_entry["event_type"] = "response"
            elif record.getMessage().startswith("Request processing error"):
                log_entry["event_type"] = "error"
        
        return json.dumps(log_entry)
        return json.dumps(log_entry)

def setup_logging() -> None:
    """Configure logging for the application"""
    # Create audit logger
    audit_logger = logging.getLogger("audit")
    audit_logger.setLevel(logging.INFO)
    
    # Create handler and formatter
    handler = logging.FileHandler("audit.log")
    handler.setLevel(logging.INFO)
    handler.setFormatter(AuditFormatter())
    
    # Add handler to logger
    audit_logger.addHandler(handler)
    
    return audit_logger

def get_audit_logger() -> logging.Logger:
    """Get the audit logger instance"""
    return logging.getLogger("audit")
