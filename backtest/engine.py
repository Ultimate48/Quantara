import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
import matplotlib.pyplot as plt
from db.queries import get_price_data
from strategies.engine import apply_columns, apply_signal_rule, load_strategy


def generate_signals(name: str, ticker: str, start: str = None, end: str = None) -> pd.DataFrame:
    strategy = load_strategy(name)
    if strategy is None:
        raise ValueError(f"Strategy '{name}' not found.")

    df = get_price_data(ticker, start, end)
    df = apply_columns(df, strategy["columns"])
    df = apply_signal_rule(df, strategy["signal_rule"])
    return df


def simulate_trades(df: pd.DataFrame, initial_capital: float = 100000) -> dict:
    cash = initial_capital
    shares = 0.0
    portfolio_values = []
    trades = []

    for date, row in df.iterrows():
        price = row["close"]
        signal = row["signal"]

        if signal == 1 and cash > 0:
            shares_bought = cash / price
            shares += shares_bought
            trades.append({
                "date": date, "type": "buy", "price": price,
                "shares": shares_bought, "cash_after": 0.0
            })
            cash = 0.0

        elif signal == -1 and shares > 0:
            proceeds = shares * price
            trades.append({
                "date": date, "type": "sell", "price": price,
                "shares": shares, "cash_after": proceeds
            })
            cash = proceeds
            shares = 0.0

        portfolio_value = cash + shares * price
        portfolio_values.append({"date": date, "value": portfolio_value})

    equity_curve = pd.DataFrame(portfolio_values).set_index("date")
    trade_log = pd.DataFrame(trades)

    return {
        "equity_curve": equity_curve,
        "trade_log": trade_log,
        "final_value": portfolio_values[-1]["value"] if portfolio_values else initial_capital,
        "initial_capital": initial_capital,
    }


def compute_benchmark(df: pd.DataFrame, initial_capital: float = 100000) -> pd.DataFrame:
    first_price = df["close"].iloc[0]
    shares = float(initial_capital) / first_price
    benchmark = (df["close"] * shares).to_frame(name="value")
    return benchmark


def plot_results(df: pd.DataFrame, result: dict, ticker: str, strategy_name: str):
    equity_curve = result["equity_curve"]
    trade_log = result["trade_log"]
    benchmark = compute_benchmark(df, result["initial_capital"])

    drawdown = (equity_curve["value"] - equity_curve["value"].cummax()) / equity_curve["value"].cummax() * 100

    fig, axes = plt.subplots(2, 1, figsize=(12, 8), sharex=True, gridspec_kw={"height_ratios": [3, 1]})

    axes[0].plot(equity_curve.index, equity_curve["value"], label=f"{strategy_name} (strategy)", color="blue")
    axes[0].plot(benchmark.index, benchmark["value"], label="Buy & Hold", color="gray", linestyle="--")

    if not trade_log.empty:
        buys = trade_log[trade_log["type"] == "buy"]
        sells = trade_log[trade_log["type"] == "sell"]

        if not buys.empty:
            buy_values = equity_curve.loc[buys["date"], "value"]
            axes[0].scatter(buys["date"], buy_values, color="green", marker="^", s=100, label="Buy", zorder=5)

        if not sells.empty:
            sell_values = equity_curve.loc[sells["date"], "value"]
            axes[0].scatter(sells["date"], sell_values, color="red", marker="v", s=100, label="Sell", zorder=5)

    axes[0].set_title(f"{strategy_name} on {ticker} — Equity Curve")
    axes[0].set_ylabel("Portfolio Value")
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)

    axes[1].fill_between(drawdown.index, drawdown, 0, color="red", alpha=0.4)
    axes[1].set_title("Drawdown (%)")
    axes[1].set_ylabel("Drawdown %")
    axes[1].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.show()

def print_summary(result: dict, ticker: str, strategy_name: str):
    equity_curve = result["equity_curve"]
    trade_log = result["trade_log"]
    initial_capital = result["initial_capital"]
    final_value = result["final_value"]

    total_return = (final_value - initial_capital) / initial_capital * 100

    daily_returns = equity_curve["value"].pct_change().dropna()
    sharpe_ratio = (daily_returns.mean() / daily_returns.std()) * (252 ** 0.5) if daily_returns.std() != 0 else 0

    cummax = equity_curve["value"].cummax()
    drawdown = (equity_curve["value"] - cummax) / cummax
    max_drawdown = drawdown.min() * 100

    total_trades = len(trade_log)

    win_rate = 0.0
    if not trade_log.empty:
        sells = trade_log[trade_log["type"] == "sell"].reset_index(drop=True)
        buys = trade_log[trade_log["type"] == "buy"].reset_index(drop=True)
        wins = 0
        for i in range(min(len(buys), len(sells))):
            if sells.iloc[i]["price"] > buys.iloc[i]["price"]:
                wins += 1
        if len(sells) > 0:
            win_rate = wins / len(sells) * 100

    print(f"\n{'='*50}")
    print(f"Backtest: {strategy_name} on {ticker}")
    print(f"{'='*50}")
    print(f"Initial Capital : {initial_capital:,.2f}")
    print(f"Final Value     : {final_value:,.2f}")
    print(f"Total Return    : {total_return:.2f}%")
    print(f"Sharpe Ratio    : {sharpe_ratio:.2f}")
    print(f"Max Drawdown    : {max_drawdown:.2f}%")
    print(f"Win Rate        : {win_rate:.2f}%")
    print(f"Total Trades    : {total_trades}")
    print(f"{'='*50}\n")

    return {
        "total_return": round(total_return, 2),
        "sharpe_ratio": round(sharpe_ratio, 2),
        "max_drawdown": round(max_drawdown, 2),
        "win_rate": round(win_rate, 2),
        "total_trades": total_trades,
    }


def run_backtest(name: str, ticker: str, start: str = None, end: str = None,
                 initial_capital: float = 100000, show_plot: bool = True) -> dict:
    """
    Single entry point: generates signals, simulates trades,
    prints summary, optionally plots results.
    Returns combined results dict.
    """
    df = generate_signals(name, ticker, start, end)
    result = simulate_trades(df, initial_capital)
    metrics = print_summary(result, ticker, name)

    if show_plot:
        plot_results(df, result, ticker, name)

    return {
        "df": df,
        "equity_curve": result["equity_curve"],
        "trade_log": result["trade_log"],
        "initial_capital": initial_capital,
        "final_value": result["final_value"],
        "metrics": metrics,
    }

def show_saved_run(run_row):
    """
    run_row: tuple from fetch_backtest_run
    Reconstructs equity_curve and trade_log DataFrames and plots them.
    """
    import json as json_module

    (run_id, strategy_id, data_tickers, execute_on, start_date, end_date,
     initial_capital, final_value, total_return, sharpe_ratio,
     max_drawdown, win_rate, total_trades, trade_log_json, equity_curve_json, run_at) = run_row

    equity_data = trade_log_json if isinstance(trade_log_json, list) else json_module.loads(trade_log_json) if trade_log_json else []
    trade_log = pd.DataFrame(equity_data)
    if not trade_log.empty:
        trade_log["date"] = pd.to_datetime(trade_log["date"])

    equity_raw = equity_curve_json if isinstance(equity_curve_json, list) else json_module.loads(equity_curve_json)
    equity_curve = pd.DataFrame(equity_raw)
    equity_curve["date"] = pd.to_datetime(equity_curve["date"])
    equity_curve.set_index("date", inplace=True)

    # Reconstruct df with close prices for benchmark
    df = get_price_data(execute_on, str(start_date), str(end_date))

    result = {
        "equity_curve": equity_curve,
        "trade_log": trade_log,
        "final_value": final_value,
        "initial_capital": initial_capital,
    }

    print(f"\n{'='*50}")
    print(f"Backtest Run #{run_id} — Strategy ID {strategy_id} on {execute_on}")
    print(f"{'='*50}")
    print(f"Period          : {start_date} to {end_date}")
    print(f"Initial Capital : {float(initial_capital):,.2f}")
    print(f"Final Value     : {float(final_value):,.2f}")
    print(f"Total Return    : {total_return}%")
    print(f"Sharpe Ratio    : {sharpe_ratio}")
    print(f"Max Drawdown    : {max_drawdown}%")
    print(f"Win Rate        : {win_rate}%")
    print(f"Total Trades    : {total_trades}")
    print(f"{'='*50}\n")

    print("Trade log:")
    print(trade_log)

    plot_results(df, result, execute_on, f"strategy_{strategy_id}")