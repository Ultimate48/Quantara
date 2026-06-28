from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
import json
from server.schemas import BacktestRequest, BacktestDetail, BacktestSummary
from db.queries import (
    ticker_exists, fetch_strategy_by_name, save_backtest_run,
    get_backtest_runs, fetch_backtest_run, get_price_data
)
from backtest.engine import run_backtest, compute_benchmark

router = APIRouter(prefix="/backtest", tags=["backtest"])

def parse_json_field(field):
    if field is None:
        return []
    if isinstance(field, str):
        try:
            return json.loads(field)
        except Exception:
            return []
    if isinstance(field, (list, dict)):
        return field
    return []

@router.post("/", response_model=BacktestDetail)
def execute_backtest(req: BacktestRequest):
    if not ticker_exists(req.ticker):
        raise HTTPException(
            status_code=400,
            detail=f"Ticker '{req.ticker}' not found in database. Please fetch data for this stock first."
        )
    
    strategy = fetch_strategy_by_name(req.strategy)
    if strategy is None:
        raise HTTPException(
            status_code=404,
            detail=f"Strategy '{req.strategy}' not found."
        )
    
    strategy_id = strategy[0]
    
    try:
        result = run_backtest(
            name=req.strategy,
            ticker=req.ticker,
            start=req.start,
            end=req.end,
            initial_capital=req.capital or 100000.0,
            show_plot=False,
            cooldown=req.cooldown or 0,
            stop_loss=req.stop_loss,
            take_profit=req.take_profit,
            mode=req.mode or "long",
            confirm_buy=req.confirm_buy or 1,
            confirm_sell=req.confirm_sell or 1,
            position_size=req.position_size or "all",
            transaction_cost=req.transaction_cost or 0.0,
            slippage=req.slippage or 0.0
        )
        
        equity_curve = result["equity_curve"]
        trade_log = result["trade_log"]
        
        equity_curve_records = [
            {"date": str(idx)[:10] if hasattr(idx, "strftime") else str(idx), "value": float(val)}
            for idx, val in equity_curve["value"].items()
        ]

        benchmark_df = compute_benchmark(result["df"], float(req.capital or 100000.0))
        benchmark_records = [
            {"date": str(idx)[:10] if hasattr(idx, "strftime") else str(idx), "value": float(val)}
            for idx, val in benchmark_df["value"].items()
        ]
        
        trade_log_records = []
        if not trade_log.empty:
            for _, row in trade_log.iterrows():
                trade_log_records.append({
                    "date": str(row["date"])[:10] if hasattr(row["date"], "strftime") else str(row["date"]),
                    "type": row["type"],
                    "price": float(row["price"]),
                    "shares": float(row["shares"]),
                    "cash_after": float(row["cash_after"]),
                    "reason": row.get("reason", "signal"),
                    "cost": float(row.get("cost", 0.0))
                })
        
        run_data = {
            "strategy_id": strategy_id,
            "data_tickers": json.dumps([req.ticker]),
            "execute_on": req.ticker,
            "start_date": equity_curve.index[0],
            "end_date": equity_curve.index[-1],
            "initial_capital": float(req.capital or 100000.0),
            "final_value": float(result["final_value"]),
            "total_return": float(result["metrics"]["total_return"]),
            "sharpe_ratio": float(result["metrics"]["sharpe_ratio"]),
            "max_drawdown": float(result["metrics"]["max_drawdown"]),
            "win_rate": float(result["metrics"]["win_rate"]),
            "total_trades": int(result["metrics"]["total_trades"]),
            "trade_log": json.dumps(trade_log_records),
            "equity_curve": json.dumps(equity_curve_records),
        }
        
        run_id = save_backtest_run(run_data)
        
        saved_row = fetch_backtest_run(run_id)
        if saved_row is None:
            raise HTTPException(status_code=500, detail="Failed to retrieve saved backtest run.")
            
        return BacktestDetail(
            id=saved_row[0],
            strategy_id=saved_row[1],
            execute_on=saved_row[3],
            start_date=saved_row[4],
            end_date=saved_row[5],
            initial_capital=float(saved_row[6]),
            total_return=float(saved_row[8]),
            sharpe_ratio=float(saved_row[9]),
            max_drawdown=float(saved_row[10]),
            win_rate=float(saved_row[11]),
            total_trades=int(saved_row[12]),
            trade_log=parse_json_field(saved_row[13]),
            equity_curve=parse_json_field(saved_row[14]),
            benchmark_curve=benchmark_records,
            run_at=saved_row[15]
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", response_model=List[BacktestSummary])
def list_backtest_runs(
    ticker: Optional[str] = Query(None),
    strategy_id: Optional[int] = Query(None)
):
    try:
        runs = get_backtest_runs(ticker=ticker, strategy_id=strategy_id)
        return [
            BacktestSummary(
                id=r[0],
                execute_on=r[1],
                strategy_id=r[2],
                start_date=r[3],
                end_date=r[4],
                initial_capital=float(r[5]),
                total_return=float(r[6]),
                sharpe_ratio=float(r[7]),
                max_drawdown=float(r[8]),
                win_rate=float(r[9]),
                total_trades=int(r[10]),
                run_at=r[11]
            )
            for r in runs
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{run_id}", response_model=BacktestDetail)
def get_backtest_detail(run_id: int):
    saved_row = fetch_backtest_run(run_id)
    if saved_row is None:
        raise HTTPException(status_code=404, detail=f"Backtest run #{run_id} not found.")
        
    # Get price data to reconstruct benchmark curve
    try:
        df = get_price_data(saved_row[3], str(saved_row[4]), str(saved_row[5]))
        benchmark_df = compute_benchmark(df, float(saved_row[6]))
        benchmark_records = [
            {"date": str(idx)[:10] if hasattr(idx, "strftime") else str(idx), "value": float(val)}
            for idx, val in benchmark_df["value"].items()
        ]
    except Exception:
        benchmark_records = []
        
    return BacktestDetail(
        id=saved_row[0],
        strategy_id=saved_row[1],
        execute_on=saved_row[3],
        start_date=saved_row[4],
        end_date=saved_row[5],
        initial_capital=float(saved_row[6]),
        total_return=float(saved_row[8]),
        sharpe_ratio=float(saved_row[9]),
        max_drawdown=float(saved_row[10]),
        win_rate=float(saved_row[11]),
        total_trades=int(saved_row[12]),
        trade_log=parse_json_field(saved_row[13]),
        equity_curve=parse_json_field(saved_row[14]),
        benchmark_curve=benchmark_records,
        run_at=saved_row[15]
    )
