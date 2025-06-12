import os
from typing import Dict, Any, List
import openai
from pydantic import BaseModel
from fastapi import HTTPException
from datetime import datetime

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatResponse(BaseModel):
    response: str
    functions_used: List[Dict[str, Any]] = []

class OpenAIChat:
    def __init__(self, api_key: str):
        self.api_key = api_key
        openai.api_key = api_key
        self.system_prompt = """
        You are a helpful church assistant. You can help answer questions about church events, groups, and people.
        Always use the provided functions to get accurate information from the church database.
        Never make assumptions about what values to plug into functions. Always ask for clarification if you're unsure.
        """

    async def chat(self, message: str, tools: List[Dict[str, Any]]) -> ChatResponse:
        try:
            # Prepare the messages for the chat
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": message}
            ]

            # Get the function signatures for the tools
            functions = [{"name": tool["name"], "description": tool["description"], "parameters": tool["parameters"]} for tool in tools]

            # Call the OpenAI API
            response = await openai.ChatCompletion.acreate(
                model="gpt-3.5-turbo",
                messages=messages,
                functions=functions,
                function_call="auto"
            )

            # Process the response
            functions_used = []
            function_calls = []
            
            # Extract function calls if any
            if response.choices[0].message.function_call:
                function_calls.append(response.choices[0].message.function_call)

            # If there are function calls, we need to execute them and get results
            if function_calls:
                # TODO: Implement function execution and response handling
                # For now, just return the function calls
                functions_used = function_calls

            # Get the AI response
            ai_response = response.choices[0].message.content

            return ChatResponse(response=ai_response, functions_used=functions_used)

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error processing chat: {str(e)}"
            )
