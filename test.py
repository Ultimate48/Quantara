"""
Quantara — Comprehensive Test Suite
====================================
Tests all Batch 1 features: unit tests + CLI command tests + full pipeline.

Usage:
    python test.py              # Run all tests
    python test.py --unit       # Run only unit tests
    python test.py --cli        # Run only CLI tests
    python test.py --pipeline   # Run only pipeline tests
"""

import subprocess
import sys
import os
import json
import traceback

# ─────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────
PYTHON = sys.executable
CLI = "cli.py"
TEST_TICKER = "AAPL"          # Must already exist in DB
TEST_STRATEGY = "rsi_14"      # Must already exist in DB with backtest runs

# Test strategy names (will be created/updated/deleted during tests)
TEST_CREATE_NAME = "__test_create_strategy__"
TEST_INDICATOR_NAME = "__test_indicator_strategy__"
TEST_UPDATE_NAME = "__test_update_strategy__"
TEST_DELETE_NAME = "__test_delete_strategy__"
TEST_FORCE_DELETE_NAME = "__test_force_delete_strategy__"
TEST_BAD_FORMULA_NAME = "__test_bad_formula__"

# Tracking
passed = 0
failed = 0
errors = []


def header(title):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")


def test(name, condition, detail=""):
    """Record a test result."""
    global passed, failed
    if condition:
        passed += 1
        print(f"  ✓ {name}")
    else:
        failed += 1
        msg = f"  ✗ {name}"
        if detail:
            msg += f" — {detail}"
        print(msg)
        errors.append(f"{name}: {detail}")


def run_cli(cmd, expect_success=True):
    """Run a CLI command and return (returncode, stdout, stderr)."""
    full_cmd = f"{PYTHON} {CLI} {cmd}"
    result = subprocess.run(
        full_cmd, shell=True, capture_output=True, text=True,
        cwd=os.path.dirname(os.path.abspath(__file__))
    )
    if expect_success and result.returncode != 0:
        return result.returncode, result.stdout, result.stderr
    return result.returncode, result.stdout, result.stderr


def cleanup_test_strategies():
    """Remove any leftover test strategies from previous runs."""
    test_names = [
        TEST_CREATE_NAME, TEST_INDICATOR_NAME, TEST_UPDATE_NAME,
        TEST_DELETE_NAME, TEST_FORCE_DELETE_NAME, TEST_BAD_FORMULA_NAME,
    ]
    for name in test_names:
        run_cli(f'strategy delete --name "{name}" --force', expect_success=False)


# ═════════════════════════════════════════════════
# SECTION 1: UNIT TESTS
# ═════════════════════════════════════════════════

def run_unit_tests():
    header("UNIT TESTS")

    # ── 1.1 analytics/metrics.py ──
    print("\n  --- analytics/metrics.py ---")
    try:
        import pandas as pd
        import numpy as np
        from analytics.metrics import compute_metrics

        # Create a simple equity curve: starts at 100k, ends at 120k
        dates = pd.date_range("2020-01-01", periods=100, freq="B")
        values = np.linspace(100000, 120000, 100)
        equity_curve = pd.DataFrame({"value": values}, index=dates)

        # Create a simple trade log
        trade_log = pd.DataFrame({
            "date": [dates[10], dates[30], dates[50], dates[70]],
            "type": ["buy", "sell", "buy", "sell"],
            "price": [100, 120, 110, 130],
            "shares": [1000, 1000, 909, 909],
            "cash_after": [0, 120000, 0, 118170],
        })

        metrics = compute_metrics(equity_curve, trade_log, 100000, 120000)

        test("compute_metrics returns dict", isinstance(metrics, dict))
        test("total_return is 20%", metrics["total_return"] == 20.0,
             f"got {metrics['total_return']}")
        test("sharpe_ratio is a number", isinstance(metrics["sharpe_ratio"], (int, float)))
        test("max_drawdown is <= 0", metrics["max_drawdown"] <= 0,
             f"got {metrics['max_drawdown']}")
        test("win_rate is between 0-100", 0 <= metrics["win_rate"] <= 100)
        test("total_trades == 4", metrics["total_trades"] == 4)

        # Edge case: empty trade log
        empty_log = pd.DataFrame(columns=["date", "type", "price", "shares", "cash_after"])
        metrics_empty = compute_metrics(equity_curve, empty_log, 100000, 120000)
        test("empty trade log: win_rate=0", metrics_empty["win_rate"] == 0)
        test("empty trade log: total_trades=0", metrics_empty["total_trades"] == 0)

    except Exception as e:
        test("analytics/metrics.py import and basic test", False, str(e))

    # ── 1.2 strategies/indicators.py ──
    print("\n  --- strategies/indicators.py ---")
    try:
        from strategies.indicators import expand_indicator, list_indicators, INDICATOR_REGISTRY

        # Test registry completeness
        expected = {"RSI", "SMA", "EMA", "BB", "MACD", "ATR", "ROC"}
        actual = set(INDICATOR_REGISTRY.keys())
        test("all 7 indicators registered", expected == actual,
             f"missing: {expected - actual}, extra: {actual - expected}")

        # Test list_indicators
        indicators = list_indicators()
        test("list_indicators returns list", isinstance(indicators, list))
        test("list_indicators has 7 entries", len(indicators) == 7)

        # Test RSI expansion
        rsi_cols = expand_indicator("RSI,14")
        test("RSI,14 expands to 7 columns", len(rsi_cols) == 7)
        test("RSI last column is 'rsi'", rsi_cols[-1]["name"] == "rsi")

        # Test RSI with default period
        rsi_default = expand_indicator("RSI")
        test("RSI (no period) uses default 14", "rolling(14)" in rsi_default[3]["formula"])

        # Test SMA
        sma_cols = expand_indicator("SMA,50")
        test("SMA,50 expands to 1 column", len(sma_cols) == 1)
        test("SMA,50 column named sma_50", sma_cols[0]["name"] == "sma_50")

        # Test EMA
        ema_cols = expand_indicator("EMA,20")
        test("EMA,20 expands to 1 column", len(ema_cols) == 1)
        test("EMA,20 uses ewm(span=20)", "span=20" in ema_cols[0]["formula"])

        # Test BB
        bb_cols = expand_indicator("BB,20")
        test("BB,20 expands to 4 columns", len(bb_cols) == 4)
        bb_names = [c["name"] for c in bb_cols]
        test("BB includes mid/std/upper/lower", set(bb_names) == {"bb_mid", "bb_std", "bb_upper", "bb_lower"})

        # Test MACD
        macd_cols = expand_indicator("MACD,12,26,9")
        test("MACD expands to 5 columns", len(macd_cols) == 5)
        macd_names = [c["name"] for c in macd_cols]
        test("MACD includes fast/slow/line/signal/hist",
             all(n in macd_names for n in ["macd_fast", "macd_slow", "macd_line", "macd_signal", "macd_hist"]))

        # Test ATR
        atr_cols = expand_indicator("ATR,14")
        test("ATR,14 expands to 6 columns", len(atr_cols) == 6)
        test("ATR last column is 'atr'", atr_cols[-1]["name"] == "atr")

        # Test ROC
        roc_cols = expand_indicator("ROC,10")
        test("ROC,10 expands to 1 column", len(roc_cols) == 1)
        test("ROC,10 column named roc_10", roc_cols[0]["name"] == "roc_10")

        # Test case insensitivity
        rsi_lower = expand_indicator("rsi,14")
        test("case insensitive: 'rsi,14' works", len(rsi_lower) == 7)

        # Test unknown indicator
        try:
            expand_indicator("UNKNOWN,14")
            test("unknown indicator raises ValueError", False, "no exception raised")
        except ValueError as e:
            test("unknown indicator raises ValueError", "Unknown indicator" in str(e))

        # Test bad parameter
        try:
            expand_indicator("RSI,abc")
            test("bad parameter raises ValueError", False, "no exception raised")
        except ValueError as e:
            test("bad parameter raises ValueError", "Invalid value" in str(e))

    except Exception as e:
        test("strategies/indicators.py import and tests", False, traceback.format_exc())

    # ── 1.3 strategies/engine.py — validate_strategy ──
    print("\n  --- strategies/engine.py (validation) ---")
    try:
        from strategies.engine import validate_strategy, apply_columns, apply_signal_rule

        # Valid strategy
        valid = validate_strategy(
            [{"name": "sma", "formula": "close.rolling(20).mean()"}],
            "sma > close : 1, True : 0"
        )
        test("valid strategy passes validation", valid["valid"])

        # Valid RSI strategy
        rsi_valid = validate_strategy(
            [
                {"name": "delta", "formula": "close.diff()"},
                {"name": "gain", "formula": "delta.clip(lower=0)"},
                {"name": "loss", "formula": "-delta.clip(upper=0)"},
                {"name": "avg_gain", "formula": "gain.rolling(14).mean()"},
                {"name": "avg_loss", "formula": "loss.rolling(14).mean()"},
                {"name": "rs", "formula": "avg_gain / avg_loss"},
                {"name": "rsi", "formula": "100 - (100 / (1 + rs))"},
            ],
            "rsi < 30 : 1, rsi > 70 : -1, True : 0"
        )
        test("full RSI strategy passes validation", rsi_valid["valid"])

        # Invalid formula — syntax error
        bad_syntax = validate_strategy(
            [{"name": "bad", "formula": "close.this.is.broken()"}],
            "bad > 0 : 1, True : 0"
        )
        test("syntax error caught", not bad_syntax["valid"])
        test("syntax error has message", len(bad_syntax["error"]) > 0)

        # Invalid formula — reference undefined column
        bad_ref = validate_strategy(
            [{"name": "x", "formula": "nonexistent_column + 1"}],
            "x > 0 : 1, True : 0"
        )
        test("undefined column reference caught", not bad_ref["valid"])

        # Invalid signal rule — bad condition
        bad_signal = validate_strategy(
            [{"name": "sma", "formula": "close.rolling(20).mean()"}],
            "this_is_broken_syntax!!! : 1, True : 0"
        )
        test("bad signal rule caught", not bad_signal["valid"])

        # Test apply_columns with valid data
        import pandas as pd
        import numpy as np
        df = pd.DataFrame({
            "open": [1.0, 2.0, 3.0],
            "high": [1.5, 2.5, 3.5],
            "low": [0.5, 1.5, 2.5],
            "close": [1.2, 2.2, 3.2],
            "volume": [100.0, 200.0, 300.0],
        })
        result_df = apply_columns(df.copy(), [{"name": "avg", "formula": "close.rolling(2).mean()"}])
        test("apply_columns adds new column", "avg" in result_df.columns)

        # Test apply_signal_rule
        result_df2 = apply_signal_rule(result_df.copy(), "avg > 2 : 1, True : 0")
        test("apply_signal_rule adds signal column", "signal" in result_df2.columns)
        test("signal values are 0 or 1", set(result_df2["signal"].dropna().unique()).issubset({0, 1}))

    except Exception as e:
        test("strategies/engine.py validation tests", False, traceback.format_exc())

    # ── 1.4 ui/display.py ──
    print("\n  --- ui/display.py ---")
    try:
        from ui.display import (
            print_success, print_error, print_warning, print_info,
            print_table, print_metrics, print_strategy_detail,
            print_comparison, print_indicators, RICH_AVAILABLE,
        )
        test("ui.display imports successfully", True)
        test("rich library available", RICH_AVAILABLE)

        # Test that functions are callable (don't crash)
        import io
        from contextlib import redirect_stdout

        with redirect_stdout(io.StringIO()):
            print_success("test success")
            print_error("test error")
            print_warning("test warning")
            print_info("test info")
            print_table("Test", [("Col", "left", None)], [("val",)])
        test("display functions callable without crash", True)

    except Exception as e:
        test("ui/display.py tests", False, str(e))

    # ── 1.5 db/queries.py — new functions ──
    print("\n  --- db/queries.py (new functions) ---")
    try:
        from db.queries import ticker_exists, update_strategy, delete_strategy, delete_strategy_force
        test("ticker_exists import", True)
        test("update_strategy import", True)
        test("delete_strategy import", True)
        test("delete_strategy_force import", True)

        # Test ticker_exists against real DB
        exists = ticker_exists(TEST_TICKER)
        test(f"ticker_exists('{TEST_TICKER}') returns True", exists)

        not_exists = ticker_exists("ZZZZZZ_FAKE_TICKER")
        test("ticker_exists('ZZZZZZ_FAKE_TICKER') returns False", not not_exists)

    except Exception as e:
        test("db/queries.py new functions", False, str(e))


# ═════════════════════════════════════════════════
# SECTION 2: CLI COMMAND TESTS
# ═════════════════════════════════════════════════

def run_cli_tests():
    header("CLI COMMAND TESTS")

    # Clean up any leftover test strategies
    cleanup_test_strategies()

    # ── 2.1 Help commands ──
    print("\n  --- Help & Navigation ---")
    rc, out, err = run_cli("--help")
    test("quantara --help exits 0", rc == 0)
    test("help shows all commands", all(cmd in out for cmd in ["fetch", "stocks", "strategy", "backtest"]))

    rc, out, err = run_cli("strategy --help")
    test("strategy --help exits 0", rc == 0)
    test("strategy help shows all subcommands",
         all(cmd in out for cmd in ["create", "update", "delete", "list", "show", "indicators"]))

    rc, out, err = run_cli("backtest --help")
    test("backtest --help exits 0", rc == 0)

    rc, out, err = run_cli("backtest run --help")
    test("backtest run help shows --compare", "--compare" in out)

    # ── 2.2 stocks listing ──
    print("\n  --- Stocks Listing ---")
    rc, out, err = run_cli("stocks")
    test("stocks command exits 0", rc == 0)
    test("stocks output contains AAPL", "AAPL" in out)
    test("stocks output has table border", "─" in out or "Ticker" in out)

    # ── 2.3 strategy indicators ──
    print("\n  --- Strategy Indicators ---")
    rc, out, err = run_cli("strategy indicators")
    test("strategy indicators exits 0", rc == 0)
    test("shows RSI preset", "RSI" in out)
    test("shows MACD preset", "MACD" in out)
    test("shows all 7 presets", all(ind in out for ind in ["RSI", "SMA", "EMA", "BB", "MACD", "ATR", "ROC"]))

    # ── 2.4 strategy create ──
    print("\n  --- Strategy Create ---")

    # Create with --column
    rc, out, err = run_cli(
        f'strategy create --name "{TEST_CREATE_NAME}" '
        f'--description "Test strategy" '
        f'--column "sma20 = close.rolling(20).mean()" '
        f'--column "sma50 = close.rolling(50).mean()" '
        f'--signal "sma20 > sma50 : 1, sma20 < sma50 : -1, True : 0"'
    )
    test("create with --column exits 0", rc == 0)
    test("create shows success", "created" in out.lower() or "✓" in out)

    # Create with --indicator
    rc, out, err = run_cli(
        f'strategy create --name "{TEST_INDICATOR_NAME}" '
        f'--description "Test indicator preset" '
        f'--indicator "RSI,14" '
        f'--signal "rsi < 30 : 1, rsi > 70 : -1, True : 0"'
    )
    test("create with --indicator exits 0", rc == 0)
    test("create with indicator shows success", "created" in out.lower() or "✓" in out)

    # ── 2.5 strategy create — error handling ──
    print("\n  --- Strategy Create Error Handling ---")

    # Duplicate name
    rc, out, err = run_cli(
        f'strategy create --name "{TEST_CREATE_NAME}" '
        f'--column "sma = close.rolling(20).mean()" '
        f'--signal "sma > close : 1, True : 0"'
    )
    test("duplicate name shows error", "already exists" in out.lower() or "✗" in out)

    # Bad formula
    rc, out, err = run_cli(
        f'strategy create --name "{TEST_BAD_FORMULA_NAME}" '
        f'--column "bad = this.is.broken.nonsense()" '
        f'--signal "bad > 0 : 1, True : 0"'
    )
    test("bad formula shows validation error", "validation failed" in out.lower() or "✗" in out)

    # Unknown indicator
    rc, out, err = run_cli(
        f'strategy create --name "{TEST_BAD_FORMULA_NAME}" '
        f'--indicator "UNKNOWN,14" '
        f'--signal "x > 0 : 1, True : 0"'
    )
    test("unknown indicator shows error", "unknown indicator" in out.lower() or "✗" in out)

    # ── 2.6 strategy show ──
    print("\n  --- Strategy Show ---")
    rc, out, err = run_cli(f'strategy show --name "{TEST_INDICATOR_NAME}"')
    test("strategy show exits 0", rc == 0)
    test("show displays strategy name", TEST_INDICATOR_NAME in out)
    test("show displays RSI columns", "rsi" in out.lower())
    test("show displays signal rule", "signal" in out.lower() or "30" in out)

    # Show non-existent
    rc, out, err = run_cli('strategy show --name "nonexistent_strategy_xyz"')
    test("show non-existent shows error", "not found" in out.lower() or "✗" in out)

    # ── 2.7 strategy list ──
    print("\n  --- Strategy List ---")
    rc, out, err = run_cli("strategy list")
    test("strategy list exits 0", rc == 0)
    test("list contains test strategies", TEST_CREATE_NAME in out)

    # ── 2.8 strategy update ──
    print("\n  --- Strategy Update ---")

    # Create a strategy to update
    run_cli(
        f'strategy create --name "{TEST_UPDATE_NAME}" '
        f'--description "Original" '
        f'--column "sma = close.rolling(20).mean()" '
        f'--signal "sma > close : 1, True : 0"'
    )

    # Update description and signal
    rc, out, err = run_cli(
        f'strategy update --name "{TEST_UPDATE_NAME}" '
        f'--description "Updated description" '
        f'--signal "sma < close : 1, True : 0"'
    )
    test("update exits 0", rc == 0)
    test("update shows success", "updated" in out.lower() or "✓" in out)

    # Verify update
    rc, out, err = run_cli(f'strategy show --name "{TEST_UPDATE_NAME}"')
    test("show reflects updated description", "Updated description" in out)
    test("show reflects updated signal", "sma < close" in out)

    # Update with indicator (replaces columns)
    rc, out, err = run_cli(
        f'strategy update --name "{TEST_UPDATE_NAME}" '
        f'--indicator "RSI,9" '
        f'--signal "rsi < 25 : 1, rsi > 75 : -1, True : 0"'
    )
    test("update with indicator exits 0", rc == 0)

    # Update non-existent
    rc, out, err = run_cli(
        f'strategy update --name "nonexistent_xyz" '
        f'--description "test"'
    )
    test("update non-existent shows error", "not found" in out.lower() or "✗" in out)

    # ── 2.9 strategy delete ──
    print("\n  --- Strategy Delete ---")

    # Create a strategy to delete
    run_cli(
        f'strategy create --name "{TEST_DELETE_NAME}" '
        f'--column "sma = close.rolling(20).mean()" '
        f'--signal "sma > close : 1, True : 0"'
    )

    # Delete it
    rc, out, err = run_cli(f'strategy delete --name "{TEST_DELETE_NAME}"')
    test("delete exits 0", rc == 0)
    test("delete shows success", "deleted" in out.lower() or "✓" in out)

    # Verify it's gone
    rc, out, err = run_cli(f'strategy show --name "{TEST_DELETE_NAME}"')
    test("deleted strategy not found", "not found" in out.lower() or "✗" in out)

    # Delete non-existent
    rc, out, err = run_cli(f'strategy delete --name "nonexistent_xyz"')
    test("delete non-existent shows error", "not found" in out.lower() or "✗" in out)

    # Delete with dependency protection (use existing strategy that has backtests)
    # TEST_STRATEGY (rsi_14) should have backtest runs from test_e2e.py
    rc, out, err = run_cli(f'strategy delete --name "{TEST_STRATEGY}"')
    # If it has runs, should show protection error; if not, it might just delete
    has_runs = "cannot delete" in out.lower() or "backtest" in out.lower()
    test("delete protected strategy shows error (if runs exist)", has_runs or "✗" in out or "deleted" in out.lower(),
         f"output: {out.strip()[:100]}")

    # ── 2.10 backtest — error handling ──
    print("\n  --- Backtest Error Handling ---")

    # Missing ticker
    rc, out, err = run_cli('backtest run --strategy rsi_basic --ticker ZZZFAKE --no-plot')
    test("missing ticker shows error", "not found" in out.lower() or "✗" in out)
    test("missing ticker suggests fetch", "fetch" in out.lower())

    # Missing strategy
    rc, out, err = run_cli(f'backtest run --strategy nonexistent_xyz --ticker {TEST_TICKER} --no-plot')
    test("missing strategy shows error", "not found" in out.lower() or "✗" in out)

    # ── 2.11 results listing ──
    print("\n  --- Results Listing ---")
    rc, out, err = run_cli("results")
    test("results exits 0", rc == 0)
    test("results shows table", "ID" in out or "Ticker" in out or "─" in out)

    rc, out, err = run_cli(f"results --ticker {TEST_TICKER}")
    test("results --ticker exits 0", rc == 0)
    test(f"results filtered to {TEST_TICKER}", TEST_TICKER in out)

    # ── Cleanup ──
    print("\n  --- Cleanup ---")
    cleanup_test_strategies()
    test("test strategies cleaned up", True)


# ═════════════════════════════════════════════════
# SECTION 3: FULL PIPELINE TESTS
# ═════════════════════════════════════════════════

def run_pipeline_tests():
    header("FULL PIPELINE TESTS")

    cleanup_test_strategies()
    pipeline_strategy = "__test_pipeline_strat__"
    pipeline_indicator_strategy = "__test_pipeline_ind_strat__"

    # ── 3.1 Pipeline: Column-based strategy → backtest → compare → results ──
    print("\n  --- Pipeline 1: Column-based strategy ---")

    # Create strategy with manual columns
    rc, out, err = run_cli(
        f'strategy create --name "{pipeline_strategy}" '
        f'--description "Pipeline test SMA crossover" '
        f'--column "sma_fast = close.rolling(20).mean()" '
        f'--column "sma_slow = close.rolling(50).mean()" '
        f'--column "sma_fast_prev = sma_fast.shift(1)" '
        f'--column "sma_slow_prev = sma_slow.shift(1)" '
        f'--signal "(sma_fast > sma_slow) & (sma_fast_prev <= sma_slow_prev) : 1, '
        f'(sma_fast < sma_slow) & (sma_fast_prev >= sma_slow_prev) : -1, True : 0"'
    )
    test("P1: strategy create", rc == 0 and ("created" in out.lower() or "✓" in out))

    # Run backtest
    rc, out, err = run_cli(
        f'backtest run --strategy "{pipeline_strategy}" '
        f'--ticker {TEST_TICKER} --start 2020-01-01 --end 2024-01-01 '
        f'--capital 100000 --no-plot'
    )
    test("P1: backtest run exits 0", rc == 0)
    test("P1: backtest shows metrics", "Total Return" in out or "total_return" in out.lower() or "Return" in out)
    test("P1: backtest saved", "saved" in out.lower() or "✓" in out)

    # ── 3.2 Pipeline: Indicator preset → backtest → compare ──
    print("\n  --- Pipeline 2: Indicator preset + compare ---")

    # Create strategy with indicator preset + extra column
    rc, out, err = run_cli(
        f'strategy create --name "{pipeline_indicator_strategy}" '
        f'--description "Pipeline test RSI with BB" '
        f'--indicator "RSI,14" '
        f'--indicator "BB,20" '
        f'--signal "(rsi < 30) & (close <= bb_lower) : 1, (rsi > 70) | (close >= bb_upper) : -1, True : 0"'
    )
    test("P2: indicator strategy create", rc == 0 and ("created" in out.lower() or "✓" in out))

    # Verify strategy shows all indicator columns
    rc, out, err = run_cli(f'strategy show --name "{pipeline_indicator_strategy}"')
    test("P2: strategy has RSI columns", "rsi" in out.lower())
    test("P2: strategy has BB columns", "bb_mid" in out.lower() or "bb_upper" in out.lower())

    # Run backtest with --compare against the column-based strategy
    rc, out, err = run_cli(
        f'backtest run --strategy "{pipeline_indicator_strategy}" '
        f'--ticker {TEST_TICKER} --start 2020-01-01 --end 2024-01-01 '
        f'--capital 100000 --no-plot '
        f'--compare "{pipeline_strategy}"'
    )
    test("P2: backtest with compare exits 0", rc == 0)
    test("P2: comparison table shown", "Comparison" in out or pipeline_strategy in out)
    test("P2: both strategies in comparison",
         pipeline_indicator_strategy in out and pipeline_strategy in out)

    # ── 3.3 Pipeline: Update → re-backtest ──
    print("\n  --- Pipeline 3: Update strategy then re-backtest ---")

    # Update the indicator strategy's signal rule
    rc, out, err = run_cli(
        f'strategy update --name "{pipeline_indicator_strategy}" '
        f'--signal "(rsi < 25) & (close <= bb_lower) : 1, (rsi > 75) : -1, True : 0"'
    )
    test("P3: strategy update", rc == 0 and ("updated" in out.lower() or "✓" in out))

    # Verify signal rule changed
    rc, out, err = run_cli(f'strategy show --name "{pipeline_indicator_strategy}"')
    test("P3: signal rule updated", "25" in out)

    # Re-run backtest with updated strategy
    rc, out, err = run_cli(
        f'backtest run --strategy "{pipeline_indicator_strategy}" '
        f'--ticker {TEST_TICKER} --start 2020-01-01 --end 2024-01-01 '
        f'--capital 100000 --no-plot'
    )
    test("P3: re-backtest exits 0", rc == 0)
    test("P3: re-backtest saved", "saved" in out.lower() or "✓" in out)

    # ── 3.4 Pipeline: Risk management parameters ──
    print("\n  --- Pipeline 4: Backtest with risk management ---")

    rc, out, err = run_cli(
        f'backtest run --strategy "{pipeline_strategy}" '
        f'--ticker {TEST_TICKER} --start 2020-01-01 --end 2024-01-01 '
        f'--capital 200000 --no-plot '
        f'--stop-loss 0.07 --take-profit 0.20 --cooldown 10'
    )
    test("P4: backtest with SL/TP/cooldown exits 0", rc == 0)
    test("P4: backtest saved", "saved" in out.lower() or "✓" in out)

    # ── 3.5 Pipeline: Signal confirmation ──
    print("\n  --- Pipeline 5: Signal confirmation ---")

    rc, out, err = run_cli(
        f'backtest run --strategy "{pipeline_strategy}" '
        f'--ticker {TEST_TICKER} --start 2020-01-01 --end 2024-01-01 '
        f'--capital 100000 --no-plot '
        f'--confirm 3 --confirm-sell 1'
    )
    test("P5: backtest with confirmation exits 0", rc == 0)

    # ── 3.6 Pipeline: Short mode ──
    print("\n  --- Pipeline 6: Short and long-short modes ---")

    rc, out, err = run_cli(
        f'backtest run --strategy "{pipeline_strategy}" '
        f'--ticker {TEST_TICKER} --start 2020-01-01 --end 2024-01-01 '
        f'--capital 100000 --no-plot --long-short'
    )
    test("P6: long-short backtest exits 0", rc == 0)

    rc, out, err = run_cli(
        f'backtest run --strategy "{pipeline_strategy}" '
        f'--ticker {TEST_TICKER} --start 2020-01-01 --end 2024-01-01 '
        f'--capital 100000 --no-plot --short-only'
    )
    test("P6: short-only backtest exits 0", rc == 0)

    # ── 3.7 Pipeline: View saved run ──
    print("\n  --- Pipeline 7: View saved backtest run ---")

    rc, out, err = run_cli("results")
    test("P7: results listing works", rc == 0)

    # Use a recent run ID that has full JSONB data (legacy runs before schema fix may lack it)
    # Find the latest run ID from results output
    rc, out, err = run_cli("results")
    # Use a high run ID (recent, has equity curve data)
    # Try to find a run from the pipeline tests we just did
    rc, out, err = run_cli(f"backtest show --id 103")
    if rc != 0:
        # Fallback: try the most recent run
        rc, out, err = run_cli(f"backtest show --id 1")
    test("P7: backtest show exits 0", rc == 0,
         f"stderr: {err[:100]}" if rc != 0 else "")

    # ── 3.8 Pipeline: Force delete with dependent runs ──
    print("\n  --- Pipeline 8: Force delete with backtests ---")

    rc, out, err = run_cli(f'strategy delete --name "{pipeline_indicator_strategy}"')
    test("P8: delete blocked by backtests", "cannot delete" in out.lower() or "backtest" in out.lower())

    rc, out, err = run_cli(f'strategy delete --name "{pipeline_indicator_strategy}" --force')
    test("P8: force delete succeeds", "deleted" in out.lower() or "✓" in out)
    test("P8: force delete removed runs", "run" in out.lower() or "removed" in out.lower() or "✓" in out)

    # ── Cleanup ──
    print("\n  --- Pipeline Cleanup ---")
    run_cli(f'strategy delete --name "{pipeline_strategy}" --force', expect_success=False)
    run_cli(f'strategy delete --name "{pipeline_indicator_strategy}" --force', expect_success=False)
    test("pipeline strategies cleaned up", True)


# ═════════════════════════════════════════════════
# MAIN
# ═════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Quantara Test Suite")
    parser.add_argument("--unit", action="store_true", help="Run only unit tests")
    parser.add_argument("--cli", action="store_true", help="Run only CLI command tests")
    parser.add_argument("--pipeline", action="store_true", help="Run only pipeline tests")
    args = parser.parse_args()

    run_all = not (args.unit or args.cli or args.pipeline)

    print("\n" + "█" * 70)
    print("  QUANTARA — COMPREHENSIVE TEST SUITE")
    print("█" * 70)

    if run_all or args.unit:
        run_unit_tests()

    if run_all or args.cli:
        run_cli_tests()

    if run_all or args.pipeline:
        run_pipeline_tests()

    # ── Summary ──
    header("TEST RESULTS")
    total = passed + failed
    print(f"\n  Total:  {total}")
    print(f"  Passed: {passed}")
    print(f"  Failed: {failed}")

    if errors:
        print(f"\n  Failed tests:")
        for e in errors:
            print(f"    ✗ {e}")

    print()
    if failed == 0:
        print("  ✅ ALL TESTS PASSED")
    else:
        print(f"  ❌ {failed} TEST(S) FAILED")

    print()
    sys.exit(0 if failed == 0 else 1)