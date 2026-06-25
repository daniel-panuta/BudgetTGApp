from fastapi import APIRouter, HTTPException, Query

from ...services.transactions_service import get_transactions_page

router = APIRouter()


@router.get("")
def list_transactions(limit: int = Query(20, ge=1, le=100)):
    try:
        return get_transactions_page(limit=limit)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc