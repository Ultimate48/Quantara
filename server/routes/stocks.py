from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import List
from server.schemas import StockOut, FetchRequest
from db.queries import get_all_stocks
from data.fetcher import fetch_and_store

router = APIRouter(prefix="/stocks", tags=["stocks"])

@router.get("/", response_model=List[StockOut])
def list_stocks():
    try:
        stocks = get_all_stocks()
        return [
            StockOut(ticker=s[0], name=s[1], market=s[2], added_at=s[3])
            for s in stocks
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/fetch")
def fetch_stock(req: FetchRequest):
    try:
        fetch_and_store(
            ticker=req.ticker,
            start=req.start,
            end=req.end,
            interval=req.interval or "1d"
        )
        return {"success": True, "message": f"Successfully fetched and stored data for {req.ticker}."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
