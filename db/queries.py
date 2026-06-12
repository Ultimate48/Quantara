import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
from db.init import get_connection

def get_price_data(ticker: str, start: str = None, end: str = None) -> pd.DataFrame:
    conn = get_connection()
    cur = conn.cursor()

    query = "SELECT date, open, high, low, close, volume FROM price_data WHERE ticker = %s"
    params = [ticker]

    if start:
        query += " AND date >= %s"
        params.append(start)
    if end:
        query += " AND date <= %s"
        params.append(end)

    query += " ORDER BY date ASC"

    cur.execute(query, params)
    rows = cur.fetchall()
    cur.close()
    conn.close()

    df = pd.DataFrame(rows, columns=["date", "open", "high", "low", "close", "volume"])
    df.set_index("date", inplace=True)
    return df

def get_all_stocks() -> list:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT ticker, name, market, added_at FROM stocks ORDER BY added_at DESC;")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

def save_backtest_run(result: dict):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO backtest_runs (
            ticker, strategy, start_date, end_date,
            initial_capital, final_value, total_return,
            sharpe_ratio, max_drawdown, win_rate, total_trades
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id;
    """, (
        result["ticker"],
        result["strategy"],
        result["start_date"],
        result["end_date"],
        result["initial_capital"],
        result["final_value"],
        result["total_return"],
        result["sharpe_ratio"],
        result["max_drawdown"],
        result["win_rate"],
        result["total_trades"],
    ))
    run_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return run_id

def get_backtest_runs(ticker: str = None, strategy: str = None) -> list:
    conn = get_connection()
    cur = conn.cursor()

    query = """
        SELECT id, ticker, strategy, start_date, end_date,
               initial_capital, total_return, sharpe_ratio,
               max_drawdown, win_rate, total_trades, run_at
        FROM backtest_runs WHERE 1=1
    """
    params = []

    if ticker:
        query += " AND ticker = %s"
        params.append(ticker)
    if strategy:
        query += " AND strategy = %s"
        params.append(strategy)

    query += " ORDER BY run_at DESC"

    cur.execute(query, params)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows