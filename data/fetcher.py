import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import yfinance as yf
from datetime import datetime, timedelta
from db.init import get_connection

def fetch_and_store(ticker: str, start: str = None, end: str = None):
    if start is None:
        start = (datetime.today() - timedelta(days=5*365)).strftime("%Y-%m-%d")
    if end is None:
        end = datetime.today().strftime("%Y-%m-%d")

    print(f"Fetching {ticker} from {start} to {end}...")

    stock = yf.Ticker(ticker)
    info = stock.info
    name = info.get("longName") or info.get("shortName") or ticker
    market = "NSE" if ticker.endswith(".NS") else "NYSE" if ticker.endswith(".NYSE") else "US"

    df = stock.history(start=start, end=end)

    if df.empty:
        print(f"No data found for {ticker}. Check the ticker symbol.")
        return

    df.reset_index(inplace=True)
    df["Date"] = df["Date"].dt.date

    conn = get_connection()
    cur = conn.cursor()

    # Insert stock if it doesn't exist
    cur.execute("""
        INSERT INTO stocks (ticker, name, market)
        VALUES (%s, %s, %s)
        ON CONFLICT (ticker) DO NOTHING;
    """, (ticker, name, market))

    # Insert price data
    inserted = 0
    skipped = 0
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

    print(f"Done. {inserted} rows inserted, {skipped} skipped for {ticker}.")