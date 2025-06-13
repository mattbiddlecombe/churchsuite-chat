from starlette.requests import Request
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import List, Optional
from backend.schemas.requests.giving import GivingAccountFilter, GivingTransactionFilter, GivingSummaryFilter

from backend.churchsuite.client import ChurchSuiteClient
from backend.churchsuite.models import GivingAccount, GivingTransaction, GivingSummary

router = APIRouter()

async def get_churchsuite_client(request: Request) -> ChurchSuiteClient:
    return request.app.get_churchsuite_client(request)

@router.get("/accounts", response_model=List[GivingAccount])
async def list_giving_accounts(
    request: Request,
    churchsuite_client: ChurchSuiteClient = Depends(get_churchsuite_client),
    filter: GivingAccountFilter = Depends()
) -> List[GivingAccount]:
    """List all giving accounts."""
    try:
        accounts = await churchsuite_client.get_giving_accounts()
        return accounts
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/accounts", response_model=dict)
async def initialize_session(
    request: Request,
    data: dict,
    churchsuite_client: ChurchSuiteClient = Depends(get_churchsuite_client)
) -> dict:
    """Initialize session with user data."""
    request.session.update(data)
    return {"message": "Session initialized successfully"}

@router.get("/account/{account_id}", response_model=GivingAccount)
async def get_giving_account(
    account_id: str,
    request: Request,
    churchsuite_client: ChurchSuiteClient = Depends(get_churchsuite_client)
) -> GivingAccount:
    """Get details for a specific giving account."""
    try:
        account = await churchsuite_client.get_giving_account(account_id)
        return account
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/transactions", response_model=List[GivingTransaction])
async def list_giving_transactions(
    request: Request,
    churchsuite_client: ChurchSuiteClient = Depends(get_churchsuite_client),
    filter: GivingTransactionFilter = Depends()
) -> List[GivingTransaction]:
    """List all giving transactions."""
    try:
        transactions = await churchsuite_client.get_giving_transactions()
        return transactions
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/summary", response_model=GivingSummary)
async def get_giving_summary(
    request: Request,
    churchsuite_client: ChurchSuiteClient = Depends(get_churchsuite_client),
    filter: GivingSummaryFilter = Depends()
) -> GivingSummary:
    """Get giving summary statistics."""
    try:
        summary = await churchsuite_client.get_giving_summary()
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history/{person_id}", response_model=List[GivingTransaction])
async def get_person_giving_history(
    person_id: str,
    request: Request,
    churchsuite_client: ChurchSuiteClient = Depends(get_churchsuite_client)
) -> List[GivingTransaction]:
    """Get giving history for a person."""
    try:
        history = await churchsuite_client.get_person_giving_history(person_id)
        return history
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


        data = await request.json()
        transaction = await client.update_giving_transaction(transaction_id, **data)
        return JSONResponse({"transaction": transaction})
    except Exception as e:
        logger.error(f"Error updating giving transaction: {str(e)}")
        return JSONResponse({"error": str(e)}, status_code=500)

async def delete_giving_transaction(request: Request):
    """Delete a giving transaction."""
    try:
        transaction_id = request.path_params['transaction_id']
        client = request.app.get_churchsuite_client(request)
        await client.delete_giving_transaction(transaction_id)
        return JSONResponse({"message": "Transaction deleted successfully"})
    except Exception as e:
        logger.error(f"Error deleting giving transaction: {str(e)}")
        return JSONResponse({"error": str(e)}, status_code=500)

async def get_giving_report(request: Request):
    """Generate a giving report."""
    try:
        client = request.app.get_churchsuite_client(request)
        # Parse query parameters
        params = {
            'start_date': request.query_params.get('start_date'),
            'end_date': request.query_params.get('end_date'),
            'account_id': request.query_params.get('account_id'),
            'person_id': request.query_params.get('person_id')
        }
        report = await client.get_giving_report(**params)
        return JSONResponse({"report": report})
    except Exception as e:
        logger.error(f"Error generating giving report: {str(e)}")
        return JSONResponse({"error": str(e)}, status_code=500)

async def get_giving_export(request: Request):
    """Export giving data."""
    try:
        client = request.app.get_churchsuite_client(request)
        # Parse query parameters
        params = {
            'start_date': request.query_params.get('start_date'),
            'end_date': request.query_params.get('end_date'),
            'account_id': request.query_params.get('account_id'),
            'format': request.query_params.get('format', 'csv')
        }
        export = await client.get_giving_export(**params)
        return JSONResponse({"export": export})
    except Exception as e:
        logger.error(f"Error exporting giving data: {str(e)}")
        return JSONResponse({"error": str(e)}, status_code=500)
