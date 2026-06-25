"""
Walk-Forward Testing for Quantara.

Splits a date range into rolling [train_days | test_days] windows.
The training window is used for indicator warm-up; the test window
drives the actual backtest evaluation. Metrics are aggregated across
all test windows to assess strategy consistency.
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
import numpy as np
from backtest.engine import generate_signals, simulate_trades
from analytics.metrics import compute_metrics


def run_walk_forward(
    name: str,
    ticker: str,
    train_days: int = 252,
    test_days: int = 63,
    start: str = None,
    end: str = None,
    initial_capital: float = 100000,
    cooldown: int = 0,
    stop_loss: float = None,
    take_profit: float = None,
    mode: str = "long",
    confirm_buy: int = 1,
    confirm_sell: int = 1,
    position_size: str = "all",
    transaction_cost: float = 0.0,
    slippage: float = 0.0,
) -> dict:
    """
    Run a walk-forward test for a strategy on a ticker.

    Parameters
    ----------
    name          : Strategy name
    ticker        : Stock ticker
    train_days    : Number of calendar days in the warm-up (training) window
    test_days     : Number of calendar days in each test window
    start / end   : Overall date range to analyse
    All other params are passed directly to simulate_trades().

    Returns
    -------
    dict with keys:
      "windows"   : list of per-window result dicts
      "summary"   : aggregate stats (mean, std, min, max per metric)
      "n_windows" : number of completed test windows
    """
    # ── 1. Load signals for the full date range ──────────────────────────────
    full_df = generate_signals(name, ticker, start, end)

    if full_df.empty:
        raise ValueError(f"No price data found for '{ticker}' in the given range.")

    dates = full_df.index
    total_days = (dates[-1] - dates[0]).days

    if train_days + test_days > total_days:
        raise ValueError(
            f"Not enough data for even one window. "
            f"Need at least {train_days + test_days} calendar days, "
            f"but only {total_days} available."
        )

    # ── 2. Build rolling windows ─────────────────────────────────────────────
    windows = []
    window_start = dates[0]

    while True:
        # The test window starts after train_days from window_start
        test_start_dt = window_start + pd.Timedelta(days=train_days)
        test_end_dt = test_start_dt + pd.Timedelta(days=test_days)

        # Stop when the test end exceeds our data
        if test_end_dt > dates[-1]:
            break

        # Slice to test window only (train window provides warm-up context
        # because signals were already computed on the full df)
        test_mask = (full_df.index >= test_start_dt) & (full_df.index <= test_end_dt)
        test_df = full_df[test_mask].copy()

        if len(test_df) < 5:
            # Slide forward and try again
            window_start = test_start_dt
            continue

        # Run trade simulation on test window
        result = simulate_trades(
            test_df, initial_capital, cooldown, stop_loss, take_profit,
            mode, confirm_buy, confirm_sell,
            position_size, transaction_cost, slippage
        )

        metrics = compute_metrics(
            result["equity_curve"], result["trade_log"],
            initial_capital, result["final_value"]
        )

        windows.append({
            "window_num": len(windows) + 1,
            "train_start": str(window_start.date()),
            "train_end": str((test_start_dt - pd.Timedelta(days=1)).date()),
            "test_start": str(test_start_dt.date()),
            "test_end": str(test_end_dt.date()),
            "n_bars": len(test_df),
            "metrics": metrics,
            "final_value": result["final_value"],
            "equity_curve": result["equity_curve"],
            "trade_log": result["trade_log"],
        })

        # Slide forward by test_days
        window_start = test_start_dt

    if not windows:
        raise ValueError("No complete windows could be built from the available data.")

    # ── 3. Aggregate metrics ─────────────────────────────────────────────────
    metric_keys = ["total_return", "sharpe_ratio", "max_drawdown", "win_rate", "total_trades"]
    summary = {}
    for key in metric_keys:
        vals = [w["metrics"][key] for w in windows]
        summary[key] = {
            "mean": round(float(np.mean(vals)), 2),
            "std": round(float(np.std(vals)), 2),
            "min": round(float(np.min(vals)), 2),
            "max": round(float(np.max(vals)), 2),
            "median": round(float(np.median(vals)), 2),
        }

    # Profitable windows
    profitable = sum(1 for w in windows if w["metrics"]["total_return"] > 0)
    summary["profitable_windows"] = profitable
    summary["total_windows"] = len(windows)
    summary["pct_profitable"] = round(profitable / len(windows) * 100, 1)

    return {
        "windows": windows,
        "summary": summary,
        "n_windows": len(windows),
        "strategy": name,
        "ticker": ticker,
        "train_days": train_days,
        "test_days": test_days,
    }


def print_walk_forward(result: dict):
    """Print a walk-forward test result in a formatted table."""
    try:
        from rich.table import Table
        from rich.console import Console
        from rich.panel import Panel
        from rich.text import Text
        from rich import box

        console = Console()
        n = result["n_windows"]
        s = result["summary"]

        # Per-window table
        table = Table(
            title=f"Walk-Forward Results — {result['strategy']} on {result['ticker']}  "
                  f"(train={result['train_days']}d / test={result['test_days']}d)",
            box=box.ROUNDED, header_style="bold cyan", title_style="bold white"
        )
        table.add_column("Win#", justify="right", style="bold")
        table.add_column("Test Period", justify="left", style="dim")
        table.add_column("Bars", justify="right")
        table.add_column("Return", justify="right")
        table.add_column("Sharpe", justify="right")
        table.add_column("Drawdown", justify="right", style="red")
        table.add_column("Win Rate", justify="right")
        table.add_column("Trades", justify="right")

        for w in result["windows"]:
            m = w["metrics"]
            ret = m["total_return"]
            ret_str = f"[green]{ret:.2f}%[/green]" if ret >= 0 else f"[red]{ret:.2f}%[/red]"
            table.add_row(
                str(w["window_num"]),
                f"{w['test_start']} → {w['test_end']}",
                str(w["n_bars"]),
                ret_str,
                f"{m['sharpe_ratio']:.2f}",
                f"{m['max_drawdown']:.2f}%",
                f"{m['win_rate']:.2f}%",
                str(m["total_trades"]),
            )
        console.print(table)

        # Summary panel
        profitable_pct = s["pct_profitable"]
        pct_color = "green" if profitable_pct >= 60 else "yellow" if profitable_pct >= 40 else "red"

        content = Text()
        content.append(f"Windows        : {n}\n")
        content.append(f"Profitable     : ")
        content.append(f"{s['profitable_windows']}/{n} ({profitable_pct}%)\n", style=pct_color)
        content.append(f"\n{'Metric':<18}  {'Mean':>8}  {'Std':>8}  {'Min':>8}  {'Max':>8}\n", style="bold")
        content.append(f"{'─'*58}\n", style="dim")

        for key, label in [
            ("total_return", "Return (%)"),
            ("sharpe_ratio", "Sharpe"),
            ("max_drawdown", "Max Drawdown"),
            ("win_rate", "Win Rate (%)"),
            ("total_trades", "Trades"),
        ]:
            v = s[key]
            content.append(
                f"{label:<18}  {v['mean']:>8.2f}  {v['std']:>8.2f}  {v['min']:>8.2f}  {v['max']:>8.2f}\n"
            )

        panel = Panel(content, title="[bold]Aggregate Summary[/bold]", border_style="blue", expand=False)
        console.print(panel)

    except ImportError:
        # Plain text fallback
        n = result["n_windows"]
        s = result["summary"]
        print(f"\n{'='*70}")
        print(f"Walk-Forward: {result['strategy']} on {result['ticker']}")
        print(f"Windows: {n}  |  Train: {result['train_days']}d  |  Test: {result['test_days']}d")
        print(f"{'='*70}")
        print(f"{'Win#':<5} {'Test Period':<26} {'Return':>9} {'Sharpe':>8} {'DD':>9} {'WinRate':>9} {'Trades':>7}")
        print("-" * 70)
        for w in result["windows"]:
            m = w["metrics"]
            print(
                f"{w['window_num']:<5} {w['test_start']} → {w['test_end']}  "
                f"{m['total_return']:>8.2f}% {m['sharpe_ratio']:>8.2f} "
                f"{m['max_drawdown']:>8.2f}% {m['win_rate']:>8.2f}% {m['total_trades']:>7}"
            )
        print(f"\n{'Metric':<18}  {'Mean':>8}  {'Std':>8}  {'Min':>8}  {'Max':>8}")
        print("-" * 58)
        for key, label in [
            ("total_return", "Return (%)"),
            ("sharpe_ratio", "Sharpe"),
            ("max_drawdown", "Max Drawdown"),
            ("win_rate", "Win Rate (%)"),
            ("total_trades", "Trades"),
        ]:
            v = s[key]
            print(f"{label:<18}  {v['mean']:>8.2f}  {v['std']:>8.2f}  {v['min']:>8.2f}  {v['max']:>8.2f}")
        print(f"\nProfitable windows: {s['profitable_windows']}/{n} ({s['pct_profitable']}%)")
        print("=" * 70)
