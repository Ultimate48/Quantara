import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import psycopg2
from config import DB_CONFIG

def get_connection():
    return psycopg2.connect(**DB_CONFIG)

def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS stocks (
            id SERIAL PRIMARY KEY,
            ticker VARCHAR(20) UNIQUE NOT NULL,
            name VARCHAR(100),
            market VARCHAR(10),
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS price_data (
            id SERIAL PRIMARY KEY,
            ticker VARCHAR(20) NOT NULL,
            date DATE NOT NULL,
            open NUMERIC,
            high NUMERIC,
            low NUMERIC,
            close NUMERIC,
            volume BIGINT,
            UNIQUE(ticker, date),
            FOREIGN KEY (ticker) REFERENCES stocks(ticker)
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS backtest_runs (
            id SERIAL PRIMARY KEY,
            ticker VARCHAR(20),
            strategy VARCHAR(50),
            start_date DATE,
            end_date DATE,
            initial_capital NUMERIC,
            final_value NUMERIC,
            total_return NUMERIC,
            sharpe_ratio NUMERIC,
            max_drawdown NUMERIC,
            win_rate NUMERIC,
            total_trades INTEGER,
            run_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    conn.commit()
    cur.close()
    conn.close()
    print("Database initialized successfully.")

if __name__ == "__main__":
    init_db()