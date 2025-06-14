from fastapi import FastAPI, Request, Response, HTTPException, status
from typing import Dict, Any
import logging
from datetime import datetime, timedelta
import json
from fastapi.responses import JSONResponse
from backend.security.dependencies import ENDPOINT_SCHEMAS

logger = logging.getLogger(__name__)

requests: Dict[str, Dict[str, Any]] = {}

def rate_limit_middleware(app: FastAPI, rate_limit: int = 100, window: int = 60):
    """Rate limit middleware factory.
    
    Args:
        app: FastAPI application
        rate_limit: Maximum number of requests per window
        window: Time window in seconds
    """
    global rate_limit_global, window_global
    rate_limit_global = rate_limit
    window_global = window
    
    @app.middleware("http")
    async def dispatch(request: Request, call_next):
        """Middleware dispatch method."""
        try:
            # Check if this is an auth endpoint
            if request.url.path in ['/auth/start', '/auth/callback', '/auth/refresh']:
                response = await call_next(request)
                return response
            
            # Get client IP
            client_ip = request.client.host
            
            # Get or initialize rate limit data
            rate_limit_data = requests.get(client_ip, None)
            
            logger.debug(f"Rate limit check for IP: {client_ip}")
            logger.debug(f"Current count: {rate_limit_data['count'] if rate_limit_data else 0}")
            logger.debug(f"Rate limit: {rate_limit_global}")
            logger.debug(f"Window: {window_global}")
            
            # If no data or window expired
            if not rate_limit_data:
                logger.debug(f"Initializing rate limit for IP: {client_ip}")
                # Initialize
                requests[client_ip] = {
                    'count': 0,  # Start with 0 requests
                    'start_time': datetime.now()
                }
                rate_limit_data = requests[client_ip]
                
                # Process request first (this is the first request)
                response = await call_next(request)
                
                # Update count
                rate_limit_data['count'] += 1
                
                # Set headers
                response.headers["X-RateLimit-Limit"] = str(rate_limit_global)
                response.headers["X-RateLimit-Remaining"] = str(rate_limit_global - 1)
                response.headers["X-RateLimit-Reset"] = str(window_global)
                
                logger.debug(f"First request for IP: {client_ip} - count: {rate_limit_data['count']}")
                return response
            
            # Calculate time remaining in window
            now = datetime.now()
            window_start_time = rate_limit_data['start_time'].timestamp()
            time_remaining = window_global - (now.timestamp() - window_start_time)
            
            logger.debug(f"Time remaining: {time_remaining:.1f} seconds")
            
            # Check if window has expired
            if time_remaining <= 0:
                logger.debug(f"Window expired for IP: {client_ip}, resetting")
                # Reset count and start time
                rate_limit_data['count'] = 0
                rate_limit_data['start_time'] = now
                time_remaining = window_global
                
                # Process request after reset
                response = await call_next(request)
                
                # Update count
                rate_limit_data['count'] += 1
                
                # Set headers
                response.headers["X-RateLimit-Limit"] = str(rate_limit_global)
                response.headers["X-RateLimit-Remaining"] = str(rate_limit_global - 1)
                response.headers["X-RateLimit-Reset"] = str(window_global)
                
                logger.debug(f"Request after reset for IP: {client_ip} - count: {rate_limit_data['count']}")
                return response
            
            # Check if request limit has been exceeded (before processing request)
            if rate_limit_data['count'] + 1 > rate_limit_global:
                logger.warning(f"Rate limit exceeded for IP: {client_ip}")
                logger.debug(f"Rate limit exceeded - count: {rate_limit_data['count']}")
                # Create a new response with 429 status
                error_response = JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "detail": f"Rate limit exceeded. Please wait {time_remaining:.1f} seconds before making more requests."
                    }
                )
                error_response.headers["X-RateLimit-Limit"] = str(rate_limit_global)
                error_response.headers["X-RateLimit-Remaining"] = "0"
                error_response.headers["X-RateLimit-Reset"] = str(int(time_remaining))
                return error_response
            
            # Process request
            response = await call_next(request)
            
            # Update count
            rate_limit_data['count'] += 1
            
            # Set headers
            response.headers["X-RateLimit-Limit"] = str(rate_limit_global)
            response.headers["X-RateLimit-Remaining"] = str(rate_limit_global - rate_limit_data['count'])
            response.headers["X-RateLimit-Reset"] = str(int(time_remaining))
            
            logger.debug(f"Request processed for IP: {client_ip} - count: {rate_limit_data['count']}")
            return response
            
        except Exception as e:
            logger.error(f"Rate limit error: {str(e)}", exc_info=True)
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "detail": "Internal server error",
                    "error": str(e)
                }
            )
