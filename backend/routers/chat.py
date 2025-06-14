from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import JSONResponse
from backend.config import settings
from backend.llm.tools import get_llm_tools
from typing import Optional, Dict, Any
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/test/rate-limit")
async def test_rate_limit(request: Request):
    """Test endpoint for rate limiting"""
    return JSONResponse({"status": "ok"})

@router.post("/chat")
async def chat_endpoint(request: Request):
    """Handle chat messages using OpenAI API"""
    try:
        chat_request = await request.json()
        tools = get_llm_tools()
        
        # Process chat request
        response = await process_chat_request(chat_request, tools)
        
        return JSONResponse(response)
    except Exception as e:
        logger.error(f"Chat endpoint error: {str(e)}", exc_info=True)
        return JSONResponse(
            {"error": f"Error processing request: {str(e)}"},
            status_code=500
        )
