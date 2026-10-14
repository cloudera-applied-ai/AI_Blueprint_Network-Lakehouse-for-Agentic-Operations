#!/usr/bin/env python3
"""
CML AMP Step: Initialize Database
Downloads portable PostgreSQL, creates database and user.
"""

import os
import sys
import subprocess
import stat
from pathlib import Path


def get_project_root():
    cwd = Path(os.getcwd()).resolve()
    if (cwd / "installer").exists():
        return cwd
    # CML exec's job scripts in a kernel where __file__ is undefined (cwd is the root).
    f = globals().get("__file__")
    return Path(f).resolve().parents[2] if f else cwd  # deploy/cml/<script>.py


def main():
    root = get_project_root()
    installer_dir = root / "installer"
    script = installer_dir / "install_postgres.sh"

    if not script.exists():
        print(f"ERROR: PostgreSQL installer not found: {script}")
        sys.exit(1)

    # Make executable
    script.chmod(script.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    print("=" * 60)
    print("Initializing PostgreSQL...")
    print("=" * 60)

    # Pass DB env vars through (set by .project-metadata.yaml)
    env = os.environ.copy()
    env.setdefault("DB_NAME", "cable_network")
    env.setdefault("DB_USER", "cable_user")
    env.setdefault("DB_PASSWORD", "cable_secure_pass_2024")
    env.setdefault("DB_PORT", "5432")

    result = subprocess.run(["bash", str(script)], cwd=str(installer_dir), env=env)

    if result.returncode != 0:
        print("WARNING: PostgreSQL installation had issues.")
        print("If using an external database, set DATABASE_URL and this step can be skipped.")
    else:
        print("\nPostgreSQL initialized successfully!")
        print(f"  Database: {env['DB_NAME']}")
        print(f"  User: {env['DB_USER']}")
        print(f"  Port: {env['DB_PORT']}")


if __name__ == "__main__":
    main()
