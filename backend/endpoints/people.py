from fastapi import APIRouter, Depends, HTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse
from backend.churchsuite.client import ChurchSuiteClient
from backend.schemas.requests.people import PersonSearchFilter, PersonUpdate
import logging

router = APIRouter()

async def get_churchsuite_client(request: Request) -> ChurchSuiteClient:
    return request.app.get_churchsuite_client(request)

logger = logging.getLogger(__name__)

@router.get("/search", response_model=dict)
async def search_people(
    request: Request,
    churchsuite_client: ChurchSuiteClient = Depends(get_churchsuite_client),
    filter: PersonSearchFilter = Depends()
):
    """Search for people."""
    try:
        people = await churchsuite_client.search_people(filter.query)
        return {"people": people}
    except Exception as e:
        logger.error(f"Error searching people: {str(e)}")
        return JSONResponse({"error": str(e)}, status_code=500)

async def get_person(request: Request):
    """Get person details."""
    try:
        person_id = request.path_params['person_id']
        client = request.app.get_churchsuite_client(request)
        person = await client.get_person(person_id)
        return JSONResponse({"person": person})
    except Exception as e:
        logger.error(f"Error getting person: {str(e)}")
        return JSONResponse({"error": str(e)}, status_code=500)

@router.put("/{person_id}", response_model=dict)
async def update_person(
    person_id: str,
    request: Request,
    churchsuite_client: ChurchSuiteClient = Depends(get_churchsuite_client),
    update_data: PersonUpdate = Depends()
):
    """Update person details."""
    try:
        person = await churchsuite_client.update_person(
            person_id,
            first_name=update_data.first_name,
            last_name=update_data.last_name,
            email=update_data.email,
            phone=update_data.phone
        )
        return {"person": person}
    except Exception as e:
        logger.error(f"Error updating person: {str(e)}")
        return JSONResponse({"error": str(e)}, status_code=500)

async def get_family(request: Request):
    """Get person's family."""
    try:
        person_id = request.path_params['person_id']
        client = request.app.get_churchsuite_client(request)
        family = await client.get_family(person_id)
        return JSONResponse({"family": family})
    except Exception as e:
        logger.error(f"Error getting family: {str(e)}")
        return JSONResponse({"error": str(e)}, status_code=500)
