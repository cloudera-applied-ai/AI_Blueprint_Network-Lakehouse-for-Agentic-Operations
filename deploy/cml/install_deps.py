#!/usr/bin/env python3
"""
CML AMP Step: Install Dependencies
Installs Python backend packages and Node.js frontend packages.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path


def get_project_root():
    """Get project root directory."""
    # In CML, scripts run from project root
    cwd = Path(os.getcwd()).resolve()
    if (cwd / "application").exists():
        return cwd
    # CML exec's job scripts in a kernel where __file__ is undefined (cwd is the root).
    f = globals().get("__file__")
    return Path(f).resolve().parents[2] if f else cwd  # deploy/cml/<script>.py


def find_npm():
    """Find npm binary, checking nvm installation if needed."""
    npm = shutil.which("npm")
    if npm:
        return npm

    # Check nvm installation
    nvm_dir = Path.home() / ".nvm" / "versions" / "node"
    if nvm_dir.exists():
        for version_dir in sorted(nvm_dir.iterdir(), reverse=True):
            npm_path = version_dir / "bin" / "npm"
            if npm_path.exists():
                os.environ["PATH"] = f"{version_dir / 'bin'}:{os.environ.get('PATH', '')}"
                return str(npm_path)

    return None


def install_node():
    """Install Node.js via nvm if not available."""
    if shutil.which("node"):
        version = subprocess.run(["node", "--version"], capture_output=True, text=True).stdout.strip()
        print(f"Node.js already available: {version}")
        return True

    print("Node.js not found, installing via nvm...")
    nvm_dir = Path.home() / ".nvm"

    # Install nvm
    if not (nvm_dir / "nvm.sh").exists():
        result = subprocess.run(
            ["bash", "-c", "curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash"],
            env={**os.environ, "NVM_DIR": str(nvm_dir)},
        )
        if result.returncode != 0:
            print("ERROR: Failed to install nvm")
            return False

    # Install Node 22
    install_script = f"""
        export NVM_DIR="{nvm_dir}"
        [ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
        nvm install 22
        nvm use 22
        nvm alias default 22
    """
    result = subprocess.run(
        ["bash", "-c", install_script],
        env={**os.environ, "NVM_DIR": str(nvm_dir)},
    )
    if result.returncode != 0:
        print("ERROR: Failed to install Node.js")
        return False

    # Add to PATH
    versions_dir = nvm_dir / "versions" / "node"
    if versions_dir.exists():
        for vdir in versions_dir.iterdir():
            if vdir.name.startswith("v22"):
                os.environ["PATH"] = f"{vdir / 'bin'}:{os.environ.get('PATH', '')}"
                break

    print("Node.js 22 installed successfully")
    return True


def main():
    root = get_project_root()
    app_dir = root / "application"
    backend_dir = app_dir / "backend"

    # 1. Install Python dependencies
    print("=" * 60)
    print("Installing Python dependencies...")
    print("=" * 60)

    req_file = backend_dir / "requirements.txt"
    if not req_file.exists():
        print(f"ERROR: {req_file} not found")
        sys.exit(1)

    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "--no-cache-dir", "-r", str(req_file)],
    )
    if result.returncode != 0:
        print("ERROR: Python dependency installation failed")
        sys.exit(1)
    print("Python dependencies installed successfully")

    # 2. Install Node.js if needed
    print("\n" + "=" * 60)
    print("Checking Node.js...")
    print("=" * 60)

    if not install_node():
        print("ERROR: Node.js installation failed")
        sys.exit(1)

    # 3. Install frontend dependencies
    print("\n" + "=" * 60)
    print("Installing frontend dependencies...")
    print("=" * 60)

    npm = find_npm()
    if not npm:
        print("ERROR: npm not found")
        sys.exit(1)

    result = subprocess.run([npm, "install"], cwd=str(app_dir))
    if result.returncode != 0:
        print("ERROR: npm install failed")
        sys.exit(1)
    print("Frontend dependencies installed successfully")

    print("\n" + "=" * 60)
    print("All dependencies installed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
