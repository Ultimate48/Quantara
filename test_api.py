import subprocess
import time
import requests
import sys
import os

def test_api():
    print("======================================================================")
    print("  QUANTARA — API INTEGRATION TEST SUITE")
    print("======================================================================")
    
    project_dir = os.path.dirname(os.path.abspath(__file__))
    print("Starting FastAPI server in subprocess...")
    server_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "server.main:app", "--host", "127.0.0.1", "--port", "8000"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        cwd=project_dir
    )
    
    time.sleep(3.0)
    
    if server_process.poll() is not None:
        print("Server failed to start!")
        sys.exit(1)
        
    print("Server started successfully.")
    
    base_url = "http://127.0.0.1:8000/api"
    passed = 0
    failed = 0
    
    def assert_status(response, expected_status=200, test_name=""):
        nonlocal passed, failed
        if response.status_code == expected_status:
            passed += 1
            print(f"  ✓ {test_name} (Status {response.status_code})")
            return True
        else:
            failed += 1
            print(f"  ✗ {test_name} (Expected {expected_status}, got {response.status_code})")
            print("  Response Content:", response.text[:300])
            return False

    try:
        print("\nTesting GET /stocks...")
        r = requests.get(f"{base_url}/stocks")
        if assert_status(r, 200, "GET /stocks"):
            stocks = r.json()
            print(f"    Found {len(stocks)} stocks.")
            
        print("\nTesting GET /indicators...")
        r = requests.get(f"{base_url}/indicators")
        if assert_status(r, 200, "GET /indicators"):
            indicators = r.json()
            print(f"    Found {len(indicators)} indicators.")
            
        print("\nTesting POST /strategies (create)...")
        strategy_data = {
            "name": "__api_test_strategy__",
            "description": "API integration test crossover strategy",
            "columns": [
                {"name": "sma_fast", "formula": "close.rolling(10).mean()"},
                {"name": "sma_slow", "formula": "close.rolling(30).mean()"}
            ],
            "signal_rule": "sma_fast > sma_slow : 1, sma_fast < sma_slow : -1, True : 0"
        }
        requests.delete(f"{base_url}/strategies/__api_test_strategy__?force=true")
        
        r = requests.post(f"{base_url}/strategies", json=strategy_data)
        assert_status(r, 200, "POST /strategies")
        
        print("\nTesting POST /backtest (execute)...")
        backtest_data = {
            "strategy": "__api_test_strategy__",
            "ticker": "AAPL",
            "capital": 100000.0,
            "cooldown": 5,
            "position_size": "fixed:50000",
            "transaction_cost": 0.001,
            "slippage": 0.001
        }
        r = requests.post(f"{base_url}/backtest", json=backtest_data)
        if assert_status(r, 200, "POST /backtest"):
            res = r.json()
            print(f"    Backtest completed. Return: {res.get('total_return')}%, Trades: {res.get('total_trades')}")
            
        print("\nTesting GET /backtests...")
        r = requests.get(f"{base_url}/backtests")
        if assert_status(r, 200, "GET /backtests"):
            runs = r.json()
            print(f"    Found {len(runs)} total runs.")
            
        print("\nTesting DELETE /strategies (cleanup)...")
        r = requests.delete(f"{base_url}/strategies/__api_test_strategy__?force=true")
        assert_status(r, 200, "DELETE /strategies (force)")
        
    except Exception as e:
        print("An error occurred during API tests:", e)
        failed += 1
        
    finally:
        print("\nShutting down FastAPI server...")
        server_process.terminate()
        server_process.wait()
        print("Server stopped.")
        
    print("\n======================================================================")
    print("  API TEST RESULTS")
    print("======================================================================")
    print(f"  Passed: {passed}")
    print(f"  Failed: {failed}")
    
    if failed == 0:
        print("\n  ✅ ALL API ENDPOINTS VERIFIED & FUNCTIONAL\n")
        sys.exit(0)
    else:
        print("\n  ❌ SOME API ENDPOINTS FAILED\n")
        sys.exit(1)

if __name__ == "__main__":
    test_api()
