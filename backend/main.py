from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from typing import Optional
import uvicorn
from pydantic import BaseModel
from churchsuite.client import ChurchSuiteClient
from llm.tools import get_llm_tools
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

app = FastAPI(title="ChurchSuite Chatbot API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Update with your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# OAuth2 setup
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Dependency for getting ChurchSuite client
def get_churchsuite_client():
    client = ChurchSuiteClient(
        client_id=os.getenv("CS_CLIENT_ID"),
        client_secret=os.getenv("CS_CLIENT_SECRET"),
        base_url="https://api.churchsuite.co.uk/v2"
    )
    return client

# Models
class ChatRequest(BaseModel):
    message: str
    user_token: str

class ChatResponse(BaseModel):
    response: str

@app.post("/chat")
async def chat_endpoint(request: ChatRequest, 
                       churchsuite_client: ChurchSuiteClient = Depends(get_churchsuite_client)):
    try:
        # Get tools for the LLM
        tools = get_llm_tools(churchsuite_client, request.user_token)
        
        # TODO: Implement chat logic with LLM
        return ChatResponse(
            response="This is a placeholder response. Chat functionality will be implemented."
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
