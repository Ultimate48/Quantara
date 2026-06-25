import pandas as pd


def compute_metrics(equity_curve: pd.DataFrame, trade_log: pd.DataFrame,
                    initial_capital: float, final_value: float) -> dict:
    """
    Compute backtest performance metrics from equity curve and trade log.
    Pure computation — no side effects or printing.

    Returns dict with: total_return, sharpe_ratio, max_drawdown, win_rate, total_trades
    """
    total_return = (final_value - initial_capital) / initial_capital * 100

    daily_returns = equity_curve["value"].pct_change().dropna()
    if daily_returns.std() != 0:
        sharpe_ratio = (daily_returns.mean() / daily_returns.std()) * (252 ** 0.5)
    else:
        sharpe_ratio = 0

    cummax = equity_curve["value"].cummax()
    drawdown = (equity_curve["value"] - cummax) / cummax
    max_drawdown = drawdown.min() * 100

    total_trades = len(trade_log)

    win_rate = 0.0
    if not trade_log.empty:
        sells = trade_log[trade_log["type"].isin(["sell", "cover"])].reset_index(drop=True)
        buys = trade_log[trade_log["type"].isin(["buy", "short"])].reset_index(drop=True)
        wins = 0
        for i in range(min(len(buys), len(sells))):
            buy_price = buys.iloc[i]["price"]
            sell_price = sells.iloc[i]["price"]
            trade_type = buys.iloc[i]["type"]
            if trade_type == "buy" and sell_price > buy_price:
                wins += 1
            elif trade_type == "short" and sell_price < buy_price:
                wins += 1
        if len(sells) > 0:
            win_rate = wins / len(sells) * 100

    return {
        "total_return": round(total_return, 2),
        "sharpe_ratio": round(sharpe_ratio, 2),
        "max_drawdown": round(max_drawdown, 2),
        "win_rate": round(win_rate, 2),
        "total_trades": total_trades,
    }
