from fastapi import APIRouter, Depends
from fastapi.security import HTTPBearer
from typing import Dict, Optional
from fastapi import Query

router = APIRouter()

# Test endpoints
@router.get("/api/test")
async def root():
    return {"message": "Test endpoint"}

@router.get("/api/test-query")
async def test_query(param: str = Query(...)):
    return {"param": param}

@router.post("/api/test-json")
async def test_json(data: Dict[str, Any]):
    return {"data": data}

@router.post("/api/test-form")
async def test_form(field: str = Form(...)):
    return {"field": field}

@router.get("/api/protected", dependencies=[Depends(HTTPBearer())])
async def protected():
    return {"message": "Protected endpoint"}
