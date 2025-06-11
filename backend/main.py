from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any
import uvicorn
from churchsuite.client import ChurchSuiteClient
from llm.tools import get_llm_tools

app = FastAPI(title="ChurchSuite Chatbot API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Update with your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/chat")
async def chat_endpoint(request: Dict[str, Any]) -> Dict[str, Any]:
    try:
        # Create a mock client for now
        churchsuite_client = ChurchSuiteClient(
            client_id="mock_client_id",
            client_secret="mock_client_secret",
            base_url="https://api.churchsuite.co.uk/v2"
        )
        
        # Get tools for the LLM
        tools = get_llm_tools(churchsuite_client, request["user_token"])
        
        # TODO: Implement chat logic with LLM
        return {"response": "This is a placeholder response. Chat functionality will be implemented."}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
