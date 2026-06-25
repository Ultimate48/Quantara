"""
Monte Carlo Simulation for Quantara.

Takes a completed trade log and reruns the trade sequence in randomized
order N times to distinguish luck from edge.  Reports the distribution
of possible outcomes and overlays the actual result.
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
import numpy as np


def _extract_trade_returns(trade_log: pd.DataFrame) -> list:
    """
    Extract per-round-trip return from a trade log.

    Pairs buys with sells (longs) and shorts with covers.
    Returns a list of fractional returns, e.g. 0.05 = +5%.
    """
    if trade_log.empty:
        return []

    returns = []
    buys = trade_log[trade_log["type"].isin(["buy", "short"])].reset_index(drop=True)
    sells = trade_log[trade_log["type"].isin(["sell", "cover"])].reset_index(drop=True)

    for i in range(min(len(buys), len(sells))):
        entry_price = buys.iloc[i]["price"]
        exit_price = sells.iloc[i]["price"]
        trade_type = buys.iloc[i]["type"]

        if entry_price <= 0:
            continue

        if trade_type == "buy":
            ret = (exit_price - entry_price) / entry_price
        else:  # short
            ret = (entry_price - exit_price) / entry_price

        returns.append(ret)

    return returns


def run_monte_carlo(
    trade_log: pd.DataFrame,
    initial_capital: float = 100000,
    n_simulations: int = 1000,
    show_plot: bool = True,
) -> dict:
    """
    Run Monte Carlo simulation by shuffling trade returns N times.

    Parameters
    ----------
    trade_log       : Trade log DataFrame from simulate_trades()
    initial_capital : Starting capital
    n_simulations   : Number of randomised simulations to run
    show_plot       : Whether to show a histogram of outcomes

    Returns
    -------
    dict with keys:
      trade_returns    : list of per-trade fractional returns
      final_values     : np.array of simulated final portfolio values
      actual_value     : actual final value from the original run
      median           : median simulated final value
      mean             : mean simulated final value
      p5               : 5th percentile
      p25              : 25th percentile
      p75              : 75th percentile
      p95              : 95th percentile
      prob_profit      : probability of ending above initial_capital
      max_sim_drawdown : worst simulated max drawdown across all runs
    """
    trade_returns = _extract_trade_returns(trade_log)

    if not trade_returns:
        return {
            "trade_returns": [],
            "final_values": np.array([initial_capital]),
            "actual_value": initial_capital,
            "median": initial_capital,
            "mean": initial_capital,
            "p5": initial_capital,
            "p25": initial_capital,
            "p75": initial_capital,
            "p95": initial_capital,
            "prob_profit": 0.0,
            "max_sim_drawdown": 0.0,
            "n_simulations": 0,
            "n_trades": 0,
        }

    n_trades = len(trade_returns)
    returns_arr = np.array(trade_returns)

    # Actual final value (applying returns in original order)
    actual_value = initial_capital
    for r in trade_returns:
        actual_value *= (1 + r)

    # Simulate: shuffle trade order N times
    rng = np.random.default_rng(seed=42)
    final_values = np.empty(n_simulations)

    for i in range(n_simulations):
        shuffled = rng.permutation(returns_arr)
        val = initial_capital
        for r in shuffled:
            val *= (1 + r)
        final_values[i] = val

    prob_profit = float((final_values > initial_capital).mean() * 100)

    # Worst simulated max drawdown (approximate: use geometric equity path)
    drawdowns = []
    for i in range(min(n_simulations, 200)):  # sample 200 to avoid slowdown
        shuffled = rng.permutation(returns_arr)
        equity = np.cumprod(np.concatenate([[1.0], 1 + shuffled])) * initial_capital
        peak = np.maximum.accumulate(equity)
        dd = ((equity - peak) / peak).min() * 100
        drawdowns.append(dd)
    max_sim_drawdown = round(float(np.min(drawdowns)), 2)

    result = {
        "trade_returns": trade_returns,
        "final_values": final_values,
        "actual_value": round(actual_value, 2),
        "median": round(float(np.median(final_values)), 2),
        "mean": round(float(np.mean(final_values)), 2),
        "p5": round(float(np.percentile(final_values, 5)), 2),
        "p25": round(float(np.percentile(final_values, 25)), 2),
        "p75": round(float(np.percentile(final_values, 75)), 2),
        "p95": round(float(np.percentile(final_values, 95)), 2),
        "prob_profit": round(prob_profit, 1),
        "max_sim_drawdown": max_sim_drawdown,
        "n_simulations": n_simulations,
        "n_trades": n_trades,
        "initial_capital": initial_capital,
    }

    if show_plot:
        _plot_monte_carlo(result)

    return result


def _plot_monte_carlo(result: dict):
    """Plot a histogram of simulated final values."""
    try:
        import matplotlib.pyplot as plt
        import matplotlib.patches as mpatches

        final_values = result["final_values"]
        actual = result["actual_value"]
        initial = result["initial_capital"]

        fig, ax = plt.subplots(figsize=(10, 5))

        # Histogram
        n_bins = min(60, result["n_simulations"] // 10)
        ax.hist(final_values, bins=n_bins, color="#4a90d9", alpha=0.7, edgecolor="white", linewidth=0.4)

        # Vertical lines
        ax.axvline(actual, color="#f59e0b", linewidth=2, label=f"Actual outcome: {actual:,.0f}")
        ax.axvline(result["median"], color="#10b981", linewidth=1.5, linestyle="--",
                   label=f"Median: {result['median']:,.0f}")
        ax.axvline(result["p5"], color="#ef4444", linewidth=1, linestyle=":",
                   label=f"5th pct: {result['p5']:,.0f}")
        ax.axvline(result["p95"], color="#8b5cf6", linewidth=1, linestyle=":",
                   label=f"95th pct: {result['p95']:,.0f}")
        ax.axvline(initial, color="gray", linewidth=1, linestyle="-",
                   label=f"Initial capital: {initial:,.0f}")

        ax.set_title(
            f"Monte Carlo Simulation — {result['n_simulations']:,} runs, {result['n_trades']} trades\n"
            f"Prob. of profit: {result['prob_profit']}%",
            fontsize=12
        )
        ax.set_xlabel("Final Portfolio Value")
        ax.set_ylabel("Frequency")
        ax.legend(fontsize=9)
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.show()

    except Exception:
        pass  # Silently skip if matplotlib unavailable or display not available


def print_monte_carlo(result: dict):
    """Print Monte Carlo summary in rich or plain text."""
    try:
        from rich.console import Console
        from rich.panel import Panel
        from rich.text import Text
        from rich import box

        console = Console()
        pp = result["prob_profit"]
        pp_color = "green" if pp >= 60 else "yellow" if pp >= 40 else "red"

        content = Text()
        content.append(f"Simulations     : {result['n_simulations']:,}\n")
        content.append(f"Trades sampled  : {result['n_trades']}\n")
        content.append(f"Initial capital : {result['initial_capital']:>14,.2f}\n\n")
        content.append(f"Actual outcome  : {result['actual_value']:>14,.2f}\n")
        content.append(f"Median outcome  : {result['median']:>14,.2f}\n")
        content.append(f"Mean outcome    : {result['mean']:>14,.2f}\n")
        content.append(f"5th  percentile : {result['p5']:>14,.2f}\n")
        content.append(f"25th percentile : {result['p25']:>14,.2f}\n")
        content.append(f"75th percentile : {result['p75']:>14,.2f}\n")
        content.append(f"95th percentile : {result['p95']:>14,.2f}\n\n")
        content.append(f"Prob. of profit : ")
        content.append(f"{pp}%\n", style=pp_color)
        content.append(f"Worst sim DD    : {result['max_sim_drawdown']:.2f}%\n", style="red")

        panel = Panel(content, title="[bold]Monte Carlo Simulation[/bold]",
                      border_style="cyan", expand=False)
        console.print(panel)

    except ImportError:
        r = result
        print(f"\n{'='*50}")
        print(f"Monte Carlo Simulation ({r['n_simulations']:,} runs, {r['n_trades']} trades)")
        print(f"{'='*50}")
        print(f"Initial capital : {r['initial_capital']:,.2f}")
        print(f"Actual outcome  : {r['actual_value']:,.2f}")
        print(f"Median outcome  : {r['median']:,.2f}")
        print(f"Mean outcome    : {r['mean']:,.2f}")
        print(f"5th  percentile : {r['p5']:,.2f}")
        print(f"95th percentile : {r['p95']:,.2f}")
        print(f"Prob. of profit : {r['prob_profit']}%")
        print(f"Worst sim DD    : {r['max_sim_drawdown']:.2f}%")
        print("=" * 50)
