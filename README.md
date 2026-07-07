# 📊 Quantara — Algorithmic Trading Research & Backtesting Platform

Quantara is a professional-grade, end-to-end quantitative trading research, strategy development, and backtesting platform. It enables traders and researchers to define complex technical strategies dynamically, perform historical backtesting with realistic execution constraints, analyze results with advanced statistical metrics, and visualize performance in an interactive, glassmorphic React dashboard.

---

## 🏗 System Architecture

```mermaid
graph TD
    subgraph Frontend [React SPA (Vite)]
        UI[Interactive Dashboard & Recharts]
        Lab[Strategy Lab: Node Editor, Code, Templates]
    end

    subgraph Backend [FastAPI Server]
        API[REST Endpoints /api/*]
        AST[asteval Formula Evaluator]
    end

    subgraph Database [PostgreSQL]
        DB[(Price Data & Strategy Store)]
    end

    subgraph Core [Python Backtesting Engine]
        Engine[Backtest Sim / Slippage & Costs]
        Metrics[Analytics: Sharpe, Max DD, Win Rate]
        Data[Yahoo Finance Fetcher]
        CLI[Command-Line Controller]
    end

    UI <-->|HTTP / REST| API
    Lab <-->|HTTP / REST| API
    API <--> DB
    Engine <--> DB
    Data --> DB
    CLI --> Engine
    API --> Engine
    API --> AST
```

---

## 🛠 Tech Stack

* **Backend**: Python 3.10+, FastAPI, `asteval` (for safe mathematical formula evaluation), `yfinance` (historical data).
* **Database**: PostgreSQL (storage for stock ticker metadata, OHLCV pricing, strategy definitions, and backtest run logs) using raw `psycopg2`.
* **Frontend**: React (built with Vite), Recharts (equity curves and drawdown charts), and Vanilla CSS (custom glassmorphic theme).

---

## 📋 Prerequisites

Before setting up Quantara, make sure you have the following installed on your system:
1. **Python 3.10+** (Verify with `python --version`)
2. **Node.js v18+ & npm** (Verify with `node -v` and `npm -v`)
3. **PostgreSQL** database instance running locally or remotely.

---

## 🚀 End-to-End Installation & Setup

Follow these steps to set up and run the complete project on your own machine.

### 1. Configure the Environment Variables
Create a file named `.env` in the root directory of the project (next to `start.py` and `requirements.txt`). Add your PostgreSQL database connection details:

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=quantara
DB_USER=postgres
DB_PASSWORD="your_postgres_password"
```

> [!NOTE]
> Make sure to create the database inside PostgreSQL before running the database initializer:
> ```sql
> CREATE DATABASE quantara;
> ```

---

### 2. Set Up the Python Virtual Environment & Backend Dependencies

1. Navigate to the root directory of the project in your terminal.
2. Create a virtual environment named `venv`:
   ```bash
   python -m venv venv
   ```
3. Activate the virtual environment:
   * **Windows (Command Prompt):**
     ```cmd
     venv\Scripts\activate.bat
     ```
   * **Windows (PowerShell):**
     ```powershell
     venv\Scripts\Activate.ps1
     ```
   * **macOS / Linux:**
     ```bash
     source venv/bin/activate
     ```
4. Install all python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

---

### 3. Initialize the Database
With your virtual environment active and your PostgreSQL service running, execute the database initialization script to create the required tables:

```bash
python db/init.py
```
*This creates the `stocks`, `price_data`, `strategies`, and `backtest_runs` tables in your PostgreSQL database.*

---

### 4. Fetch Stock Pricing Data
Populate the database with historical stock prices from Yahoo Finance using the CLI. You can fetch daily (`1d`) or intraday (`1h`, `15m`, etc.) data:

```bash
# Fetch 5 years of daily data for Apple (AAPL)
python cli.py fetch AAPL

# Fetch NSE stock data with explicit date ranges
python cli.py fetch RELIANCE.NS --start 2023-01-01 --end 2026-01-01

# Fetch US tech stock data
python cli.py fetch MSFT --start 2020-01-01
```

---

### 5. Set Up the Frontend React App
Navigate to the `frontend` folder, install the packages, and prepare the project:

```bash
cd frontend
npm install
cd ..
```

---

## ⚡ Running the Application

You can launch both the FastAPI backend and React frontend concurrently using the project's parallel startup script, or run them manually in separate terminal windows.

### Option A: Parallel Startup Script (Recommended)
Run the startup script in the root directory:
```bash
python start.py
```
This launches:
* **FastAPI Backend** on [http://127.0.0.1:8000](http://127.0.0.1:8000)
* **Vite React Frontend** on [http://localhost:5173](http://localhost:5173)

### Option B: Manual Startup

1. **Terminal 1: Start FastAPI Backend**
   ```bash
   # Make sure virtual environment is active
   uvicorn server.main:app --reload --port 8000
   ```
2. **Terminal 2: Start Vite Dev Server**
   ```bash
   cd frontend
   npm run dev
   ```

---

## 📊 Platform Usage Guide

### 1. Managing Strategies via CLI
Quantara uses a dynamic strategy definition format where you can define custom columns using pandas-compatible formula strings, and signal rules matching those columns.

#### Create a Moving Average Crossover Strategy:
```bash
python cli.py strategy create \
  --name "SMA_Crossover" \
  --description "10-day and 30-day Simple Moving Average crossover" \
  --column "sma_fast = close.rolling(10).mean()" \
  --column "sma_slow = close.rolling(30).mean()" \
  --signal "sma_fast > sma_slow : 1, sma_fast < sma_slow : -1, True : 0"
```

#### Create an RSI Mean Reversion Strategy (Using Shorthand Indicators):
```bash
python cli.py strategy create \
  --name "RSI_Mean_Reversion" \
  --description "RSI oversold/overbought entry and exit" \
  --indicator "RSI,14" \
  --signal "rsi < 30 : 1, rsi > 70 : -1, True : 0"
```
*Note: The `--indicator RSI,14` option automatically generates the column definitions for `rsi_delta`, `rsi_gain`, `rsi_loss`, `rsi_avg_gain`, `rsi_avg_loss`, `rsi_rs`, and `rsi`.*

#### List and View Saved Strategies:
```bash
# List all strategies
python cli.py strategy list

# Show a strategy's formulas and rules
python cli.py strategy show --name "SMA_Crossover"
```

---

### 2. Running Backtests via CLI
Simulate trading strategies on historical data with robust execution controls including Stop Loss (SL), Take Profit (TP), Cooldown Days, Signal Confirmations, Position Sizing (Fixed/Percentage/Volatility), Slippage, and Transaction Costs.

#### Run a Standard Backtest:
```bash
python cli.py backtest run \
  --strategy "SMA_Crossover" \
  --ticker "AAPL" \
  --capital 100000 \
  --transaction-cost 0.001 \
  --slippage 0.0005
```

#### Run with Advanced Constraints (Long & Short, Cooldown, Stop Loss):
```bash
python cli.py backtest run \
  --strategy "RSI_Mean_Reversion" \
  --ticker "MSFT" \
  --capital 100000 \
  --long-short \
  --cooldown 3 \
  --stop-loss 0.05 \
  --take-profit 0.15 \
  --position-size "pct:50"
```

#### Run a Walk-Forward Test:
Evaluate how a strategy behaves across rolling train/test split windows:
```bash
python cli.py backtest walk-forward \
  --strategy "SMA_Crossover" \
  --ticker "AAPL" \
  --train-days 252 \
  --test-days 63
```

#### Compare Two Strategies:
```bash
python cli.py backtest run \
  --strategy "SMA_Crossover" \
  --ticker "AAPL" \
  --compare "RSI_Mean_Reversion"
```

---

### 3. Interactive Web Dashboard
Once the app is running, open [http://localhost:5173](http://localhost:5173) in your browser:
* **Strategy Lab**: A 4-mode playground to build strategies.
  * **Templates**: Select from Trend Following, Mean Reversion, Momentum, or Volatility structures.
  * **Visual Builder**: Stack indicators (SMA, EMA, RSI, MACD, Bollinger Bands) and build logic rules.
  * **Node Editor**: Connect logic flow visually.
  * **Code View**: Write custom pandas formulas directly.
* **Backtest Suite**: Select any ticker, pick a strategy, adjust capital, SL/TP levels, slippage, and position sizing, then trigger a backtest instantly.
* **Analytics Center**: Dive into equity curve overlays, drawdown metrics, Sharpe ratio analysis, win rates, and compare performance charts.

---

## 🧪 Testing the Platform

Verify the codebase integrity by running the test suite:

### 1. Run Unit Tests (Core calculations, pandas indicators, and metrics):
```bash
python test.py --unit
```

### 2. Run CLI Tests (Command-Line argument parsing and state persistence):
```bash
python test.py --cli
```

### 3. Run API Integration Tests (Fires up uvicorn server, performs API requests, and shuts down):
```bash
python test_api.py
```

---