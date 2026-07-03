"""
Quantara Startup Script
Launches both the FastAPI backend and React frontend in parallel.
Usage: python start.py
"""

import subprocess
import sys
import os
import signal
import time

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(ROOT_DIR, "frontend")
VENV_PYTHON = os.path.join(ROOT_DIR, "venv", "Scripts", "python.exe")
VENV_UVICORN = os.path.join(ROOT_DIR, "venv", "Scripts", "uvicorn.exe")

processes = []


def cleanup(signum=None, frame=None):
    """Terminate all child processes on exit."""
    print("\n🛑 Shutting down Quantara...")
    for name, proc in processes:
        if proc.poll() is None:
            print(f"   Stopping {name} (PID {proc.pid})...")
            proc.terminate()
    # Give processes a moment to terminate gracefully
    for name, proc in processes:
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            print(f"   Force killing {name}...")
            proc.kill()
    print("✅ Quantara stopped.")
    sys.exit(0)


def main():
    # Register signal handlers for clean shutdown
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    print("=" * 50)
    print("  🚀 Quantara — Starting Up")
    print("=" * 50)

    # --- Start FastAPI Backend ---
    print("\n📡 Starting FastAPI backend on http://127.0.0.1:8000 ...")
    backend = subprocess.Popen(
        [VENV_UVICORN, "server.main:app", "--reload", "--port", "8000"],
        cwd=ROOT_DIR,
    )
    processes.append(("Backend (uvicorn)", backend))

    # Brief pause to let backend initialize before frontend proxy connects
    time.sleep(2)

    # --- Start React Frontend ---
    print("🌐 Starting React frontend on http://localhost:5173 ...")
    frontend = subprocess.Popen(
        ["npm", "run", "dev"],
        cwd=FRONTEND_DIR,
        shell=True,
    )
    processes.append(("Frontend (vite)", frontend))

    print("\n" + "=" * 50)
    print("  ✅ Quantara is running!")
    print("  📊 Dashboard:  http://localhost:5173")
    print("  📡 API Docs:   http://127.0.0.1:8000/docs")
    print("  Press Ctrl+C to stop everything.")
    print("=" * 50 + "\n")

    # Wait for either process to exit
    while True:
        for name, proc in processes:
            retcode = proc.poll()
            if retcode is not None:
                print(f"\n⚠️  {name} exited with code {retcode}")
                cleanup()
        time.sleep(1)


if __name__ == "__main__":
    main()
