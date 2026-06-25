import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
import matplotlib.pyplot as plt
from db.queries import get_price_data
from strategies.engine import apply_columns, apply_signal_rule, load_strategy
from analytics.metrics import compute_metrics


def generate_signals(name: str, ticker: str, start: str = None, end: str = None) -> pd.DataFrame:
    strategy = load_strategy(name)
    if strategy is None:
        raise ValueError(f"Strategy '{name}' not found.")

    df = get_price_data(ticker, start, end)
    df = apply_columns(df, strategy["columns"])
    df = apply_signal_rule(df, strategy["signal_rule"])
    return df


def simulate_trades(df: pd.DataFrame, initial_capital: float = 100000, cooldown: int = 0,
                    stop_loss: float = None, take_profit: float = None,
                    mode: str = "long", confirm_buy: int = 1, confirm_sell: int = 1) -> dict:
    """
    mode: "long" — long only (default)
          "short" — short only
          "long_short" — both directions
    """
    cash = initial_capital
    shares = 0.0
    short_shares = 0.0
    short_entry_price = None
    portfolio_values = []
    trades = []
    cooldown_remaining = 0
    entry_price = None
    buy_streak = 0
    sell_streak = 0

    for date, row in df.iterrows():
        price = row["close"]
        signal = row["signal"]

        if cooldown_remaining > 0:
            cooldown_remaining -= 1

        # ── Stop loss / take profit on LONG position ──
        if shares > 0 and entry_price is not None:
            price_change = (price - entry_price) / entry_price

            if stop_loss is not None and price_change <= -stop_loss:
                proceeds = shares * price
                trades.append({"date": date, "type": "sell", "price": price,
                                "shares": shares, "cash_after": proceeds, "reason": "stop_loss"})
                cash = proceeds
                shares = 0.0
                entry_price = None
                cooldown_remaining = cooldown
                portfolio_values.append({"date": date, "value": cash})
                continue

            if take_profit is not None and price_change >= take_profit:
                proceeds = shares * price
                trades.append({"date": date, "type": "sell", "price": price,
                                "shares": shares, "cash_after": proceeds, "reason": "take_profit"})
                cash = proceeds
                shares = 0.0
                entry_price = None
                cooldown_remaining = cooldown
                portfolio_values.append({"date": date, "value": cash})
                continue

        # ── Stop loss / take profit on SHORT position ──
        if short_shares > 0 and short_entry_price is not None:
            price_change = (price - short_entry_price) / short_entry_price

            if stop_loss is not None and price_change >= stop_loss:
                # price rose X% above short entry — stop loss
                pnl = (short_entry_price - price) * short_shares
                cash = cash + pnl
                trades.append({"date": date, "type": "cover", "price": price,
                                "shares": short_shares, "cash_after": cash, "reason": "stop_loss"})
                short_shares = 0.0
                short_entry_price = None
                cooldown_remaining = cooldown
                portfolio_values.append({"date": date, "value": cash})
                continue

            if take_profit is not None and price_change <= -take_profit:
                # price fell X% below short entry — take profit
                pnl = (short_entry_price - price) * short_shares
                cash = cash + pnl
                trades.append({"date": date, "type": "cover", "price": price,
                                "shares": short_shares, "cash_after": cash, "reason": "take_profit"})
                short_shares = 0.0
                short_entry_price = None
                cooldown_remaining = cooldown
                portfolio_values.append({"date": date, "value": cash})
                continue

        # ── Signal handling ──
        # Track confirmation streaks
        if signal == 1:
            buy_streak += 1
            sell_streak = 0
        elif signal == -1:
            sell_streak += 1
            buy_streak = 0
        else:
            buy_streak = 0
            sell_streak = 0

        buy_confirmed = buy_streak >= confirm_buy
        sell_confirmed = sell_streak >= confirm_sell

        if buy_confirmed:
            # Cover short first if in short position
            if short_shares > 0 and mode in ["long_short"]:
                pnl = (short_entry_price - price) * short_shares
                cash = cash + pnl
                trades.append({"date": date, "type": "cover", "price": price,
                                "shares": short_shares, "cash_after": cash, "reason": "signal"})
                short_shares = 0.0
                short_entry_price = None
                cooldown_remaining = cooldown

            # Go long if allowed
            if mode in ["long", "long_short"] and cash > 0 and cooldown_remaining == 0:
                shares_bought = cash / price
                shares += shares_bought
                entry_price = price
                trades.append({"date": date, "type": "buy", "price": price,
                                "shares": shares_bought, "cash_after": 0.0, "reason": "signal"})
                cash = 0.0

        elif sell_confirmed:
            # Sell long first if in long position
            if shares > 0 and mode in ["long", "long_short"]:
                proceeds = shares * price
                trades.append({"date": date, "type": "sell", "price": price,
                                "shares": shares, "cash_after": proceeds, "reason": "signal"})
                cash = proceeds
                shares = 0.0
                entry_price = None
                cooldown_remaining = cooldown

            # Go short if allowed
            if mode in ["short", "long_short"] and short_shares == 0 and cooldown_remaining == 0:
                short_shares = cash / price
                short_entry_price = price
                trades.append({"date": date, "type": "short", "price": price,
                                "shares": short_shares, "cash_after": cash, "reason": "signal"})
        # Portfolio value calculation
        long_value = shares * price
        short_pnl = (short_entry_price - price) * short_shares if short_shares > 0 and short_entry_price else 0
        portfolio_value = cash + long_value + short_pnl
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
    first_price = float(df["close"].iloc[0])
    shares = initial_capital / first_price
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
        sells = trade_log[trade_log["type"].isin(["sell", "cover"])]
        shorts = trade_log[trade_log["type"] == "short"]

        if not buys.empty:
            buy_values = equity_curve.loc[buys["date"], "value"]
            axes[0].scatter(buys["date"], buy_values, color="green", marker="^", s=100, label="Buy", zorder=5)

        if not sells.empty:
            sell_values = equity_curve.loc[sells["date"], "value"]
            axes[0].scatter(sells["date"], sell_values, color="red", marker="v", s=100, label="Sell/Cover", zorder=5)

        if not shorts.empty:
            short_values = equity_curve.loc[shorts["date"], "value"]
            axes[0].scatter(shorts["date"], short_values, color="orange", marker="v", s=100, label="Short", zorder=5)

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
    """Compute metrics and print summary. Returns metrics dict."""
    equity_curve = result["equity_curve"]
    trade_log = result["trade_log"]
    initial_capital = result["initial_capital"]
    final_value = result["final_value"]

    metrics = compute_metrics(equity_curve, trade_log, initial_capital, final_value)

    print(f"\n{'='*50}")
    print(f"Backtest: {strategy_name} on {ticker}")
    print(f"{'='*50}")
    print(f"Initial Capital : {initial_capital:,.2f}")
    print(f"Final Value     : {final_value:,.2f}")
    print(f"Total Return    : {metrics['total_return']:.2f}%")
    print(f"Sharpe Ratio    : {metrics['sharpe_ratio']:.2f}")
    print(f"Max Drawdown    : {metrics['max_drawdown']:.2f}%")
    print(f"Win Rate        : {metrics['win_rate']:.2f}%")
    print(f"Total Trades    : {metrics['total_trades']}")
    print(f"{'='*50}\n")

    return metrics


def compare_backtests(results: list, ticker: str):
    """
    Print a side-by-side comparison table for multiple backtest results.
    results: list of {"name": str, "metrics": dict, "initial_capital": float, "final_value": float}
    """
    if not results:
        return

    # Header
    name_width = max(len(r["name"]) for r in results) + 2
    print(f"\n{'='*80}")
    print(f"Strategy Comparison on {ticker}")
    print(f"{'='*80}")
    print(f"{'Metric':<20}", end="")
    for r in results:
        print(f"{r['name']:>{name_width}}", end="")
    print()
    print("-" * (20 + name_width * len(results)))

    # Rows
    metric_labels = [
        ("Initial Capital", "initial_capital", "{:,.0f}"),
        ("Final Value", "final_value", "{:,.0f}"),
        ("Total Return", "total_return", "{:.2f}%"),
        ("Sharpe Ratio", "sharpe_ratio", "{:.2f}"),
        ("Max Drawdown", "max_drawdown", "{:.2f}%"),
        ("Win Rate", "win_rate", "{:.2f}%"),
        ("Total Trades", "total_trades", "{}"),
    ]

    for label, key, fmt in metric_labels:
        print(f"{label:<20}", end="")
        for r in results:
            if key in ("initial_capital", "final_value"):
                val = r[key]
            else:
                val = r["metrics"][key]
            print(f"{fmt.format(val):>{name_width}}", end="")
        print()

    print(f"{'='*80}\n")


def show_saved_run(run_row):
    import json as json_module

    (run_id, strategy_id, data_tickers, execute_on, start_date, end_date,
     initial_capital, final_value, total_return, sharpe_ratio,
     max_drawdown, win_rate, total_trades, trade_log_json, equity_curve_json, run_at) = run_row

    equity_data = trade_log_json if isinstance(trade_log_json, list) else json_module.loads(trade_log_json) if trade_log_json else []
    trade_log = pd.DataFrame(equity_data)
    if not trade_log.empty:
        trade_log["date"] = pd.to_datetime(trade_log["date"])

    # Handle legacy runs where equity_curve was not stored
    has_equity_curve = equity_curve_json is not None
    if has_equity_curve:
        equity_raw = equity_curve_json if isinstance(equity_curve_json, list) else json_module.loads(equity_curve_json)
        equity_curve = pd.DataFrame(equity_raw)
        equity_curve["date"] = pd.to_datetime(equity_curve["date"])
        equity_curve.set_index("date", inplace=True)
    else:
        equity_curve = pd.DataFrame(columns=["value"])

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

    if not trade_log.empty:
        print("Trade log:")
        print(trade_log)

    if has_equity_curve and not equity_curve.empty:
        df = get_price_data(execute_on, str(start_date), str(end_date))
        result = {
            "equity_curve": equity_curve,
            "trade_log": trade_log,
            "final_value": final_value,
            "initial_capital": initial_capital,
        }
        plot_results(df, result, execute_on, f"strategy_{strategy_id}")
    else:
        print("(No equity curve data stored — this is a legacy run.)")


def run_backtest(name: str, ticker: str, start: str = None, end: str = None,
                 initial_capital: float = 100000, show_plot: bool = True,
                 cooldown: int = 0, stop_loss: float = None, take_profit: float = None,
                 mode: str = "long", confirm_buy: int = 1, confirm_sell: int = 1) -> dict:
    df = generate_signals(name, ticker, start, end)
    result = simulate_trades(df, initial_capital, cooldown, stop_loss, take_profit, mode, confirm_buy, confirm_sell)
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