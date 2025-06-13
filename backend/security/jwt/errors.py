from typing import Optional, Any, Dict
from jose import JWTError, ExpiredSignatureError
from pydantic import BaseModel


class JWTValidationError(BaseModel):
    """Model for JWT validation error responses."""
    error: str
    detail: str
    code: int = 401


class JWTErrorDetails(Exception):
    """Custom exception for JWT-related errors with structured error details."""
    
    def __init__(self, error: str, detail: str, code: int = 401):
        """
        Initialize the JWT error with structured details.
        
        Args:
            error (str): The error type (e.g., "Authentication required")
            detail (str): Detailed error message
            code (int): HTTP status code (default: 401)
        """
        self.error = error
        self.detail = detail
        self.code = code
        super().__init__(f"{error}: {detail}")


def format_jwt_error(error: JWTError, detail: str) -> JWTValidationError:
    """
    Format a JWT error into a structured error response.
    
    Args:
        error (JWTError): The JWT error instance
        detail (str): Additional error details
        
    Returns:
        JWTValidationError: Structured error response
    """
    return JWTValidationError(
        error=str(error.__class__.__name__),
        detail=detail
    )


def raise_jwt_error(error: JWTError, detail: str) -> None:
    """
    Raise a structured JWT error exception.
    
    Args:
        error (JWTError): The JWT error instance
        detail (str): Additional error details
        
    Raises:
        JWTErrorDetails: Structured JWT error exception
    """
    raise JWTErrorDetails(
        error=str(error.__class__.__name__),
        detail=detail,
        code=401 if isinstance(error, JWTError) else 500
    )
