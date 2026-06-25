"""
Regime Detection for Quantara.

Classifies each trading day as 'bull', 'bear', or 'sideways' using
a combination of price position relative to the 200-day SMA and the
slope of that SMA.  Then splits backtest metrics by regime to show
where a strategy works and where it doesn't.
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
import numpy as np
from analytics.metrics import compute_metrics


def detect_regime(
    df: pd.DataFrame,
    sma_period: int = 200,
    slope_lookback: int = 20,
    slope_threshold: float = 0.001,
) -> pd.Series:
    """
    Classify each bar as 'bull', 'bear', or 'sideways'.

    Rules:
      bull     : close > SMA AND SMA slope is positive (> threshold)
      bear     : close < SMA AND SMA slope is negative (< -threshold)
      sideways : everything else (SMA flat or price crossing SMA)

    Parameters
    ----------
    df               : DataFrame with at least a 'close' column
    sma_period       : SMA period (default 200)
    slope_lookback   : How many bars to use for slope estimation
    slope_threshold  : Minimum absolute slope (fraction/bar) to count as trending

    Returns
    -------
    pd.Series of strings ('bull' / 'bear' / 'sideways'), same index as df
    """
    close = df["close"]
    sma = close.rolling(sma_period).mean()

    # Slope = percentage change of SMA over slope_lookback bars
    sma_slope = sma.pct_change(slope_lookback)

    regime = pd.Series("sideways", index=df.index, dtype=str)

    bull_mask = (close > sma) & (sma_slope > slope_threshold)
    bear_mask = (close < sma) & (sma_slope < -slope_threshold)

    regime[bull_mask] = "bull"
    regime[bear_mask] = "bear"

    return regime


def analyze_by_regime(
    equity_curve: pd.DataFrame,
    trade_log: pd.DataFrame,
    regime_series: pd.Series,
    initial_capital: float,
) -> dict:
    """
    Compute performance metrics split by market regime.

    Parameters
    ----------
    equity_curve   : DataFrame with 'value' column, indexed by date
    trade_log      : Trade log from simulate_trades()
    regime_series  : Output of detect_regime() — Series indexed by date
    initial_capital: Starting capital for each regime sub-period

    Returns
    -------
    dict mapping regime name → metrics dict (+ extra regime-level stats)
    """
    results = {}

    for regime_name in ["bull", "bear", "sideways"]:
        mask = regime_series == regime_name
        regime_equity = equity_curve[equity_curve.index.isin(regime_series[mask].index)]

        if regime_equity.empty or len(regime_equity) < 2:
            results[regime_name] = {
                "n_bars": 0,
                "pct_of_time": 0.0,
                "metrics": None,
            }
            continue

        # Filter trades that fall inside this regime
        if not trade_log.empty:
            regime_dates = set(regime_equity.index)
            regime_trades = trade_log[trade_log["date"].isin(regime_dates)].copy()
        else:
            regime_trades = pd.DataFrame()

        # Use the first value of this regime's equity curve as the starting capital
        segment_start = float(regime_equity["value"].iloc[0])
        segment_end = float(regime_equity["value"].iloc[-1])

        metrics = compute_metrics(
            regime_equity, regime_trades, segment_start, segment_end
        )

        n_total = len(equity_curve)
        n_regime = len(regime_equity)

        results[regime_name] = {
            "n_bars": n_regime,
            "pct_of_time": round(n_regime / n_total * 100, 1) if n_total > 0 else 0.0,
            "start_value": round(segment_start, 2),
            "end_value": round(segment_end, 2),
            "metrics": metrics,
        }

    return results


def print_regime_analysis(regime_results: dict, ticker: str, strategy_name: str):
    """Print regime analysis in a formatted table."""
    try:
        from rich.table import Table
        from rich.console import Console
        from rich import box

        console = Console()
        table = Table(
            title=f"Regime Analysis — {strategy_name} on {ticker}",
            box=box.ROUNDED, header_style="bold cyan", title_style="bold white"
        )
        table.add_column("Regime", style="bold")
        table.add_column("% Time", justify="right")
        table.add_column("Bars", justify="right")
        table.add_column("Return", justify="right")
        table.add_column("Sharpe", justify="right")
        table.add_column("Max DD", justify="right", style="red")
        table.add_column("Win Rate", justify="right")
        table.add_column("Trades", justify="right")

        regime_styles = {"bull": "green", "bear": "red", "sideways": "yellow"}

        for regime_name in ["bull", "bear", "sideways"]:
            r = regime_results.get(regime_name, {})
            if not r or r["n_bars"] == 0:
                table.add_row(
                    f"[{regime_styles[regime_name]}]{regime_name.capitalize()}[/{regime_styles[regime_name]}]",
                    "—", "0", "—", "—", "—", "—", "—"
                )
                continue

            m = r["metrics"]
            ret = m["total_return"]
            ret_color = "green" if ret >= 0 else "red"
            style = regime_styles[regime_name]

            table.add_row(
                f"[{style}]{regime_name.capitalize()}[/{style}]",
                f"{r['pct_of_time']}%",
                str(r["n_bars"]),
                f"[{ret_color}]{ret:.2f}%[/{ret_color}]",
                f"{m['sharpe_ratio']:.2f}",
                f"{m['max_drawdown']:.2f}%",
                f"{m['win_rate']:.2f}%",
                str(m["total_trades"]),
            )

        console.print(table)

    except ImportError:
        print(f"\n{'='*70}")
        print(f"Regime Analysis: {strategy_name} on {ticker}")
        print(f"{'='*70}")
        print(f"{'Regime':<12} {'%Time':>7} {'Bars':>6} {'Return':>9} {'Sharpe':>8} {'MaxDD':>9} {'WinRate':>9} {'Trades':>7}")
        print("-" * 70)
        for regime_name in ["bull", "bear", "sideways"]:
            r = regime_results.get(regime_name, {})
            if not r or r["n_bars"] == 0:
                print(f"{regime_name.capitalize():<12} {'—':>7}")
                continue
            m = r["metrics"]
            print(
                f"{regime_name.capitalize():<12} {r['pct_of_time']:>6.1f}% "
                f"{r['n_bars']:>6} {m['total_return']:>8.2f}% "
                f"{m['sharpe_ratio']:>8.2f} {m['max_drawdown']:>8.2f}% "
                f"{m['win_rate']:>8.2f}% {m['total_trades']:>7}"
            )
        print("=" * 70)
