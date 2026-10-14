#!/usr/bin/env python3
"""
CML AMP Step: Start Application
Launches the combined frontend + backend application.
Delegates to the existing start.py which handles CML detection,
PostgreSQL startup, and service monitoring.
"""

import os
import sys
import subprocess
from pathlib import Path


def get_project_root():
    cwd = Path(os.getcwd()).resolve()
    if (cwd / "application").exists():
        return cwd
    # CML exec's job scripts in a kernel where __file__ is undefined (cwd is the root).
    f = globals().get("__file__")
    return Path(f).resolve().parents[2] if f else cwd  # deploy/cml/<script>.py


def main():
    root = get_project_root()
    app_dir = root / "application"
    start_script = app_dir / "start.py"

    if not start_script.exists():
        print(f"ERROR: start.py not found: {start_script}")
        sys.exit(1)

    print("=" * 60)
    print("Starting Cable Network Data Lakehouse")
    print("=" * 60)
    print(f"CML detected: {bool(os.getenv('CDSW_PROJECT') or os.getenv('CDSW_APP_PORT'))}")
    print(f"App port: {os.getenv('CDSW_APP_PORT', os.getenv('CDSW_READONLY_PORT', '8100'))}")
    print()

    # Execute start.py in the application directory
    # This handles PostgreSQL startup, backend, frontend, and CML monitoring
    os.chdir(str(app_dir))
    result = subprocess.run([sys.executable, str(start_script)])
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
