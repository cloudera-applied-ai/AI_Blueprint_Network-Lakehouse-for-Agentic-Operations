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
Network Data Lakehouse - Backend Server Startup Script
Starts the FastAPI backend server as a standalone Cloudera AMP application.
"""

import os
import sys
import signal
import subprocess
import time
import shutil
from pathlib import Path


def _get_project_dir():
    """Get project directory, works in both script and Jupyter environments."""
    try:
        return Path(__file__).parent.resolve()
    except NameError:
        cwd = Path(os.getcwd()).resolve()
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
BACKEND_LOG = PROJECT_DIR / "backend.log"

# Cloudera environment configuration
# In CML, the app listens on CDSW_APP_PORT (8100)
BACKEND_PORT = int(os.getenv('CDSW_READONLY_PORT', os.getenv('CDSW_APP_PORT', '8100')))

# In CML environment, bind to 127.0.0.1
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
    liveness (use is_running, which needs no external tools).
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
    """Check if a service is listening on the port (socket probe, no lsof).

    CML/CAI runtimes typically don't include lsof; the old lsof-based check
    always returned False, causing duplicate process spawns and Errno 98.
    """
    import socket
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=1):
            return True
    except OSError:
        return False


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
            # Update PATH so we can find pg_ctl after installation
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


def ensure_database_setup():
    """Ensure database user and database exist using single-user mode.

    Zonky embedded PostgreSQL binaries do not include psql, so we use
    postgres --single to create the user and database if missing.
    Requires the server to be stopped.
    """
    postgres_bin = PG_BIN / "postgres"
    if not postgres_bin.exists() or not PG_DATA.exists():
        return

    pg_ctl = find_pg_ctl()
    db_user = os.environ.get("DB_USER", "cable_user")
    db_password = os.environ.get("DB_PASSWORD", "cable_secure_pass_2024")
    db_name = os.environ.get("DB_NAME", "cable_network")

    # Stop server for single-user mode
    if pg_ctl:
        subprocess.run([pg_ctl, "-D", str(PG_DATA), "stop"], capture_output=True)
        time.sleep(1)

    # Create user
    subprocess.run(
        [str(postgres_bin), "--single", "-D", str(PG_DATA), "postgres"],
        input=f"CREATE USER {db_user} WITH PASSWORD '{db_password}';\n",
        capture_output=True, text=True
    )
    # Ensure password is current
    subprocess.run(
        [str(postgres_bin), "--single", "-D", str(PG_DATA), "postgres"],
        input=f"ALTER USER {db_user} WITH PASSWORD '{db_password}';\n",
        capture_output=True, text=True
    )
    # Create database
    subprocess.run(
        [str(postgres_bin), "--single", "-D", str(PG_DATA), "postgres"],
        input=f"CREATE DATABASE {db_name} OWNER {db_user};\n",
        capture_output=True, text=True
    )
    # Grant schema privileges
    subprocess.run(
        [str(postgres_bin), "--single", "-D", str(PG_DATA), db_name],
        input=f"GRANT ALL ON SCHEMA public TO {db_user};\n",
        capture_output=True, text=True
    )
    print("   [OK] Database setup verified")


def start_postgres():
    """Start PostgreSQL, installing it first if needed."""
    print("Starting PostgreSQL...")

    pg_ctl = find_pg_ctl()

    # If PostgreSQL is not installed, run the installer automatically
    if not pg_ctl or not PG_DATA.exists():
        print("   [INFO] PostgreSQL not installed - running installer...")
        if not install_postgres():
            print("   [ERROR] PostgreSQL installation failed - backend cannot start")
            return False
        # Re-check after installation
        pg_ctl = find_pg_ctl()
        if not pg_ctl:
            print("   [ERROR] pg_ctl still not found after installation")
            return False

    if PG_BIN.exists():
        os.environ['PATH'] = f"{PG_BIN}:{os.environ.get('PATH', '')}"

    # Ensure user and database exist (uses single-user mode, server must be stopped)
    ensure_database_setup()

    if is_postgres_running():
        print("   [OK] PostgreSQL already running")
        return True

    try:
        result = subprocess.run(
            [pg_ctl, "-D", str(PG_DATA), "-l", str(PG_LOG), "-o", f"-k {PG_HOME}", "start"],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
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
    venv_uvicorn = BACKEND_DIR / "venv" / "bin" / "uvicorn"
    if venv_uvicorn.exists():
        return str(venv_uvicorn)
    local_uvicorn = Path.home() / ".local/bin/uvicorn"
    if local_uvicorn.exists():
        return str(local_uvicorn)
    return "uvicorn"


def start_backend():
    """Start the FastAPI backend server."""
    print("Starting backend server...")

    if is_running(BACKEND_PORT):
        print(f"   Port {BACKEND_PORT} in use, stopping existing process...")
        kill_process_on_port(BACKEND_PORT, "backend")
        time.sleep(1)

    uvicorn_path = find_uvicorn()
    print(f"   Using uvicorn: {uvicorn_path}")

    log_file = open(BACKEND_LOG, 'w')
    process = subprocess.Popen(
        [uvicorn_path, "app.main:app", "--host", HOST_BIND, "--port", str(BACKEND_PORT)],
        cwd=BACKEND_DIR,
        stdout=log_file,
        stderr=subprocess.STDOUT,
        start_new_session=True
    )

    for i in range(30):
        time.sleep(0.5)
        if is_running(BACKEND_PORT):
            print(f"   [OK] Backend started on http://{HOST_BIND}:{BACKEND_PORT}")
            return process.pid

    print(f"   [WARN] Backend may not have started correctly")
    print(f"   Check logs: {BACKEND_LOG}")
    return process.pid


def main():
    """Start the backend service."""
    print("=" * 60)
    print("Network Data Lakehouse - Backend Server")
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
    print("=" * 60)
    print("Backend Service Running")
    print("=" * 60)
    print(f"   Backend API:  http://{HOST_BIND}:{BACKEND_PORT}")
    print(f"   API Docs:     http://{HOST_BIND}:{BACKEND_PORT}/docs")
    print()
    print("Logs:")
    print(f"   Backend:  {BACKEND_LOG}")
    print()

    # In CML environment, keep process alive
    if IS_CML_ENVIRONMENT:
        print("Running in Cloudera Machine Learning - keeping process alive...")
        print(f"   Using CDSW_READONLY_PORT: {os.getenv('CDSW_READONLY_PORT', 'N/A')}")
        print(f"   Using CDSW_APP_PORT: {os.getenv('CDSW_APP_PORT', 'N/A')}")
        print("Press Ctrl+C to stop")
        print()

        while True:
            time.sleep(30)
            if not is_running(BACKEND_PORT):
                print("[WARN] Backend stopped unexpectedly, restarting...")
                start_backend()

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
