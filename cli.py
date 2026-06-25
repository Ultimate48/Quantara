import argparse
import json
import sys
from data.fetcher import fetch_and_store
from db.queries import (
    get_all_stocks, get_backtest_runs, save_backtest_run,
    fetch_backtest_run, ticker_exists,
)
from strategies.engine import (
    create_strategy, list_strategies, show_strategy,
    update_strategy, delete_strategy, validate_strategy,
)
from strategies.indicators import expand_indicator, list_indicators
from backtest.engine import run_backtest, show_saved_run, compare_backtests
from ui.display import (
    print_success, print_error, print_warning, print_info,
    print_table, print_metrics, print_strategy_detail,
    print_comparison, print_indicators,
)


def parse_columns(column_args):
    """Convert ['name = formula', ...] into [{'name': ..., 'formula': ...}, ...]"""
    columns = []
    if column_args:
        for c in column_args:
            if "=" not in c:
                print_error(f"Invalid column format: '{c}'. Expected 'name = formula'.")
                sys.exit(1)
            name, formula = c.split("=", 1)
            columns.append({"name": name.strip(), "formula": formula.strip()})
    return columns


def main():
    parser = argparse.ArgumentParser(prog="quantara", description="Quantara — Algorithmic Trading Research Platform")
    subparsers = parser.add_subparsers(dest="command")

    # ── fetch ──
    fetch_parser = subparsers.add_parser("fetch", help="Fetch stock data from Yahoo Finance")
    fetch_parser.add_argument("ticker", type=str, help="Stock ticker e.g. RELIANCE.NS or AAPL")
    fetch_parser.add_argument("--start", type=str, default=None)
    fetch_parser.add_argument("--end", type=str, default=None)
    fetch_parser.add_argument("--interval", type=str, default="1d",
                               help="Data interval: 1m, 5m, 15m, 30m, 1h, 1d (default), 1wk, 1mo")

    # ── stocks ──
    subparsers.add_parser("stocks", help="List all stocks in the database")

    # ── results ──
    results_parser = subparsers.add_parser("results", help="View past backtest runs")
    results_parser.add_argument("--ticker", type=str, default=None)
    results_parser.add_argument("--strategy", type=str, default=None)

    # ── strategy ──
    strategy_parser = subparsers.add_parser("strategy", help="Manage strategies")
    strategy_subparsers = strategy_parser.add_subparsers(dest="strategy_command")

    # strategy create
    strategy_create = strategy_subparsers.add_parser("create", help="Create a new strategy")
    strategy_create.add_argument("--name", type=str, required=True)
    strategy_create.add_argument("--description", type=str, default="")
    strategy_create.add_argument("--column", action="append", dest="columns",
                                  help="Column definition: 'name = formula'. Can be repeated.")
    strategy_create.add_argument("--indicator", action="append", dest="indicators",
                                  help="Predefined indicator shortcut e.g. 'RSI,14', 'MACD,12,26,9'. Can be repeated.")
    strategy_create.add_argument("--signal", type=str, required=True,
                                  help="Signal rule e.g. 'rsi < 30 : 1, rsi > 70 : -1, True : 0'")

    # strategy update
    strategy_update = strategy_subparsers.add_parser("update", help="Update an existing strategy")
    strategy_update.add_argument("--name", type=str, required=True, help="Name of strategy to update")
    strategy_update.add_argument("--description", type=str, default=None)
    strategy_update.add_argument("--column", action="append", dest="columns",
                                  help="New column definitions (replaces all existing columns)")
    strategy_update.add_argument("--indicator", action="append", dest="indicators",
                                  help="Predefined indicator shortcut. Can be repeated.")
    strategy_update.add_argument("--signal", type=str, default=None, help="New signal rule")

    # strategy delete
    strategy_delete = strategy_subparsers.add_parser("delete", help="Delete a strategy")
    strategy_delete.add_argument("--name", type=str, required=True)
    strategy_delete.add_argument("--force", action="store_true",
                                  help="Force delete even if backtest runs reference this strategy")

    # strategy list
    strategy_subparsers.add_parser("list", help="List all saved strategies")

    # strategy show
    strategy_show = strategy_subparsers.add_parser("show", help="Show a strategy's definition")
    strategy_show.add_argument("--name", type=str, required=True)

    # strategy indicators — list available presets
    strategy_subparsers.add_parser("indicators", help="List available indicator presets")

    # ── backtest ──
    backtest_parser = subparsers.add_parser("backtest", help="Run and view backtests")
    backtest_subparsers = backtest_parser.add_subparsers(dest="backtest_command")

    # ── shared backtest flags (used by both 'run' and 'walk-forward') ──
    def _add_common_backtest_args(p):
        p.add_argument("--strategy", type=str, required=True)
        p.add_argument("--ticker", type=str, required=True)
        p.add_argument("--start", type=str, default=None)
        p.add_argument("--end", type=str, default=None)
        p.add_argument("--capital", type=float, default=100000)
        p.add_argument("--cooldown", type=int, default=0, help="Cooldown days after a sell")
        p.add_argument("--stop-loss", type=float, default=None, help="Stop loss e.g. 0.05 for 5%%")
        p.add_argument("--take-profit", type=float, default=None, help="Take profit e.g. 0.15 for 15%%")
        p.add_argument("--short-only", action="store_true", help="Only take short positions")
        p.add_argument("--long-short", action="store_true", help="Take both long and short positions")
        p.add_argument("--confirm", type=int, default=None, help="Confirmation days for both buy and sell signals")
        p.add_argument("--confirm-buy", type=int, default=None, help="Confirmation days for buy signal")
        p.add_argument("--confirm-sell", type=int, default=None, help="Confirmation days for sell signal")
        # Batch 2 — new flags
        p.add_argument("--position-size", type=str, default="all",
                       help="Position sizing: 'all' (default), 'fixed:50000', 'pct:50', 'volatility:14'")
        p.add_argument("--transaction-cost", type=float, default=0.0,
                       help="Transaction cost fraction per trade e.g. 0.001 for 0.1%%")
        p.add_argument("--slippage", type=float, default=0.0,
                       help="Slippage fraction e.g. 0.001 for 0.1%%")

    # backtest run
    backtest_run = backtest_subparsers.add_parser("run", help="Run a backtest")
    _add_common_backtest_args(backtest_run)
    backtest_run.add_argument("--no-plot", action="store_true", help="Skip showing the plot")
    backtest_run.add_argument("--compare", type=str, default=None,
                               help="Compare with another strategy (runs both, prints side-by-side metrics)")
    # Batch 2 — analysis flags
    backtest_run.add_argument("--monte-carlo", type=int, default=None, metavar="N",
                               help="Run N Monte Carlo simulations after the backtest")
    backtest_run.add_argument("--regime", action="store_true",
                               help="Run regime detection analysis after the backtest")
    backtest_run.add_argument("--correlation", action="store_true",
                               help="Run correlation analysis vs buy-and-hold after the backtest")

    # backtest walk-forward
    backtest_wf = backtest_subparsers.add_parser("walk-forward", help="Run a walk-forward test")
    _add_common_backtest_args(backtest_wf)
    backtest_wf.add_argument("--train-days", type=int, default=252,
                              help="Training / warm-up window in calendar days (default: 252)")
    backtest_wf.add_argument("--test-days", type=int, default=63,
                              help="Test window in calendar days (default: 63 ≈ 1 quarter)")

    # backtest show
    backtest_show = backtest_subparsers.add_parser("show", help="Show a saved backtest run")
    backtest_show.add_argument("--id", type=int, required=True)

    args = parser.parse_args()

    # ──────────────────────────────────────────────────────────────────────────
    # Handlers
    # ──────────────────────────────────────────────────────────────────────────

    if args.command == "fetch":
        fetch_and_store(args.ticker, args.start, args.end, args.interval)

    elif args.command == "stocks":
        stocks = get_all_stocks()
        if not stocks:
            print_warning("No stocks in database yet. Use: python cli.py fetch <ticker>")
        else:
            columns = [
                ("Ticker", "left", "cyan"),
                ("Name", "left", None),
                ("Market", "left", "yellow"),
                ("Added", "left", "dim"),
            ]
            rows = [(s[0], s[1], s[2], str(s[3])[:10]) for s in stocks]
            print_table("Stocks in Database", columns, rows)

    elif args.command == "results":
        strategy_id = None
        if args.strategy:
            strategy = show_strategy(args.strategy)
            if strategy is None:
                print_error(f"Strategy '{args.strategy}' not found.")
                return
            strategy_id = strategy["id"]
        runs = get_backtest_runs(args.ticker, strategy_id)
        if not runs:
            print_warning("No backtest runs found.")
        else:
            columns = [
                ("ID", "right", "bold"),
                ("Ticker", "left", "cyan"),
                ("Strategy", "right", None),
                ("Return", "right", "green"),
                ("Sharpe", "right", None),
                ("Drawdown", "right", "red"),
                ("Win Rate", "right", None),
                ("Trades", "right", None),
                ("Run At", "left", "dim"),
            ]
            rows = [
                (r[0], str(r[1]), str(r[2]),
                 f"{r[6]}%", str(r[7]), f"{r[8]}%", f"{r[9]}%",
                 str(r[10]), str(r[11])[:16])
                for r in runs
            ]
            print_table("Backtest Results", columns, rows)

    elif args.command == "strategy":
        if args.strategy_command == "create":
            indicator_columns = []
            if args.indicators:
                for ind_str in args.indicators:
                    try:
                        indicator_columns.extend(expand_indicator(ind_str))
                    except ValueError as e:
                        print_error(str(e))
                        return

            user_columns = parse_columns(args.columns)
            all_columns = indicator_columns + user_columns

            if not all_columns:
                print_error("No columns defined. Use --column or --indicator to define at least one computed column.")
                return

            validation = validate_strategy(all_columns, args.signal)
            if not validation["valid"]:
                print_error(f"Strategy validation failed: {validation['error']}")
                print_info("Fix your column formulas or signal rule and try again.")
                return

            try:
                strategy_id = create_strategy(args.name, args.description, all_columns, args.signal)
                print_success(f"Strategy '{args.name}' created with id {strategy_id}")
            except Exception as e:
                error_msg = str(e)
                if "unique" in error_msg.lower() or "duplicate" in error_msg.lower():
                    print_error(f"Strategy '{args.name}' already exists. Use 'strategy update --name {args.name}' to modify it.")
                else:
                    print_error(f"Failed to create strategy: {error_msg}")

        elif args.strategy_command == "update":
            existing = show_strategy(args.name)
            if existing is None:
                print_error(f"Strategy '{args.name}' not found.")
                return

            new_columns = None
            if args.columns or args.indicators:
                indicator_columns = []
                if args.indicators:
                    for ind_str in args.indicators:
                        try:
                            indicator_columns.extend(expand_indicator(ind_str))
                        except ValueError as e:
                            print_error(str(e))
                            return
                user_columns = parse_columns(args.columns)
                new_columns = indicator_columns + user_columns

            validate_cols = new_columns if new_columns is not None else existing["columns"]
            validate_signal = args.signal if args.signal is not None else existing["signal_rule"]

            validation = validate_strategy(validate_cols, validate_signal)
            if not validation["valid"]:
                print_error(f"Strategy validation failed: {validation['error']}")
                return

            updated = update_strategy(args.name, args.description, new_columns, args.signal)
            if updated:
                print_success(f"Strategy '{args.name}' updated.")
            else:
                print_warning(f"No changes made to '{args.name}'.")

        elif args.strategy_command == "delete":
            result = delete_strategy(args.name, force=args.force)
            if result["deleted"]:
                msg = f"Strategy '{args.name}' deleted."
                if "deleted_runs" in result and result["deleted_runs"] > 0:
                    msg += f" ({result['deleted_runs']} backtest run(s) also removed.)"
                print_success(msg)
            else:
                print_error(result["error"])

        elif args.strategy_command == "list":
            strategies = list_strategies()
            if not strategies:
                print_warning("No strategies saved yet.")
            else:
                columns = [
                    ("ID", "right", "bold"),
                    ("Name", "left", "cyan"),
                    ("Description", "left", None),
                    ("Created", "left", "dim"),
                ]
                rows = [(s[0], s[1], (s[2] or "")[:50], str(s[3])[:16]) for s in strategies]
                print_table("Saved Strategies", columns, rows)

        elif args.strategy_command == "show":
            strategy = show_strategy(args.name)
            if strategy is None:
                print_error(f"Strategy '{args.name}' not found.")
            else:
                print_strategy_detail(strategy)

        elif args.strategy_command == "indicators":
            indicators = list_indicators()
            print_indicators(indicators)

        else:
            strategy_parser.print_help()

    elif args.command == "backtest":

        # ── backtest run ──────────────────────────────────────────────────────
        if args.backtest_command == "run":
            if not ticker_exists(args.ticker):
                print_error(f"Ticker '{args.ticker}' not found in database. Run 'python cli.py fetch {args.ticker}' first.")
                return

            strategy = show_strategy(args.strategy)
            if strategy is None:
                print_error(f"Strategy '{args.strategy}' not found. Run 'python cli.py strategy list' to see available strategies.")
                return

            mode = "long"
            if args.long_short:
                mode = "long_short"
            elif args.short_only:
                mode = "short"

            confirm_buy = args.confirm if args.confirm is not None else 1
            confirm_sell = args.confirm if args.confirm is not None else 1
            if args.confirm_buy is not None:
                confirm_buy = args.confirm_buy
            if args.confirm_sell is not None:
                confirm_sell = args.confirm_sell

            result = run_backtest(
                name=args.strategy,
                ticker=args.ticker,
                start=args.start,
                end=args.end,
                initial_capital=args.capital,
                show_plot=not args.no_plot,
                cooldown=args.cooldown,
                stop_loss=args.stop_loss,
                take_profit=args.take_profit,
                mode=mode,
                confirm_buy=confirm_buy,
                confirm_sell=confirm_sell,
                position_size=args.position_size,
                transaction_cost=args.transaction_cost,
                slippage=args.slippage,
            )

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
                        "reason": row.get("reason", "signal"),
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
            print_success(f"Backtest run saved with id {run_id}")

            # ── Compare mode ──
            if args.compare:
                compare_strategy = show_strategy(args.compare)
                if compare_strategy is None:
                    print_error(f"Comparison strategy '{args.compare}' not found.")
                else:
                    print_info(f"Running comparison backtest with '{args.compare}'...")
                    compare_result = run_backtest(
                        name=args.compare,
                        ticker=args.ticker,
                        start=args.start,
                        end=args.end,
                        initial_capital=args.capital,
                        show_plot=False,
                        cooldown=args.cooldown,
                        stop_loss=args.stop_loss,
                        take_profit=args.take_profit,
                        mode=mode,
                        confirm_buy=confirm_buy,
                        confirm_sell=confirm_sell,
                        position_size=args.position_size,
                        transaction_cost=args.transaction_cost,
                        slippage=args.slippage,
                    )
                    comparison = [
                        {
                            "name": args.strategy,
                            "metrics": result["metrics"],
                            "initial_capital": args.capital,
                            "final_value": result["final_value"],
                        },
                        {
                            "name": args.compare,
                            "metrics": compare_result["metrics"],
                            "initial_capital": args.capital,
                            "final_value": compare_result["final_value"],
                        },
                    ]
                    print_comparison(comparison, args.ticker)

            # ── Monte Carlo ──
            if args.monte_carlo and args.monte_carlo > 0:
                from backtest.monte_carlo import run_monte_carlo, print_monte_carlo
                print_info(f"Running {args.monte_carlo:,} Monte Carlo simulations...")
                mc_result = run_monte_carlo(
                    trade_log=result["trade_log"],
                    initial_capital=args.capital,
                    n_simulations=args.monte_carlo,
                    show_plot=not args.no_plot,
                )
                print_monte_carlo(mc_result)

            # ── Regime analysis ──
            if args.regime:
                from analytics.regime import detect_regime, analyze_by_regime, print_regime_analysis
                print_info("Running regime analysis...")
                regime_series = detect_regime(result["df"])
                regime_results = analyze_by_regime(
                    result["equity_curve"],
                    result["trade_log"],
                    regime_series,
                    args.capital,
                )
                print_regime_analysis(regime_results, args.ticker, args.strategy)

            # ── Correlation analysis ──
            if args.correlation:
                from backtest.engine import compute_benchmark
                from analytics.correlation import analyze_correlation, print_correlation
                print_info("Running correlation analysis...")
                benchmark = compute_benchmark(result["df"], args.capital)
                corr_result = analyze_correlation(result["equity_curve"], benchmark)
                print_correlation(corr_result, args.ticker, args.strategy,
                                  show_plot=not args.no_plot)

        # ── backtest walk-forward ─────────────────────────────────────────────
        elif args.backtest_command == "walk-forward":
            if not ticker_exists(args.ticker):
                print_error(f"Ticker '{args.ticker}' not found in database. Run 'python cli.py fetch {args.ticker}' first.")
                return

            strategy = show_strategy(args.strategy)
            if strategy is None:
                print_error(f"Strategy '{args.strategy}' not found. Run 'python cli.py strategy list' to see available strategies.")
                return

            mode = "long"
            if args.long_short:
                mode = "long_short"
            elif args.short_only:
                mode = "short"

            confirm_buy = args.confirm if args.confirm is not None else 1
            confirm_sell = args.confirm if args.confirm is not None else 1
            if args.confirm_buy is not None:
                confirm_buy = args.confirm_buy
            if args.confirm_sell is not None:
                confirm_sell = args.confirm_sell

            print_info(
                f"Running walk-forward test: train={args.train_days}d, test={args.test_days}d ..."
            )

            from backtest.walk_forward import run_walk_forward, print_walk_forward
            try:
                wf_result = run_walk_forward(
                    name=args.strategy,
                    ticker=args.ticker,
                    train_days=args.train_days,
                    test_days=args.test_days,
                    start=args.start,
                    end=args.end,
                    initial_capital=args.capital,
                    cooldown=args.cooldown,
                    stop_loss=args.stop_loss,
                    take_profit=args.take_profit,
                    mode=mode,
                    confirm_buy=confirm_buy,
                    confirm_sell=confirm_sell,
                    position_size=args.position_size,
                    transaction_cost=args.transaction_cost,
                    slippage=args.slippage,
                )
                print_walk_forward(wf_result)
            except ValueError as e:
                print_error(str(e))

        # ── backtest show ─────────────────────────────────────────────────────
        elif args.backtest_command == "show":
            run_row = fetch_backtest_run(args.id)
            if run_row is None:
                print_error(f"No backtest run found with id {args.id}")
            else:
                show_saved_run(run_row)

        else:
            backtest_parser.print_help()

    else:
        parser.print_help()


if __name__ == "__main__":
    main()