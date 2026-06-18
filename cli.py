import argparse
import json
from data.fetcher import fetch_and_store
from strategies.engine import create_strategy, list_strategies, show_strategy
from backtest.engine import run_backtest, show_saved_run
from db.queries import get_all_stocks, get_backtest_runs, save_backtest_run, fetch_backtest_run

def parse_columns(column_args):
    """Convert ['name = formula', ...] into [{'name': ..., 'formula': ...}, ...]"""
    columns = []
    if column_args:
        for c in column_args:
            name, formula = c.split("=", 1)
            columns.append({"name": name.strip(), "formula": formula.strip()})
    return columns


def main():
    parser = argparse.ArgumentParser(prog="quantara", description="Quantara CLI")
    subparsers = parser.add_subparsers(dest="command")

    # ---------------- fetch ----------------
    fetch_parser = subparsers.add_parser("fetch", help="Fetch stock data")
    fetch_parser.add_argument("ticker", type=str, help="Stock ticker e.g. RELIANCE.NS or AAPL")
    fetch_parser.add_argument("--start", type=str, default=None)
    fetch_parser.add_argument("--end", type=str, default=None)
    fetch_parser.add_argument("--interval", type=str, default="1d")

    # ---------------- stocks ----------------
    subparsers.add_parser("stocks", help="List all stocks in the database")

    # ---------------- results ----------------
    results_parser = subparsers.add_parser("results", help="View past backtest runs")
    results_parser.add_argument("--ticker", type=str, default=None)
    results_parser.add_argument("--strategy", type=str, default=None)

    # ---------------- strategy ----------------
    strategy_parser = subparsers.add_parser("strategy", help="Manage strategies")
    strategy_subparsers = strategy_parser.add_subparsers(dest="strategy_command")

    # strategy create
    strategy_create = strategy_subparsers.add_parser("create", help="Create a new strategy")
    strategy_create.add_argument("--name", type=str, required=True)
    strategy_create.add_argument("--description", type=str, default="")
    strategy_create.add_argument("--column", action="append", dest="columns",
                                  help="Column definition: 'name = formula'. Can be repeated.")
    strategy_create.add_argument("--signal", type=str, required=True,
                                  help="Signal rule e.g. 'rsi < 30 : 1, rsi > 70 : -1, True : 0'")

    # strategy list
    strategy_subparsers.add_parser("list", help="List all saved strategies")

    # strategy show
    strategy_show = strategy_subparsers.add_parser("show", help="Show a strategy's definition")
    strategy_show.add_argument("--name", type=str, required=True)

    # ---------------- backtest ----------------
    backtest_parser = subparsers.add_parser("backtest", help="Run backtests")
    backtest_subparsers = backtest_parser.add_subparsers(dest="backtest_command")

    backtest_run = backtest_subparsers.add_parser("run", help="Run a backtest")
    backtest_run.add_argument("--strategy", type=str, required=True)
    backtest_run.add_argument("--ticker", type=str, required=True)
    backtest_run.add_argument("--start", type=str, default=None)
    backtest_run.add_argument("--end", type=str, default=None)
    backtest_run.add_argument("--capital", type=float, default=100000)
    backtest_run.add_argument("--no-plot", action="store_true", help="Skip showing the plot")
    backtest_show = backtest_subparsers.add_parser("show", help="Show a saved backtest run")
    backtest_show.add_argument("--id", type=int, required=True)

    args = parser.parse_args()

    # ---------------- handlers ----------------
    if args.command == "fetch":
        fetch_and_store(args.ticker, args.start, args.end, args.interval)

    elif args.command == "stocks":
        stocks = get_all_stocks()
        if not stocks:
            print("No stocks in database yet. Use: python cli.py fetch <ticker>")
        else:
            print(f"\n{'Ticker':<15} {'Name':<40} {'Market':<10} {'Added'}")
            print("-" * 80)
            for s in stocks:
                print(f"{s[0]:<15} {s[1]:<40} {s[2]:<10} {str(s[3])[:10]}")



    elif args.command == "results":
        strategy_id = None
        if args.strategy:
            strategy = show_strategy(args.strategy)
            if strategy is None:
                print(f"Strategy '{args.strategy}' not found.")
                return
            strategy_id = strategy["id"]
        runs = get_backtest_runs(args.ticker, strategy_id)
        if not runs:
            print("No backtest runs found.")
        else:
            print(f"\n{'ID':<5} {'Ticker':<12} {'Strategy ID':<12} {'Return':<10} {'Sharpe':<10} {'Drawdown':<12} {'Win Rate':<10} {'Trades':<8} {'Run At'}")
            print("-" * 100)
            for r in runs:
                print(f"{r[0]:<5} {r[1]:<12} {r[2]:<12} {str(r[6])+'%':<10} {str(r[7]):<10} {str(r[8])+'%':<12} {str(r[9])+'%':<10} {str(r[10]):<8} {str(r[11])[:16]}")

    elif args.command == "strategy":
        if args.strategy_command == "create":
            columns = parse_columns(args.columns)
            strategy_id = create_strategy(args.name, args.description, columns, args.signal)
            print(f"Strategy '{args.name}' created with id {strategy_id}")

        elif args.strategy_command == "list":
            strategies = list_strategies()
            if not strategies:
                print("No strategies saved yet.")
            else:
                print(f"\n{'ID':<5} {'Name':<25} {'Description':<40} {'Created'}")
                print("-" * 90)
                for s in strategies:
                    print(f"{s[0]:<5} {s[1]:<25} {(s[2] or '')[:40]:<40} {str(s[3])[:16]}")

        elif args.strategy_command == "show":
            strategy = show_strategy(args.name)
            if strategy is None:
                print(f"Strategy '{args.name}' not found.")
            else:
                print(f"\nName: {strategy['name']}")
                print(f"Description: {strategy['description']}")
                print(f"Created: {strategy['created_at']}")
                print(f"\nColumns:")
                for col in strategy["columns"]:
                    print(f"  {col['name']} = {col['formula']}")
                print(f"\nSignal Rule:\n  {strategy['signal_rule']}")

        else:
            strategy_parser.print_help()

    elif args.command == "backtest":
        if args.backtest_command == "run":
            result = run_backtest(
                name=args.strategy,
                ticker=args.ticker,
                start=args.start,
                end=args.end,
                initial_capital=args.capital,
                show_plot=not args.no_plot
            )

            strategy = show_strategy(args.strategy)
            equity_curve = result["equity_curve"]
            trade_log = result["trade_log"]

            equity_curve_records = [
                {"date": str(idx), "value": float(val)}
                for idx, val in equity_curve["value"].items()
            ]

            trade_log_records = []
            if not trade_log.empty:
                for _, row in trade_log.iterrows():
                    trade_log_records.append({
                        "date": str(row["date"]),
                        "type": row["type"],
                        "price": float(row["price"]),
                        "shares": float(row["shares"]),
                        "cash_after": float(row["cash_after"]),
                    })

            run_id = save_backtest_run({
                "strategy_id": strategy["id"],
                "data_tickers": json.dumps([args.ticker]),
                "execute_on": args.ticker,
                "start_date": equity_curve.index[0],
                "end_date": equity_curve.index[-1],
                "initial_capital": float(args.capital),
                "final_value": float(result["final_value"]),
                "total_return": float(result["metrics"]["total_return"]),
                "sharpe_ratio": float(result["metrics"]["sharpe_ratio"]),
                "max_drawdown": float(result["metrics"]["max_drawdown"]),
                "win_rate": float(result["metrics"]["win_rate"]),
                "total_trades": int(result["metrics"]["total_trades"]),
                "trade_log": json.dumps(trade_log_records),
                "equity_curve": json.dumps(equity_curve_records),
            })
            print(f"Backtest run saved with id {run_id}")

        elif args.backtest_command == "show":
                run_row = fetch_backtest_run(args.id)
                if run_row is None:
                    print(f"No backtest run found with id {args.id}")
                else:
                    show_saved_run(run_row)
                    
        else:
            backtest_parser.print_help()

    else:
        parser.print_help()


if __name__ == "__main__":
    main()