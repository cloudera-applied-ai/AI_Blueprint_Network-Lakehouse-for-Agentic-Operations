#!/usr/bin/env python3
"""
Network Data Lakehouse - Server Stop Script
Stops both frontend and backend servers.
"""

import os
import sys
import signal
import subprocess
import shutil
import time
from pathlib import Path

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
PID_FILE = PROJECT_DIR / ".server_pids"

FRONTEND_PORT = 8100
BACKEND_PORT = 8000

# PostgreSQL paths (user-space installation)
PG_HOME = Path.home() / ".postgres"
PG_DATA = PG_HOME / "data"
PG_BIN = PG_HOME / "bin"


def find_pg_ctl():
    """Find pg_ctl executable."""
    pg_ctl = PG_BIN / "pg_ctl"
    if pg_ctl.exists():
        return str(pg_ctl)
    pg_ctl_path = shutil.which('pg_ctl')
    if pg_ctl_path:
        return pg_ctl_path
    return None


def is_postgres_running():
    """Check if PostgreSQL is running."""
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


def stop_postgres():
    """Stop PostgreSQL if running."""
    print("Stopping PostgreSQL...")

    pg_ctl = find_pg_ctl()
    if not pg_ctl or not PG_DATA.exists():
        print("   [SKIP] PostgreSQL not installed locally")
        return False

    if not is_postgres_running():
        print("   [OK] PostgreSQL not running")
        return False

    try:
        result = subprocess.run(
            [pg_ctl, "-D", str(PG_DATA), "stop", "-m", "fast"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print("   [OK] PostgreSQL stopped")
            return True
        print(f"   [WARN] Failed to stop PostgreSQL: {result.stderr}")
        return False
    except Exception as e:
        print(f"   [WARN] Error stopping PostgreSQL: {e}")
        return False


def get_pids_on_port(port):
    """Best-effort PID lookup for a port, used to kill stale processes.

    Tries lsof, then fuser, then ss — CML/CAI runtimes often ship none of
    them. Returns [] when no tool is available.
    """
    import re
    for cmd in (["lsof", "-t", "-i", f":{port}"], ["fuser", f"{port}/tcp"]):
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
    try:
        result = subprocess.run(
            ["ss", "-lptnH", f"sport = :{port}"], capture_output=True, text=True
        )
        if result.returncode == 0 and result.stdout:
            return [int(p) for p in re.findall(r"pid=(\d+)", result.stdout)]
    except Exception:
        pass
    return []


def is_running(port):
    """Check if a service is listening on the port (socket probe, no lsof)."""
    import socket
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=1):
            return True
    except OSError:
        return False


def kill_process_on_port(port, name="process"):
    """Kill any process running on the specified port."""
    pids = get_pids_on_port(port)
    killed = False
    for pid in pids:
        try:
            os.kill(pid, signal.SIGTERM)
            print(f"   Stopped {name} (PID {pid})")
            killed = True
        except ProcessLookupError:
            pass
        except Exception as e:
            print(f"   Warning: Could not stop PID {pid}: {e}")
    return killed


def load_pids():
    """Load PIDs from file."""
    try:
        with open(PID_FILE, 'r') as f:
            lines = f.read().strip().split('\n')
            backend_pid = int(lines[0]) if lines[0] else None
            frontend_pid = int(lines[1]) if len(lines) > 1 and lines[1] else None
            return backend_pid, frontend_pid
    except Exception:
        return None, None


def clear_pids():
    """Remove PID file."""
    try:
        PID_FILE.unlink()
    except Exception:
        pass


def main():
    """Stop both servers."""
    print("=" * 60)
    print("Network Data Lakehouse - Stopping Services")
    print("=" * 60)
    print()

    backend_stopped = False
    frontend_stopped = False

    # Stop backend
    print("Stopping backend...")
    if is_running(BACKEND_PORT):
        backend_stopped = kill_process_on_port(BACKEND_PORT, "backend")
    else:
        print(f"   Not running on port {BACKEND_PORT}")

    print()

    # Stop frontend
    print("Stopping frontend...")
    if is_running(FRONTEND_PORT):
        frontend_stopped = kill_process_on_port(FRONTEND_PORT, "frontend")
    else:
        print(f"   Not running on port {FRONTEND_PORT}")

    # Also try to kill by saved PIDs
    backend_pid, frontend_pid = load_pids()
    for pid in [backend_pid, frontend_pid]:
        if pid:
            try:
                os.kill(pid, signal.SIGTERM)
            except Exception:
                pass

    clear_pids()

    # Give processes time to terminate
    time.sleep(1)

    print()

    # Stop PostgreSQL
    postgres_stopped = stop_postgres()

    print()
    if backend_stopped or frontend_stopped or postgres_stopped:
        print("[OK] Services stopped")
    else:
        print("[INFO] No services were running")

    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nCancelled")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
