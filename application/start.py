#!/usr/bin/env python3
# ###########################################################################
#
#  CLOUDERA APPLIED MACHINE LEARNING PROTOTYPE (AMP)
#  (C) Cloudera, Inc. 2021
#  All rights reserved.
#
#  Applicable Open Source License: Apache 2.0
#
#  NOTE: Cloudera open source products are modular software products
#  made up of hundreds of individual components, each of which was
#  individually copyrighted.  Each Cloudera open source product is a
#  collective work under U.S. Copyright Law. Your license to use the
#  collective work is as provided in your written agreement with
#  Cloudera.  Used apart from the collective work, this file is
#  licensed for your use pursuant to the open source license
#  identified above.
#
#  This code is provided to you pursuant a written agreement with
#  (i) Cloudera, Inc. or (ii) a third-party authorized to distribute
#  this code. If you do not have a written agreement with Cloudera nor
#  with an authorized and properly licensed third party, you do not
#  have any rights to access nor to use this code.
#
#  Absent a written agreement with Cloudera, Inc. ("Cloudera") to the
#  contrary, A) CLOUDERA PROVIDES THIS CODE TO YOU WITHOUT WARRANTIES OF ANY
#  KIND; (B) CLOUDERA DISCLAIMS ANY AND ALL EXPRESS AND IMPLIED
#  WARRANTIES WITH RESPECT TO THIS CODE, INCLUDING BUT NOT LIMITED TO
#  IMPLIED WARRANTIES OF TITLE, NON-INFRINGEMENT, MERCHANTABILITY AND
#  FITNESS FOR A PARTICULAR PURPOSE; (C) CLOUDERA IS NOT LIABLE TO YOU,
#  AND WILL NOT DEFEND, INDEMNIFY, NOR HOLD YOU HARMLESS FOR ANY CLAIMS
#  ARISING FROM OR RELATED TO THE CODE; AND (D)WITH RESPECT TO YOUR EXERCISE
#  OF ANY RIGHTS GRANTED TO YOU FOR THE CODE, CLOUDERA IS NOT LIABLE FOR ANY
#  DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, PUNITIVE OR
#  CONSEQUENTIAL DAMAGES INCLUDING, BUT NOT LIMITED TO, DAMAGES
#  RELATED TO LOST REVENUE, LOST PROFITS, LOSS OF INCOME, LOSS OF
#  BUSINESS ADVANTAGE OR UNAVAILABILITY, OR LOSS OR CORRUPTION OF
#  DATA.
#
# ###########################################################################
"""
Network Data Lakehouse - Combined Server Startup Script
Starts both frontend and backend servers together (local development or single-app CML deployment).

For separate CML applications (recommended for production):
  - start_backend.py - Backend API only (port 8100)
  - start_frontend.py - Frontend UI only (port 8100, requires VITE_API_BASE_URL)
"""

import os
import sys
import signal
import subprocess
import time
import shutil
from pathlib import Path

# Load .env before reading any env vars
try:
    from dotenv import load_dotenv
    try:
        _env_file = Path(__file__).parent.resolve() / ".env"
    except NameError:
        _env_file = Path.cwd() / ".env"
    if _env_file.exists():
        load_dotenv(_env_file, override=False)
except ImportError:
    pass

# Configuration - handle both script execution and Jupyter notebook environments
def _get_project_dir():
    """Get project directory, works in both script and Jupyter environments."""
    try:
        return Path(__file__).parent.resolve()
    except NameError:
        # Running in Jupyter notebook or interactive Python
        cwd = Path(os.getcwd()).resolve()
        # Check if we're in application or if it's a subdirectory
        if cwd.name == 'application':
            return cwd
        app_dir = cwd / 'application'
        if app_dir.exists():
            return app_dir
        return cwd

PROJECT_DIR = _get_project_dir()
REPO_ROOT = PROJECT_DIR.parent
INSTALLER_DIR = REPO_ROOT / "installer"
BACKEND_DIR = PROJECT_DIR / "backend"
PID_FILE = PROJECT_DIR / ".server_pids"
FRONTEND_LOG = PROJECT_DIR / "frontend.log"
BACKEND_LOG = PROJECT_DIR / "backend.log"

# Cloudera environment configuration
# CDSW_READONLY_PORT is used for read-only applications in CML
# CDSW_APP_PORT is used for interactive applications in CML
FRONTEND_PORT = int(os.getenv('CDSW_READONLY_PORT', os.getenv('CDSW_APP_PORT', '8100')))
BACKEND_PORT = int(os.getenv('BACKEND_PORT', '8000'))

# In CML environment, bind to 127.0.0.1; otherwise bind to all interfaces
IS_CML_ENVIRONMENT = bool(os.getenv('CDSW_READONLY_PORT') or os.getenv('CDSW_APP_PORT') or os.getenv('CDSW_PROJECT'))
HOST_BIND = '127.0.0.1' if IS_CML_ENVIRONMENT else '0.0.0.0'

# PostgreSQL paths (user-space installation)
PG_HOME = Path.home() / ".postgres"
PG_DATA = PG_HOME / "data"
PG_BIN = PG_HOME / "bin"
PG_LOG = PG_HOME / "postgres.log"


def get_pids_on_port(port):
    """Best-effort PID lookup for a port, used only to kill stale processes.

    Tries lsof, then fuser, then ss — CML/CAI runtimes often ship none of
    them. Returns [] when no tool is available; callers must NOT use this for
    liveness (use is_running/is_port_listening, which need no external tools).
    """
    import re
    candidates = (
        ["lsof", "-t", "-i", f":{port}"],
        ["fuser", f"{port}/tcp"],
    )
    for cmd in candidates:
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
        except FileNotFoundError:
            continue
        except Exception:
            continue
        if result.returncode == 0 and result.stdout.strip():
            pids = [int(t) for t in result.stdout.replace("\n", " ").split() if t.strip().isdigit()]
            if pids:
                return pids
    # ss fallback: parse "pid=NNN" out of the socket listing
    try:
        result = subprocess.run(
            ["ss", "-lptnH", f"sport = :{port}"], capture_output=True, text=True
        )
        if result.returncode == 0 and result.stdout:
            return [int(p) for p in re.findall(r"pid=(\d+)", result.stdout)]
    except Exception:
        pass
    return []


def is_port_listening(port, host="127.0.0.1"):
    """True if something accepts TCP connections on the port (no lsof needed)."""
    import socket
    try:
        with socket.create_connection((host, port), timeout=1):
            return True
    except OSError:
        return False


def is_running(port):
    """Check if a service is listening on the port.

    Uses a socket probe rather than lsof. CML/CAI runtimes typically don't
    include lsof, which made the old lsof-based check always return False; the
    monitor loop then respawned uvicorn/vite every cycle, and each duplicate
    failed to bind with '[Errno 98] Address already in use' (a restart loop).
    """
    return is_port_listening(port)


def kill_process_on_port(port, name="process"):
    """Kill any process running on the specified port."""
    pids = get_pids_on_port(port)
    for pid in pids:
        try:
            os.kill(pid, signal.SIGTERM)
            print(f"   Stopped existing {name} (PID {pid})")
        except ProcessLookupError:
            pass
        except Exception as e:
            print(f"   Warning: Could not stop PID {pid}: {e}")


def save_pids(backend_pid, frontend_pid):
    """Save PIDs to file for later cleanup."""
    with open(PID_FILE, 'w') as f:
        f.write(f"{backend_pid or ''}\n{frontend_pid or ''}\n")


def find_npm():
    """Find npm executable, checking nvm installation if needed."""
    # First check if npm is in PATH
    npm_path = shutil.which('npm')
    if npm_path:
        return npm_path

    # Check nvm installation
    nvm_dir = Path.home() / ".nvm" / "versions" / "node"
    if nvm_dir.exists():
        for version_dir in sorted(nvm_dir.iterdir(), reverse=True):  # Prefer newer versions
            npm_path = version_dir / "bin" / "npm"
            if npm_path.exists():
                # Also update PATH for subprocess calls
                bin_dir = version_dir / "bin"
                os.environ['PATH'] = f"{bin_dir}:{os.environ.get('PATH', '')}"
                return str(npm_path)

    return 'npm'  # Fallback


def find_pg_ctl():
    """Find pg_ctl executable."""
    # Check user-space installation first
    pg_ctl = PG_BIN / "pg_ctl"
    if pg_ctl.exists():
        return str(pg_ctl)

    # Fall back to PATH
    pg_ctl_path = shutil.which('pg_ctl')
    if pg_ctl_path:
        return pg_ctl_path

    return None


def is_postgres_reachable():
    """Check if PostgreSQL is reachable via TCP (works with Docker, system, or user-space installs)."""
    import socket
    db_host = os.environ.get("DB_HOST", "localhost")
    db_port = int(os.environ.get("DB_PORT", "5432"))
    try:
        with socket.create_connection((db_host, db_port), timeout=2):
            return True
    except (OSError, ConnectionRefusedError):
        return False


def is_postgres_running():
    """Check if PostgreSQL is running (user-space install via pg_ctl)."""
    pg_ctl = find_pg_ctl()
    if not pg_ctl or not PG_DATA.exists():
        return False

    try:
        result = subprocess.run(
            [pg_ctl, "-D", str(PG_DATA), "status"],
            capture_output=True,
            text=True
        )
        return result.returncode == 0
    except Exception:
        return False


def install_postgres():
    """Run the PostgreSQL installer script to install and configure PostgreSQL."""
    install_script = INSTALLER_DIR / "install_postgres.sh"

    if not install_script.exists():
        print(f"   [ERROR] PostgreSQL installer not found: {install_script}")
        return False

    print("   Installing PostgreSQL (first-time setup)...")
    try:
        result = subprocess.run(
            ["bash", str(install_script)],
            cwd=str(INSTALLER_DIR),
            timeout=300
        )

        if result.returncode == 0:
            if PG_BIN.exists():
                os.environ['PATH'] = f"{PG_BIN}:{os.environ.get('PATH', '')}"
            print("   [OK] PostgreSQL installed successfully")
            return True
        else:
            print("   [ERROR] PostgreSQL installer exited with errors")
            return False
    except subprocess.TimeoutExpired:
        print("   [ERROR] PostgreSQL installation timed out")
        return False
    except Exception as e:
        print(f"   [ERROR] Failed to run PostgreSQL installer: {e}")
        return False


def start_postgres():
    """Start PostgreSQL, installing it first if needed.

    Checks for PostgreSQL in this order:
    1. TCP reachability (Docker container, system install, or remote DB)
    2. User-space pg_ctl status
    3. Install user-space PostgreSQL as a last resort
    """
    print("Starting PostgreSQL...")

    # First check if PostgreSQL is already reachable (Docker, system, or remote)
    if is_postgres_reachable():
        db_host = os.environ.get("DB_HOST", "localhost")
        db_port = os.environ.get("DB_PORT", "5432")
        print(f"   [OK] PostgreSQL already reachable at {db_host}:{db_port}")
        return True

    # Check user-space installation
    if is_postgres_running():
        print("   [OK] PostgreSQL already running (user-space)")
        return True

    pg_ctl = find_pg_ctl()

    # If PostgreSQL is not installed, run the installer automatically
    if not pg_ctl or not PG_DATA.exists():
        print("   [INFO] PostgreSQL not installed - running installer...")
        if not install_postgres():
            print("   [ERROR] PostgreSQL installation failed - backend cannot start")
            return False
        pg_ctl = find_pg_ctl()
        if not pg_ctl:
            print("   [ERROR] pg_ctl still not found after installation")
            return False

    # Add PG_BIN to PATH for this process
    if PG_BIN.exists():
        os.environ['PATH'] = f"{PG_BIN}:{os.environ.get('PATH', '')}"

    try:
        result = subprocess.run(
            [pg_ctl, "-D", str(PG_DATA), "-l", str(PG_LOG), "-o", f"-k {PG_HOME}", "start"],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            # Wait for PostgreSQL to be ready
            time.sleep(2)
            if is_postgres_running():
                print("   [OK] PostgreSQL started")
                return True

        print(f"   [WARN] PostgreSQL may not have started: {result.stderr}")
        return False
    except Exception as e:
        print(f"   [WARN] Failed to start PostgreSQL: {e}")
        return False


def find_uvicorn():
    """Find uvicorn executable."""
    # Check in backend venv first
    venv_uvicorn = BACKEND_DIR / "venv" / "bin" / "uvicorn"
    if venv_uvicorn.exists():
        return str(venv_uvicorn)

    # Check in user's local bin
    local_uvicorn = Path.home() / ".local/bin/uvicorn"
    if local_uvicorn.exists():
        return str(local_uvicorn)

    # Fall back to PATH
    return "uvicorn"


def start_backend():
    """Start the FastAPI backend server."""
    print("Starting backend server...")

    # If the port is already served, try to reclaim it; if we can't free it,
    # assume it's a healthy backend and do NOT spawn a duplicate (would fail
    # to bind with Errno 98).
    if is_running(BACKEND_PORT):
        print(f"   Port {BACKEND_PORT} in use, stopping existing process...")
        kill_process_on_port(BACKEND_PORT, "backend")
        time.sleep(1)
        if is_running(BACKEND_PORT):
            print(f"   [OK] Backend already serving on port {BACKEND_PORT}; leaving it")
            return None

    uvicorn_path = find_uvicorn()
    print(f"   Using uvicorn: {uvicorn_path}")

    # Configure workers for better throughput
    # Use multiple workers in production, single worker with reload in development
    worker_count = int(os.environ.get("WORKERS", "4"))
    dev_mode = os.environ.get("RELOAD", "0") == "1"

    cmd = [uvicorn_path, "app.main:app", "--host", HOST_BIND, "--port", str(BACKEND_PORT)]
    if dev_mode:
        cmd.append("--reload")
        print(f"   Development mode: hot reload enabled")
    else:
        cmd.extend(["--workers", str(worker_count)])
        print(f"   Production mode: {worker_count} workers")

    log_file = open(BACKEND_LOG, 'w')
    process = subprocess.Popen(
        cmd,
        cwd=BACKEND_DIR,
        stdout=log_file,
        stderr=subprocess.STDOUT,
        start_new_session=True
    )

    # Wait for it to start
    for i in range(30):
        time.sleep(0.5)
        if is_running(BACKEND_PORT):
            print(f"   [OK] Backend started on http://{HOST_BIND}:{BACKEND_PORT}")
            return process.pid

    print(f"   [WARN] Backend may not have started correctly")
    print(f"   Check logs: {BACKEND_LOG}")
    return process.pid


def start_frontend():
    """Start the Vite frontend server."""
    print("Starting frontend server...")

    # If the port is already served, try to reclaim it; if we can't free it,
    # assume it's a healthy frontend and do NOT spawn a duplicate.
    if is_running(FRONTEND_PORT):
        print(f"   Port {FRONTEND_PORT} in use, stopping existing process...")
        kill_process_on_port(FRONTEND_PORT, "frontend")
        time.sleep(1)
        if is_running(FRONTEND_PORT):
            print(f"   [OK] Frontend already serving on port {FRONTEND_PORT}; leaving it")
            return None

    # Find npm (supports nvm installation)
    npm_cmd = find_npm()
    print(f"   Using npm: {npm_cmd}")

    # Check if node_modules exists
    if not (PROJECT_DIR / "node_modules").exists():
        print("   Installing frontend dependencies...")
        subprocess.run([npm_cmd, "install"], cwd=PROJECT_DIR, check=True, capture_output=True)

    log_file = open(FRONTEND_LOG, 'w')
    process = subprocess.Popen(
        [npm_cmd, "run", "dev", "--", "--host", HOST_BIND, "--port", str(FRONTEND_PORT)],
        cwd=PROJECT_DIR,
        stdin=subprocess.DEVNULL,
        stdout=log_file,
        stderr=subprocess.STDOUT,
        start_new_session=True
    )

    # Wait for it to start
    for i in range(30):
        time.sleep(0.5)
        if is_running(FRONTEND_PORT):
            print(f"   [OK] Frontend started on http://{HOST_BIND}:{FRONTEND_PORT}")
            return process.pid

    print(f"   [WARN] Frontend may not have started correctly")
    print(f"   Check logs: {FRONTEND_LOG}")
    return process.pid


def main():
    """Start all services."""
    print("=" * 60)
    print("Network Data Lakehouse - Starting Services")
    print("=" * 60)
    print()

    # Start PostgreSQL first - fail early if database is unavailable
    if not start_postgres():
        print("[ERROR] PostgreSQL is not available. Backend cannot start without a database.")
        print("        To install manually, run: bash installer/install_postgres.sh")
        return 1
    print()

    # Start backend
    backend_pid = start_backend()
    print()

    # Start frontend
    frontend_pid = start_frontend()

    # Save PIDs
    save_pids(backend_pid, frontend_pid)

    print()
    print("=" * 60)
    print("Services Running")
    print("=" * 60)
    print(f"   Backend API:  http://{HOST_BIND}:{BACKEND_PORT}")
    print(f"   Frontend UI:  http://{HOST_BIND}:{FRONTEND_PORT}")
    print()
    print("Logs:")
    print(f"   Backend:  {BACKEND_LOG}")
    print(f"   Frontend: {FRONTEND_LOG}")
    print()
    print("To stop services:")
    print("   python stop.py")
    print()

    # Check if running in CML/CDSW environment (needs to stay alive)
    if IS_CML_ENVIRONMENT:
        print("Running in Cloudera Machine Learning - keeping process alive...")
        print(f"   Using CDSW_READONLY_PORT: {os.getenv('CDSW_READONLY_PORT', 'N/A')}")
        print(f"   Using CDSW_APP_PORT: {os.getenv('CDSW_APP_PORT', 'N/A')}")
        print("Press Ctrl+C to stop")
        print()

        # Block forever, monitoring services
        while True:
            time.sleep(30)
            # Check if services are still running
            if not is_running(BACKEND_PORT):
                print("[WARN] Backend stopped unexpectedly, restarting...")
                start_backend()
            if not is_running(FRONTEND_PORT):
                print("[WARN] Frontend stopped unexpectedly, restarting...")
                start_frontend()

    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nStartup cancelled")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
