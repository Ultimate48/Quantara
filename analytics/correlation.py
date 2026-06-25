"""
Correlation Analysis for Quantara.

Measures how much a strategy's returns are driven by the market
(buy-and-hold benchmark) vs being genuinely independent.

Computes:
  - Overall correlation (Pearson R)
  - Rolling correlation over a configurable window
  - Beta (sensitivity to market moves)
  - Alpha (CAPM excess return, annualised)
  - R-squared
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
import numpy as np


def analyze_correlation(
    equity_curve: pd.DataFrame,
    benchmark: pd.DataFrame,
    window: int = 60,
    risk_free_rate: float = 0.0,
) -> dict:
    """
    Compute correlation, beta, and alpha between a strategy and a benchmark.

    Parameters
    ----------
    equity_curve    : DataFrame with 'value' column from simulate_trades()
    benchmark       : DataFrame with 'value' column from compute_benchmark()
    window          : Rolling window in bars for rolling correlation
    risk_free_rate  : Annual risk-free rate (default 0; used for alpha calc)

    Returns
    -------
    dict with:
      correlation         : float — Pearson R, overall
      beta                : float — regression slope (strategy vs benchmark)
      alpha               : float — annualised CAPM alpha (%)
      r_squared           : float — R² of the linear regression
      rolling_correlation : pd.Series — rolling R over `window` bars
      strategy_return     : float — total strategy return (%)
      benchmark_return    : float — total benchmark return (%)
      n_bars              : int
    """
    # Align both series on common dates
    strat = equity_curve["value"].copy()
    bench = benchmark["value"].copy()
    common_idx = strat.index.intersection(bench.index)

    if len(common_idx) < 10:
        return {
            "correlation": 0.0,
            "beta": 0.0,
            "alpha": 0.0,
            "r_squared": 0.0,
            "rolling_correlation": pd.Series(dtype=float),
            "strategy_return": 0.0,
            "benchmark_return": 0.0,
            "n_bars": len(common_idx),
        }

    strat = strat.loc[common_idx]
    bench = bench.loc[common_idx]

    # Daily returns
    strat_returns = strat.pct_change().dropna()
    bench_returns = bench.pct_change().dropna()

    common_ret_idx = strat_returns.index.intersection(bench_returns.index)
    strat_r = strat_returns.loc[common_ret_idx]
    bench_r = bench_returns.loc[common_ret_idx]

    # Overall correlation
    correlation = float(strat_r.corr(bench_r)) if len(strat_r) > 1 else 0.0

    # Beta and alpha via OLS (manual, no scipy dependency)
    bench_mean = bench_r.mean()
    strat_mean = strat_r.mean()
    bench_var = bench_r.var()

    if bench_var == 0:
        beta = 0.0
        alpha_daily = strat_mean
    else:
        cov = float(((bench_r - bench_mean) * (strat_r - strat_mean)).mean())
        beta = cov / float(bench_var)
        alpha_daily = strat_mean - beta * bench_mean

    # Annualise alpha; subtract risk-free rate (daily)
    rf_daily = risk_free_rate / 252
    alpha_annualised = (alpha_daily - rf_daily) * 252 * 100  # as percentage

    # R-squared
    r_squared = correlation ** 2

    # Rolling correlation
    rolling_corr = strat_r.rolling(window).corr(bench_r)

    # Total returns
    strategy_return = (float(strat.iloc[-1]) - float(strat.iloc[0])) / float(strat.iloc[0]) * 100
    benchmark_return = (float(bench.iloc[-1]) - float(bench.iloc[0])) / float(bench.iloc[0]) * 100

    return {
        "correlation": round(correlation, 4),
        "beta": round(beta, 4),
        "alpha": round(alpha_annualised, 2),
        "r_squared": round(r_squared, 4),
        "rolling_correlation": rolling_corr,
        "strategy_return": round(strategy_return, 2),
        "benchmark_return": round(benchmark_return, 2),
        "n_bars": len(common_idx),
        "window": window,
    }


def print_correlation(result: dict, ticker: str, strategy_name: str, show_plot: bool = True):
    """Print correlation analysis summary."""
    try:
        from rich.console import Console
        from rich.panel import Panel
        from rich.text import Text

        console = Console()

        corr = result["correlation"]
        beta = result["beta"]
        alpha = result["alpha"]
        r2 = result["r_squared"]

        corr_color = "yellow" if abs(corr) > 0.7 else "green" if abs(corr) < 0.3 else "white"
        alpha_color = "green" if alpha > 0 else "red"

        content = Text()
        content.append(f"Strategy        : {strategy_name} on {ticker}\n")
        content.append(f"Bars analysed   : {result['n_bars']}\n\n")
        content.append(f"Strategy return : {result['strategy_return']:.2f}%\n")
        content.append(f"Benchmark return: {result['benchmark_return']:.2f}%\n\n")
        content.append(f"Correlation (R) : ")
        content.append(f"{corr:.4f}\n", style=corr_color)
        content.append(f"Beta            : {beta:.4f}\n")
        content.append(f"Alpha (ann.)    : ")
        content.append(f"{alpha:.2f}%\n", style=alpha_color)
        content.append(f"R-squared       : {r2:.4f}\n\n")

        # Interpretation
        if abs(corr) > 0.85:
            interp = "[yellow]High market correlation — strategy moves with the market.[/yellow]"
        elif abs(corr) > 0.5:
            interp = "[white]Moderate correlation — some market exposure.[/white]"
        else:
            interp = "[green]Low correlation — strategy appears market-independent.[/green]"
        content.append("Interpretation  : ")
        content.append_text(Text.from_markup(interp))
        content.append("\n")

        if beta > 1.2:
            content.append("Beta note       : [yellow]Amplified market moves (high leverage-like exposure).[/yellow]\n")
        elif beta < 0:
            content.append("Beta note       : [green]Negative beta — potential hedge.[/green]\n")

        panel = Panel(content, title="[bold]Correlation Analysis[/bold]",
                      border_style="cyan", expand=False)
        console.print(panel)

    except ImportError:
        r = result
        print(f"\n{'='*50}")
        print(f"Correlation Analysis: {strategy_name} on {ticker}")
        print(f"{'='*50}")
        print(f"Strategy return  : {r['strategy_return']:.2f}%")
        print(f"Benchmark return : {r['benchmark_return']:.2f}%")
        print(f"Correlation (R)  : {r['correlation']:.4f}")
        print(f"Beta             : {r['beta']:.4f}")
        print(f"Alpha (ann.)     : {r['alpha']:.2f}%")
        print(f"R-squared        : {r['r_squared']:.4f}")
        print("=" * 50)

    if show_plot and not result["rolling_correlation"].empty:
        _plot_rolling_correlation(result, ticker, strategy_name)


def _plot_rolling_correlation(result: dict, ticker: str, strategy_name: str):
    """Plot rolling correlation between strategy and benchmark."""
    try:
        import matplotlib.pyplot as plt

        rolling = result["rolling_correlation"].dropna()
        if rolling.empty:
            return

        fig, ax = plt.subplots(figsize=(12, 4))
        ax.plot(rolling.index, rolling, color="#4a90d9", linewidth=1.2, label=f"Rolling {result['window']}-bar correlation")
        ax.axhline(result["correlation"], color="#f59e0b", linestyle="--", linewidth=1,
                   label=f"Overall R = {result['correlation']:.3f}")
        ax.axhline(0, color="gray", linewidth=0.7, linestyle="-")
        ax.fill_between(rolling.index, rolling, 0, alpha=0.15, color="#4a90d9")
        ax.set_ylim(-1.05, 1.05)
        ax.set_title(f"Rolling Correlation — {strategy_name} vs Buy & Hold ({ticker})")
        ax.set_ylabel("Pearson R")
        ax.legend(fontsize=9)
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.show()
    except Exception:
        pass
