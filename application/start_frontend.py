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
Network Data Lakehouse - Frontend Server Startup Script
Starts the Vite/React frontend server as a standalone Cloudera AMP application.
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
        # start_frontend.py is in application/, project root is parent
        return Path(__file__).parent.parent.resolve()
    except NameError:
        cwd = Path(os.getcwd()).resolve()
        if cwd.name == 'application':
            return cwd.parent
        return cwd


PROJECT_DIR = _get_project_dir()
APP_DIR = PROJECT_DIR / "application"
FRONTEND_LOG = APP_DIR / "frontend.log"

# Cloudera environment configuration
# In CML, the app listens on CDSW_APP_PORT (8100)
FRONTEND_PORT = int(os.getenv('CDSW_READONLY_PORT', os.getenv('CDSW_APP_PORT', '8100')))

# In CML environment, bind to 127.0.0.1
IS_CML_ENVIRONMENT = bool(os.getenv('CDSW_READONLY_PORT') or os.getenv('CDSW_APP_PORT') or os.getenv('CDSW_PROJECT'))
HOST_BIND = '127.0.0.1' if IS_CML_ENVIRONMENT else '0.0.0.0'


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


def find_npm():
    """Find npm executable, checking nvm installation if needed."""
    npm_path = shutil.which('npm')
    if npm_path:
        return npm_path

    nvm_dir = Path.home() / ".nvm" / "versions" / "node"
    if nvm_dir.exists():
        for version_dir in sorted(nvm_dir.iterdir(), reverse=True):
            npm_path = version_dir / "bin" / "npm"
            if npm_path.exists():
                bin_dir = version_dir / "bin"
                os.environ['PATH'] = f"{bin_dir}:{os.environ.get('PATH', '')}"
                return str(npm_path)

    return 'npm'


def start_frontend():
    """Start the Vite frontend server."""
    print("Starting frontend server...")

    if is_running(FRONTEND_PORT):
        print(f"   Port {FRONTEND_PORT} in use, stopping existing process...")
        kill_process_on_port(FRONTEND_PORT, "frontend")
        time.sleep(1)

    npm_cmd = find_npm()
    print(f"   Using npm: {npm_cmd}")

    # Check if node_modules exists (in APP_DIR where package.json lives)
    if not (APP_DIR / "node_modules").exists():
        print("   Installing frontend dependencies...")
        subprocess.run([npm_cmd, "install"], cwd=APP_DIR, check=True, capture_output=True)

    # Check for optional environment variable
    backend_url = os.getenv('VITE_API_BASE_URL', '')
    if backend_url:
        print(f"   Backend URL: {backend_url}")
    else:
        print("   [INFO] Backend URL can be configured in Settings panel after deployment")

    log_file = open(FRONTEND_LOG, 'w')
    process = subprocess.Popen(
        [npm_cmd, "run", "dev", "--", "--host", HOST_BIND, "--port", str(FRONTEND_PORT)],
        cwd=APP_DIR,
        stdin=subprocess.DEVNULL,
        stdout=log_file,
        stderr=subprocess.STDOUT,
        start_new_session=True
    )

    for i in range(30):
        time.sleep(0.5)
        if is_running(FRONTEND_PORT):
            print(f"   [OK] Frontend started on http://{HOST_BIND}:{FRONTEND_PORT}")
            return process.pid

    print(f"   [WARN] Frontend may not have started correctly")
    print(f"   Check logs: {FRONTEND_LOG}")
    return process.pid


def main():
    """Start the frontend service."""
    print("=" * 60)
    print("Network Data Lakehouse - Frontend Server")
    print("=" * 60)
    print()

    # Start frontend
    frontend_pid = start_frontend()

    print()
    print("=" * 60)
    print("Frontend Service Running")
    print("=" * 60)
    print(f"   Frontend UI:  http://{HOST_BIND}:{FRONTEND_PORT}")
    print()
    print("Logs:")
    print(f"   Frontend: {FRONTEND_LOG}")
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
