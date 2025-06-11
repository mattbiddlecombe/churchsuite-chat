from typing import Dict, Any, Callable, List
from backend.churchsuite.client import ChurchSuiteClient

def get_llm_tools(client: ChurchSuiteClient, user_token: str) -> List[Dict[str, Any]]:
    """Get the list of LLM tools with their function signatures"""
    return [
        {
            "name": "search_people",
            "description": "Search for people in the address book",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search term for finding people"
                    },
                    "user_token": {
                        "type": "string",
                        "description": "User authentication token"
                    }
                },
                "required": ["query", "user_token"]
            },
            "function": lambda params: client.search_people(params["query"], user_token)
        },
        {
            "name": "list_groups",
            "description": "List small groups visible to the user",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_token": {
                        "type": "string",
                        "description": "User authentication token"
                    }
                },
                "required": ["user_token"]
            },
            "function": lambda params: client.list_groups(user_token)
        },
        {
            "name": "list_events",
            "description": "List events within a date range",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {
                        "type": "string",
                        "description": "Start date for event search (YYYY-MM-DD)"
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date for event search (YYYY-MM-DD)"
                    },
                    "user_token": {
                        "type": "string",
                        "description": "User authentication token"
                    }
                },
                "required": ["start_date", "end_date", "user_token"]
            },
            "function": lambda params: client.list_events(
                params["start_date"],
                params["end_date"],
                user_token
            )
        },
        {
            "name": "get_my_profile",
            "description": "Get the current user's profile details",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_token": {
                        "type": "string",
                        "description": "User authentication token"
                    }
                },
                "required": ["user_token"]
            },
            "function": lambda params: client.get_my_profile(user_token)
        }
    ]
