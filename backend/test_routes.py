from fastapi import APIRouter, Depends
from fastapi.security import HTTPBearer
from typing import Dict

router = APIRouter()

# Test endpoints
@router.get("/api/test")
async def root():
    return {"message": "Test endpoint"}

@router.get("/api/protected", dependencies=[Depends(HTTPBearer())])
async def protected():
    return {"message": "Protected endpoint"}
