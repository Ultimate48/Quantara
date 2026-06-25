import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
import json
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
    df = df.astype({"open": "float64", "high": "float64", "low": "float64", "close": "float64", "volume": "float64"})
    return df

def get_all_stocks() -> list:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT ticker, name, market, added_at FROM stocks ORDER BY added_at DESC;")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

def save_backtest_run(result: dict) -> int:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO backtest_runs (
            strategy_id, data_tickers, execute_on, start_date, end_date,
            initial_capital, final_value, total_return,
            sharpe_ratio, max_drawdown, win_rate, total_trades,
            trade_log, equity_curve
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id;
    """, (
        result["strategy_id"],
        result["data_tickers"],
        result["execute_on"],
        result["start_date"],
        result["end_date"],
        result["initial_capital"],
        result["final_value"],
        result["total_return"],
        result["sharpe_ratio"],
        result["max_drawdown"],
        result["win_rate"],
        result["total_trades"],
        result["trade_log"],
        result["equity_curve"],
    ))
    run_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return run_id   

def get_backtest_runs(ticker: str = None, strategy_id: int = None) -> list:
    conn = get_connection()
    cur = conn.cursor()

    query = """
        SELECT id, execute_on, strategy_id, start_date, end_date,
               initial_capital, total_return, sharpe_ratio,
               max_drawdown, win_rate, total_trades, run_at
        FROM backtest_runs WHERE 1=1
    """
    params = []

    if ticker:
        query += " AND execute_on = %s"
        params.append(ticker)
    if strategy_id:
        query += " AND strategy_id = %s"
        params.append(strategy_id)

    query += " ORDER BY run_at DESC"

    cur.execute(query, params)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

def insert_strategy(name: str, description: str, columns: list, signal_rule: str) -> int:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO strategies (name, description, columns, signal_rule)
        VALUES (%s, %s, %s, %s)
        RETURNING id;
    """, (name, description, json.dumps(columns), signal_rule))
    strategy_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return strategy_id

def fetch_strategy_by_name(name: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, name, description, columns, signal_rule, created_at
        FROM strategies WHERE name = %s;
    """, (name,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row

def fetch_all_strategies():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, name, description, created_at
        FROM strategies ORDER BY created_at DESC;
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

def fetch_backtest_run(run_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, strategy_id, data_tickers, execute_on, start_date, end_date,
               initial_capital, final_value, total_return, sharpe_ratio,
               max_drawdown, win_rate, total_trades, trade_log, equity_curve, run_at
        FROM backtest_runs WHERE id = %s;
    """, (run_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row


def update_strategy(name: str, description: str = None, columns: list = None, signal_rule: str = None) -> bool:
    """Update a strategy by name. Only updates fields that are not None. Returns True if found."""
    conn = get_connection()
    cur = conn.cursor()

    # Build dynamic SET clause
    updates = []
    params = []
    if description is not None:
        updates.append("description = %s")
        params.append(description)
    if columns is not None:
        updates.append("columns = %s")
        params.append(json.dumps(columns))
    if signal_rule is not None:
        updates.append("signal_rule = %s")
        params.append(signal_rule)

    if not updates:
        cur.close()
        conn.close()
        return False

    params.append(name)
    cur.execute(f"""
        UPDATE strategies SET {', '.join(updates)}
        WHERE name = %s;
    """, params)
    updated = cur.rowcount > 0
    conn.commit()
    cur.close()
    conn.close()
    return updated


def delete_strategy(name: str) -> dict:
    """
    Delete a strategy by name.
    Returns {"deleted": True/False, "error": str or None}
    Refuses to delete if backtest_runs reference this strategy.
    """
    conn = get_connection()
    cur = conn.cursor()

    # Find strategy id
    cur.execute("SELECT id FROM strategies WHERE name = %s;", (name,))
    row = cur.fetchone()
    if row is None:
        cur.close()
        conn.close()
        return {"deleted": False, "error": f"Strategy '{name}' not found."}

    strategy_id = row[0]

    # Check for dependent backtest runs
    cur.execute("SELECT COUNT(*) FROM backtest_runs WHERE strategy_id = %s;", (strategy_id,))
    count = cur.fetchone()[0]
    if count > 0:
        cur.close()
        conn.close()
        return {"deleted": False, "error": f"Cannot delete '{name}': {count} backtest run(s) reference it. Delete those first or use --force."}

    cur.execute("DELETE FROM strategies WHERE id = %s;", (strategy_id,))
    conn.commit()
    cur.close()
    conn.close()
    return {"deleted": True, "error": None}


def delete_strategy_force(name: str) -> dict:
    """Delete a strategy and all its backtest runs."""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT id FROM strategies WHERE name = %s;", (name,))
    row = cur.fetchone()
    if row is None:
        cur.close()
        conn.close()
        return {"deleted": False, "error": f"Strategy '{name}' not found."}

    strategy_id = row[0]
    cur.execute("DELETE FROM backtest_runs WHERE strategy_id = %s;", (strategy_id,))
    deleted_runs = cur.rowcount
    cur.execute("DELETE FROM strategies WHERE id = %s;", (strategy_id,))
    conn.commit()
    cur.close()
    conn.close()
    return {"deleted": True, "error": None, "deleted_runs": deleted_runs}


def ticker_exists(ticker: str) -> bool:
    """Check if a ticker exists in the stocks table."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM stocks WHERE ticker = %s;", (ticker,))
    exists = cur.fetchone() is not None
    cur.close()
    conn.close()
    return exists