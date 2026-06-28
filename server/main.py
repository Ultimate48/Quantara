from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional

from server.routes import stocks, strategies, backtest
from server.schemas import FetchRequest

app = FastAPI(title="Quantara API", description="API for Quantara Algorithmic Trading Research Platform")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(stocks.router, prefix="/api")
app.include_router(strategies.router, prefix="/api")
app.include_router(backtest.router, prefix="/api")

@app.post("/api/fetch")
def api_fetch(req: FetchRequest):
    return stocks.fetch_stock(req)

@app.get("/api/backtests")
def api_backtests(ticker: Optional[str] = None, strategy_id: Optional[int] = None):
    return backtest.list_backtest_runs(ticker, strategy_id)

@app.get("/api/indicators")
def api_indicators():
    from strategies.indicators import list_indicators
    return list_indicators()

@app.get("/")
def read_root():
    return {
        "status": "online",
        "message": "Welcome to the Quantara API. Use /docs for API documentation."
    }
