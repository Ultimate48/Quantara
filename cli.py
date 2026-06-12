import argparse
from data.fetcher import fetch_and_store
from db.queries import get_all_stocks, get_backtest_runs

def main():
    parser = argparse.ArgumentParser(prog="quantara", description="Quantara CLI")
    subparsers = parser.add_subparsers(dest="command")

    # fetch command
    fetch_parser = subparsers.add_parser("fetch", help="Fetch stock data")
    fetch_parser.add_argument("ticker", type=str, help="Stock ticker e.g. RELIANCE.NS or AAPL")
    fetch_parser.add_argument("--start", type=str, help="Start date YYYY-MM-DD", default=None)
    fetch_parser.add_argument("--end", type=str, help="End date YYYY-MM-DD", default=None)
    fetch_parser.add_argument("--interval", type=str, help="Data interval e.g. 1d 1h 5m", default="1d")

    # stocks command
    subparsers.add_parser("stocks", help="List all stocks in the database")

    # results command
    results_parser = subparsers.add_parser("results", help="View past backtest runs")
    results_parser.add_argument("--ticker", type=str, help="Filter by ticker", default=None)
    results_parser.add_argument("--strategy", type=str, help="Filter by strategy", default=None)

    args = parser.parse_args()

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
        runs = get_backtest_runs(args.ticker, args.strategy)
        if not runs:
            print("No backtest runs found.")
        else:
            print(f"\n{'ID':<5} {'Ticker':<12} {'Strategy':<15} {'Return':<10} {'Sharpe':<10} {'Drawdown':<12} {'Win Rate':<10} {'Trades':<8} {'Run At'}")
            print("-" * 100)
            for r in runs:
                print(f"{r[0]:<5} {r[1]:<12} {r[2]:<15} {str(r[6])+'%':<10} {str(r[7]):<10} {str(r[8])+'%':<12} {str(r[9])+'%':<10} {str(r[10]):<8} {str(r[11])[:16]}")

    else:
        parser.print_help()

if __name__ == "__main__":
    main()