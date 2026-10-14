#!/usr/bin/env python3
"""
CML AMP Step: Build Frontend
Runs TypeScript compilation and Vite production build.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path


def get_project_root():
    cwd = Path(os.getcwd()).resolve()
    if (cwd / "application").exists():
        return cwd
    # CML exec's job scripts in a kernel where __file__ is undefined (cwd is the root).
    f = globals().get("__file__")
    return Path(f).resolve().parents[2] if f else cwd  # deploy/cml/<script>.py


def find_npm():
    npm = shutil.which("npm")
    if npm:
        return npm

    nvm_dir = Path.home() / ".nvm" / "versions" / "node"
    if nvm_dir.exists():
        for version_dir in sorted(nvm_dir.iterdir(), reverse=True):
            npm_path = version_dir / "bin" / "npm"
            if npm_path.exists():
                os.environ["PATH"] = f"{version_dir / 'bin'}:{os.environ.get('PATH', '')}"
                return str(npm_path)

    return None


def main():
    root = get_project_root()
    app_dir = root / "application"

    npm = find_npm()
    if not npm:
        print("ERROR: npm not found. Run install_deps.py first.")
        sys.exit(1)

    # Check node_modules exists
    if not (app_dir / "node_modules").exists():
        print("node_modules not found, running npm install...")
        result = subprocess.run([npm, "install"], cwd=str(app_dir))
        if result.returncode != 0:
            print("ERROR: npm install failed")
            sys.exit(1)

    print("=" * 60)
    print("Building frontend (tsc + vite build)...")
    print("=" * 60)

    # Set VITE_ env vars for the build so they're baked into the bundle
    build_env = os.environ.copy()
    build_env.setdefault("VITE_API_KEY", build_env.get("API_KEY", "dev-api-key-change-me"))

    result = subprocess.run([npm, "run", "build"], cwd=str(app_dir), env=build_env)
    if result.returncode != 0:
        print("WARNING: Production build failed. Dev mode will still work.")
    else:
        print("Frontend built successfully!")
        dist_dir = app_dir / "dist"
        if dist_dir.exists():
            file_count = sum(1 for _ in dist_dir.rglob("*") if _.is_file())
            print(f"Output: {dist_dir} ({file_count} files)")


if __name__ == "__main__":
    main()
