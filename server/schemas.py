from pydantic import BaseModel, Field
from typing import Optional, List, Any, Dict
from datetime import datetime, date

class StockOut(BaseModel):
    ticker: str
    name: Optional[str] = None
    market: Optional[str] = None
    added_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class FetchRequest(BaseModel):
    ticker: str
    start: Optional[str] = None
    end: Optional[str] = None
    interval: Optional[str] = "1d"

class StrategyCreate(BaseModel):
    name: str = Field(..., max_length=50)
    description: Optional[str] = None
    columns: List[Dict[str, str]]
    signal_rule: str

class StrategyUpdate(BaseModel):
    description: Optional[str] = None
    columns: Optional[List[Dict[str, str]]] = None
    signal_rule: Optional[str] = None

class StrategyOut(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    columns: List[Dict[str, str]]
    signal_rule: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class BacktestRequest(BaseModel):
    strategy: str
    ticker: str
    start: Optional[str] = None
    end: Optional[str] = None
    capital: Optional[float] = 100000.0
    cooldown: Optional[int] = 0
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    mode: Optional[str] = "long"
    confirm_buy: Optional[int] = 1
    confirm_sell: Optional[int] = 1
    position_size: Optional[str] = "all"
    transaction_cost: Optional[float] = 0.0
    slippage: Optional[float] = 0.0

class BacktestSummary(BaseModel):
    id: int
    execute_on: str
    strategy_id: int
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    initial_capital: float
    total_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    total_trades: int
    run_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class BacktestDetail(BacktestSummary):
    trade_log: List[Dict[str, Any]]
    equity_curve: List[Dict[str, Any]]
    benchmark_curve: Optional[List[Dict[str, Any]]] = None
