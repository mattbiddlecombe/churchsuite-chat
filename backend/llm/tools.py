from typing import Dict, Any, Callable, List
from pydantic import BaseModel
from churchsuite.client import ChurchSuiteClient

# Define the function signatures for LLM tools
class ChurchSuiteSearchPeopleParams(BaseModel):
    query: str
    user_token: str

class ChurchSuiteListGroupsParams(BaseModel):
    user_token: str

class ChurchSuiteListEventsParams(BaseModel):
    start_date: str
    end_date: str
    user_token: str

class ChurchSuiteGetProfileParams(BaseModel):
    user_token: str

def get_llm_tools(client: ChurchSuiteClient, user_token: str) -> List[Dict[str, Any]]:
    """Get the list of LLM tools with their function signatures"""
    return [
        {
            "name": "churchsuite.search_people",
            "description": "Search for people in the address book",
            "parameters": ChurchSuiteSearchPeopleParams.schema(),
            "function": lambda params: client.search_people(params["query"], user_token)
        },
        {
            "name": "churchsuite.list_groups",
            "description": "List small groups visible to the user",
            "parameters": ChurchSuiteListGroupsParams.schema(),
            "function": lambda params: client.list_groups(user_token)
        },
        {
            "name": "churchsuite.list_events",
            "description": "List events within a date range",
            "parameters": ChurchSuiteListEventsParams.schema(),
            "function": lambda params: client.list_events(
                params["start_date"],
                params["end_date"],
                user_token
            )
        },
        {
            "name": "churchsuite.get_my_profile",
            "description": "Get the current user's profile details",
            "parameters": ChurchSuiteGetProfileParams.schema(),
            "function": lambda params: client.get_my_profile(user_token)
        }
    ]
