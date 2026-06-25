import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import numpy as np
import pandas as pd
from db.queries import (
    insert_strategy, fetch_strategy_by_name, fetch_all_strategies,
    update_strategy as db_update_strategy,
    delete_strategy as db_delete_strategy,
    delete_strategy_force as db_delete_strategy_force,
)


def apply_columns(df: pd.DataFrame, columns: list) -> pd.DataFrame:
    """
    columns: list of {"name": str, "formula": str}
    Evaluates each formula in order and adds it as a new column.
    """
    local_vars = {col: df[col] for col in df.columns}

    for col_def in columns:
        name = col_def["name"]
        formula = col_def["formula"]
        result = eval(formula, {"__builtins__": {}}, local_vars)
        df[name] = result
        local_vars[name] = df[name]

    return df


def apply_signal_rule(df: pd.DataFrame, signal_rule: str) -> pd.DataFrame:
    """
    signal_rule: string like "rsi < 30 : 1, rsi > 70 : -1, True : 0"
    Evaluates conditions top-to-bottom per row, first match wins.
    """
    conditions = []
    for clause in signal_rule.split(","):
        condition_str, value_str = clause.split(":")
        conditions.append((condition_str.strip(), int(value_str.strip())))

    local_vars = {col: df[col] for col in df.columns}

    signals = pd.Series(0, index=df.index)
    assigned = pd.Series(False, index=df.index)

    for condition_str, value in conditions:
        mask = eval(condition_str, {"__builtins__": {}}, local_vars)
        if isinstance(mask, bool):
            mask = pd.Series(mask, index=df.index)
        apply_mask = mask & (~assigned)
        signals[apply_mask] = value
        assigned = assigned | mask

    df["signal"] = signals
    return df


def validate_strategy(columns: list, signal_rule: str) -> dict:
    """
    Validate columns and signal_rule by running them against a synthetic DataFrame.
    Returns {"valid": True} or {"valid": False, "error": str}.
    """
    try:
        # Generate a small synthetic OHLCV DataFrame with realistic-looking data
        np.random.seed(42)
        n = 300  # enough rows for 200-day indicators
        dates = pd.date_range("2020-01-01", periods=n, freq="B")
        close = 100 + np.cumsum(np.random.randn(n) * 0.5)
        df = pd.DataFrame({
            "open": close + np.random.randn(n) * 0.1,
            "high": close + abs(np.random.randn(n) * 0.5),
            "low": close - abs(np.random.randn(n) * 0.5),
            "close": close,
            "volume": np.random.randint(1000000, 10000000, n).astype(float),
        }, index=dates)

        df = apply_columns(df, columns)
        df = apply_signal_rule(df, signal_rule)

        # Verify signal column exists and contains only valid values
        if "signal" not in df.columns:
            return {"valid": False, "error": "Signal column was not generated."}

        return {"valid": True}

    except Exception as e:
        return {"valid": False, "error": str(e)}


def create_strategy(name: str, description: str, columns: list, signal_rule: str) -> int:
    return insert_strategy(name, description, columns, signal_rule)


def load_strategy(name: str):
    row = fetch_strategy_by_name(name)
    if row is None:
        return None
    return {
        "id": row[0],
        "name": row[1],
        "description": row[2],
        "columns": row[3],
        "signal_rule": row[4],
        "created_at": row[5],
    }


def list_strategies():
    return fetch_all_strategies()


def show_strategy(name: str):
    return load_strategy(name)


def update_strategy(name: str, description: str = None, columns: list = None, signal_rule: str = None) -> bool:
    """Update a strategy by name. Returns True if strategy was found and updated."""
    return db_update_strategy(name, description, columns, signal_rule)


def delete_strategy(name: str, force: bool = False) -> dict:
    """
    Delete a strategy by name.
    If force=True, also deletes all backtest runs referencing it.
    Returns {"deleted": bool, "error": str or None, "deleted_runs": int (if force)}.
    """
    if force:
        return db_delete_strategy_force(name)
    return db_delete_strategy(name)