import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import yfinance as yf
from datetime import datetime, timedelta
from db.init import get_connection

try:
    from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, MofNCompleteColumn
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

def fetch_and_store(ticker: str, start: str = None, end: str = None, interval: str = "1d"):
    if start is None:
        start = (datetime.today() - timedelta(days=5*365)).strftime("%Y-%m-%d")
    if end is None:
        end = datetime.today().strftime("%Y-%m-%d")

    # Import display helpers for consistent messaging
    try:
        from ui.display import print_info, print_success, print_error
    except ImportError:
        print_info = print_success = print_error = print

    print_info(f"Fetching [bold]{ticker}[/bold] from {start} to {end} (interval: {interval})..."
               if RICH_AVAILABLE else f"Fetching {ticker} from {start} to {end} (interval: {interval})...")

    stock = yf.Ticker(ticker)
    info = stock.info
    name = info.get("longName") or info.get("shortName") or ticker
    market = "NSE" if ticker.endswith(".NS") else "NYSE" if ticker.endswith(".NYSE") else "US"

    df = stock.history(start=start, end=end, interval=interval)

    if df.empty:
        print_error(f"No data found for {ticker}. Check the ticker symbol.")
        return

    df.reset_index(inplace=True)
    # Only truncate to date for daily intervals; preserve full timestamp for intraday
    if interval == "1d":
        df["Date"] = df["Date"].dt.date

    conn = get_connection()
    cur = conn.cursor()

    # Insert stock if it doesn't exist
    cur.execute("""
        INSERT INTO stocks (ticker, name, market)
        VALUES (%s, %s, %s)
        ON CONFLICT (ticker) DO NOTHING;
    """, (ticker, name, market))

    # Insert price data with progress bar
    inserted = 0
    skipped = 0
    total = len(df)

    if RICH_AVAILABLE and total > 10:
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(bar_width=40),
            MofNCompleteColumn(),
            TextColumn("[dim]{task.fields[status]}"),
            transient=True,
        ) as progress:
            task = progress.add_task(f"Inserting {ticker}", total=total, status="")
            for _, row in df.iterrows():
                try:
                    cur.execute("""
                        INSERT INTO price_data (ticker, date, open, high, low, close, volume)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (ticker, date) DO NOTHING;
                    """, (
                        ticker,
                        row["Date"],
                        round(float(row["Open"]), 4),
                        round(float(row["High"]), 4),
                        round(float(row["Low"]), 4),
                        round(float(row["Close"]), 4),
                        int(row["Volume"]),
                    ))
                    inserted += 1
                except Exception as e:
                    skipped += 1
                progress.update(task, advance=1, status=f"{inserted} inserted, {skipped} skipped")
    else:
        for _, row in df.iterrows():
            try:
                cur.execute("""
                    INSERT INTO price_data (ticker, date, open, high, low, close, volume)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (ticker, date) DO NOTHING;
                """, (
                    ticker,
                    row["Date"],
                    round(float(row["Open"]), 4),
                    round(float(row["High"]), 4),
                    round(float(row["Low"]), 4),
                    round(float(row["Close"]), 4),
                    int(row["Volume"]),
                ))
                inserted += 1
            except Exception as e:
                skipped += 1

    conn.commit()
    cur.close()
    conn.close()

    print_success(f"Done. {inserted} rows inserted, {skipped} skipped for {ticker}."
                  if not RICH_AVAILABLE else
                  f"[bold]{ticker}[/bold]: {inserted} rows inserted, {skipped} skipped.")