import os
from dotenv import load_dotenv
import openai

# Load environment variables from .env file
load_dotenv()

# Set OpenAI API key and configuration
openai.api_key = os.getenv("OPENAI_API_KEY")
openai.api_base = "https://api.openai.com/v1"

from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.routing import Route
import uvicorn
from typing import Dict, Any
from backend.churchsuite.client import ChurchSuiteClient
from backend.llm.tools import get_llm_tools
import json
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def chat_endpoint(request):
    try:
        # Get the request body
        body = await request.json()
        logger.debug(f"Received request body: {body}")
        
        # Prepare messages for OpenAI
        messages = [
            {
                "role": "system",
                "content": "You are a helpful church assistant. Use the provided tools to help users with church-related queries."
            },
            {
                "role": "user",
                "content": body["message"]
            }
        ]
        logger.debug(f"Sending messages to OpenAI: {messages}")
        
        # Call OpenAI API
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages
        )
        logger.debug(f"OpenAI response: {response}")
        
        # Get the response
        message = response["choices"][0]["message"]
        logger.debug(f"Message from OpenAI: {message}")
        
        return JSONResponse({
            "response": message["content"]
        })
        
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}", exc_info=True)
        return JSONResponse(
            {"error": str(e)},
            status_code=500
        )

routes = [
    Route('/chat', chat_endpoint, methods=['POST'])
]

middleware = [
    Middleware(CORSMiddleware, 
        allow_origins=["http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    ),
]

app = Starlette(routes=routes, middleware=middleware)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
