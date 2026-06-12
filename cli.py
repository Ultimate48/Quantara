import argparse
from data.fetcher import fetch_and_store

def main():
    parser = argparse.ArgumentParser(prog="quantara", description="Quantara CLI")
    subparsers = parser.add_subparsers(dest="command")

    # fetch command
    fetch_parser = subparsers.add_parser("fetch", help="Fetch stock data")
    fetch_parser.add_argument("ticker", type=str, help="Stock ticker e.g. RELIANCE.NS or AAPL")
    fetch_parser.add_argument("--start", type=str, help="Start date YYYY-MM-DD", default=None)
    fetch_parser.add_argument("--end", type=str, help="End date YYYY-MM-DD", default=None)

    args = parser.parse_args()

    if args.command == "fetch":
        fetch_and_store(args.ticker, args.start, args.end)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()