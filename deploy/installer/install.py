#!/usr/bin/env python3
"""
Network Data Lakehouse - Cloudera Installer
Automated installation of all dependencies with no prompts.
"""

import os
import sys
import subprocess
import shutil
import stat
from pathlib import Path

# ANSI color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def print_header(message):
    """Print a formatted header message"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'=' * 70}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{message:^70}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'=' * 70}{Colors.ENDC}\n")


def print_success(message):
    print(f"{Colors.OKGREEN}[OK] {message}{Colors.ENDC}")


def print_error(message):
    print(f"{Colors.FAIL}[ERROR] {message}{Colors.ENDC}")


def print_warning(message):
    print(f"{Colors.WARNING}[WARN] {message}{Colors.ENDC}")


def print_info(message):
    print(f"{Colors.OKCYAN}[INFO] {message}{Colors.ENDC}")


def run_command(cmd, cwd=None, env=None):
    """Run a command and return success status"""
    try:
        # Use current os.environ if no env specified (includes PATH updates)
        run_env = env if env is not None else os.environ.copy()
        result = subprocess.run(
            cmd,
            cwd=cwd,
            env=run_env,
            check=True,
            capture_output=True,
            text=True
        )
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, e.stderr or e.stdout or str(e)


def check_command(command):
    """Check if a command exists"""
    return shutil.which(command) is not None


def install_nodejs():
    """Install Node.js using nvm (Node Version Manager)"""
    print_header("Installing Node.js")

    home_dir = Path.home()
    nvm_dir = home_dir / ".nvm"
    node_version = "22"  # LTS version

    # Check if nvm is already installed
    nvm_script = nvm_dir / "nvm.sh"

    if not nvm_script.exists():
        print_info("Installing nvm (Node Version Manager)...")

        # Download and install nvm
        try:
            result = subprocess.run(
                ['bash', '-c', 'curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash'],
                capture_output=True,
                text=True,
                env={**os.environ, 'NVM_DIR': str(nvm_dir)}
            )

            if result.returncode != 0:
                print_error(f"Failed to install nvm: {result.stderr}")
                return False

            print_success("nvm installed successfully")
        except Exception as e:
            print_error(f"Failed to install nvm: {e}")
            return False
    else:
        print_info("nvm already installed")

    # Install Node.js using nvm
    print_info(f"Installing Node.js {node_version} via nvm...")

    # Create a bash script to source nvm and install node
    install_script = f'''
        export NVM_DIR="{nvm_dir}"
        [ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
        nvm install {node_version}
        nvm use {node_version}
        nvm alias default {node_version}
    '''

    try:
        result = subprocess.run(
            ['bash', '-c', install_script],
            capture_output=True,
            text=True,
            env={**os.environ, 'NVM_DIR': str(nvm_dir)}
        )

        if result.returncode != 0:
            print_error(f"Failed to install Node.js: {result.stderr}")
            return False

        print_success(f"Node.js {node_version} installed successfully")
    except Exception as e:
        print_error(f"Failed to install Node.js: {e}")
        return False

    # Add node to PATH for this session
    node_bin = nvm_dir / "versions" / "node" / f"v{node_version}."

    # Find the actual version directory (e.g., v22.x.x)
    versions_dir = nvm_dir / "versions" / "node"
    if versions_dir.exists():
        for version_dir in versions_dir.iterdir():
            if version_dir.name.startswith(f"v{node_version}"):
                node_bin_dir = version_dir / "bin"
                if node_bin_dir.exists():
                    os.environ['PATH'] = f"{node_bin_dir}:{os.environ.get('PATH', '')}"
                    print_info(f"Added {node_bin_dir} to PATH")
                    break

    # Verify installation
    if check_command('node'):
        version = get_version('node')
        print_success(f"Node.js is now available: {version}")
        return True
    else:
        print_error("Node.js installation completed but 'node' command not found in PATH")
        print_info("You may need to restart your shell or run: source ~/.bashrc")
        return False


def get_version(command):
    """Get version of a command"""
    try:
        result = subprocess.run(
            [command, '--version'],
            capture_output=True,
            text=True
        )
        return result.stdout.strip().split('\n')[0]
    except Exception:
        return "unknown"


def check_prerequisites():
    """Check all prerequisites are met, installing Node.js if needed"""
    print_header("Checking Prerequisites")

    all_ok = True

    # Check Python
    py_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    if sys.version_info.major >= 3 and sys.version_info.minor >= 8:
        print_success(f"Python {py_version}")
    else:
        print_error(f"Python {py_version} - requires >= 3.8")
        all_ok = False

    # Check Node.js - install if not found
    node_ok = False
    if check_command('node'):
        version = get_version('node')
        print_success(f"Node.js {version}")
        try:
            major = int(version.split('.')[0].replace('v', ''))
            if major < 22:
                print_warning("Node.js >= 22 recommended, will install newer version")
                if install_nodejs():
                    node_ok = True
                else:
                    all_ok = False
            else:
                node_ok = True
        except ValueError:
            node_ok = True
    else:
        print_warning("Node.js not found - will install automatically")
        if install_nodejs():
            node_ok = True
        else:
            print_error("Failed to install Node.js")
            all_ok = False

    # Check npm (should be available after Node.js installation)
    if check_command('npm'):
        version = get_version('npm')
        print_success(f"npm {version}")
    else:
        if node_ok:
            # npm should come with node, try to find it
            print_warning("npm not found in PATH, checking nvm installation...")
            nvm_dir = Path.home() / ".nvm" / "versions" / "node"
            if nvm_dir.exists():
                for version_dir in nvm_dir.iterdir():
                    npm_path = version_dir / "bin" / "npm"
                    if npm_path.exists():
                        os.environ['PATH'] = f"{version_dir / 'bin'}:{os.environ.get('PATH', '')}"
                        print_success(f"npm found at {npm_path}")
                        break
                else:
                    print_error("npm not found")
                    all_ok = False
            else:
                print_error("npm not found")
                all_ok = False
        else:
            print_error("npm not found - Node.js installation required")
            all_ok = False

    # Check pip
    if check_command('pip3') or check_command('pip'):
        print_success("pip available")
    else:
        print_error("pip not found")
        all_ok = False

    return all_ok


def get_npm_command():
    """Get the npm command path, checking nvm installation if needed"""
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
                # Also update PATH for subsequent calls
                bin_dir = version_dir / "bin"
                os.environ['PATH'] = f"{bin_dir}:{os.environ.get('PATH', '')}"
                return str(npm_path)

    return 'npm'  # Fallback to hoping it's in PATH


def install_frontend_dependencies(app_dir):
    """Install npm dependencies for frontend"""
    print_header("Installing Frontend Dependencies")

    npm_cmd = get_npm_command()
    print_info(f"Using npm: {npm_cmd}")
    print_info("Running npm install...")

    success, output = run_command([npm_cmd, 'install'], cwd=app_dir)

    if success:
        print_success("Frontend dependencies installed")
        return True
    else:
        print_error(f"npm install failed: {output}")
        return False


def install_backend_dependencies(app_dir):
    """Install Python dependencies for backend"""
    print_header("Installing Backend Dependencies")

    backend_dir = app_dir / "backend"
    requirements_file = backend_dir / "requirements.txt"

    if not requirements_file.exists():
        print_error(f"requirements.txt not found at {requirements_file}")
        return False

    # Use the current Python's pip
    pip_cmd = [sys.executable, '-m', 'pip']

    # Upgrade pip
    print_info("Upgrading pip...")
    run_command(pip_cmd + ['install', '--upgrade', 'pip'])

    # Install requirements
    print_info("Installing Python packages...")
    success, output = run_command(
        pip_cmd + ['install', '-r', str(requirements_file)]
    )

    if success:
        print_success("Backend dependencies installed")
        return True
    else:
        print_error(f"pip install failed: {output}")
        return False


def build_frontend(app_dir):
    """Build frontend for production"""
    print_header("Building Frontend")

    npm_cmd = get_npm_command()
    print_info("Running production build...")
    success, output = run_command([npm_cmd, 'run', 'build'], cwd=app_dir)

    if success:
        print_success("Frontend built successfully")
        return True
    else:
        print_error(f"Build failed: {output}")
        # Non-fatal - dev mode still works
        print_warning("Production build failed, but dev mode will still work")
        return True


def check_postgres_installed():
    """Check if PostgreSQL is installed (system-wide or locally)"""
    # Check system PATH first (pg_ctl is the essential binary)
    if check_command('pg_ctl'):
        return True

    # Check local installation at ~/.postgres/bin
    # Zonky embedded binaries include initdb, pg_ctl, postgres (no psql)
    pg_home = Path.home() / ".postgres"
    pg_bin = pg_home / "bin"
    pg_ctl_path = pg_bin / "pg_ctl"

    if pg_ctl_path.exists() and pg_ctl_path.is_file():
        # Add to PATH for subsequent operations
        os.environ['PATH'] = f"{pg_bin}:{os.environ.get('PATH', '')}"
        return True

    return False


def install_postgresql(installer_dir):
    """Install and configure PostgreSQL using the shell script"""
    print_header("Installing PostgreSQL")

    postgres_script = installer_dir / "install_postgres.sh"

    if not postgres_script.exists():
        print_error(f"PostgreSQL installer script not found: {postgres_script}")
        return False

    # Make the script executable
    postgres_script.chmod(postgres_script.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    print_info("Running PostgreSQL installation script...")

    try:
        # Run the script interactively so user can see output
        result = subprocess.run(
            ['bash', str(postgres_script)],
            cwd=installer_dir
        )

        if result.returncode == 0:
            print_success("PostgreSQL installation completed")
            return True
        else:
            print_error("PostgreSQL installation script failed")
            return False

    except Exception as e:
        print_error(f"Failed to run PostgreSQL installer: {e}")
        return False


def display_summary(app_dir):
    """Display installation summary"""
    print_header("Installation Complete")

    print(f"{Colors.OKGREEN}The Cable Network ISP Data Lakehouse has been installed successfully.{Colors.ENDC}\n")

    print(f"{Colors.BOLD}To start the application:{Colors.ENDC}")
    print(f"  cd {app_dir}")
    print(f"  python start.py\n")

    print(f"{Colors.BOLD}Services will be available at:{Colors.ENDC}")
    print(f"  Frontend: http://localhost:8100")
    print(f"  Backend:  http://localhost:8000\n")

    print(f"{Colors.BOLD}Additional options:{Colors.ENDC}")
    print(f"  --skip-postgres   Skip PostgreSQL installation")
    print(f"  --postgres-only   Only install/configure PostgreSQL\n")


def get_installer_dir():
    """
    Get the installer directory, handling both script execution and Jupyter notebook environments.
    In Jupyter notebooks, __file__ is not defined, so we fall back to the current working directory.
    """
    try:
        # Works when run as a script
        return Path(__file__).parent.resolve()
    except NameError:
        # Running in Jupyter notebook or interactive Python - use current working directory
        cwd = Path(os.getcwd()).resolve()

        # Check if we're in the installer directory
        if cwd.name == 'installer':
            return cwd

        # Check if installer exists as a subdirectory
        installer_subdir = cwd / 'installer'
        if installer_subdir.exists():
            return installer_subdir

        # Otherwise assume we're in the project root and installer is a sibling consideration
        # Just use current directory and let validation catch issues
        return cwd


def is_interactive_environment():
    """Check if running in IPython/Jupyter environment where sys.exit() causes issues"""
    try:
        # Check for IPython
        get_ipython()
        return True
    except NameError:
        pass

    # Check for common Jupyter/IPython indicators
    if 'IPython' in sys.modules or 'ipykernel' in sys.modules:
        return True

    return False


def safe_exit(code):
    """Exit safely, avoiding SystemExit exceptions in interactive environments"""
    if is_interactive_environment():
        # In IPython/Jupyter, don't call sys.exit() as it raises an exception
        if code != 0:
            print(f"{Colors.FAIL}Installation failed with code {code}{Colors.ENDC}")
        # Just return - the script will end naturally
        return
    else:
        sys.exit(code)


def main():
    """Main installation flow"""
    print_header("Cable Network ISP Data Lakehouse - Installer")

    # Parse command line arguments
    skip_postgres = '--skip-postgres' in sys.argv
    postgres_only = '--postgres-only' in sys.argv

    # Determine paths - handles both script and Jupyter notebook execution
    installer_dir = get_installer_dir()
    # Application should be in sibling directory application
    app_dir = installer_dir.parent / "application"

    if not app_dir.exists():
        print_error(f"Application directory not found: {app_dir}")
        print_info("Expected directory structure:")
        print_info("  installer/install.py  (this script)")
        print_info("  application/          (application files)")
        safe_exit(1)
        return 1

    print_info(f"Installer directory: {installer_dir}")
    print_info(f"Application directory: {app_dir}")

    # PostgreSQL only mode
    if postgres_only:
        print_info("Running PostgreSQL installation only...")
        if not install_postgresql(installer_dir):
            print_error("PostgreSQL installation failed")
            safe_exit(1)
            return 1
        print_success("PostgreSQL installation completed successfully!")
        return 0

    # Check prerequisites
    if not check_prerequisites():
        print_error("\nPrerequisite checks failed. Please install missing dependencies.")
        safe_exit(1)
        return 1

    print_success("All prerequisites satisfied")

    # Install PostgreSQL if not skipped and not already installed
    if not skip_postgres:
        if check_postgres_installed():
            print_info("PostgreSQL is already installed")
        else:
            print_info("PostgreSQL not found. Installing...")
            if not install_postgresql(installer_dir):
                print_warning("PostgreSQL installation failed. You can install it manually later.")
                print_warning("Run: python install.py --postgres-only")
    else:
        print_info("Skipping PostgreSQL installation (--skip-postgres)")

    # Install frontend dependencies
    if not install_frontend_dependencies(app_dir):
        print_error("Frontend installation failed")
        safe_exit(1)
        return 1

    # Install backend dependencies
    if not install_backend_dependencies(app_dir):
        print_error("Backend installation failed")
        safe_exit(1)
        return 1

    # Build frontend (optional, non-fatal)
    build_frontend(app_dir)

    # Display summary
    display_summary(app_dir)

    print_success("Installation completed successfully!")
    return 0


if __name__ == '__main__':
    try:
        result = main()
        if not is_interactive_environment():
            sys.exit(result)
    except KeyboardInterrupt:
        print(f"\n{Colors.WARNING}Installation cancelled{Colors.ENDC}")
        if not is_interactive_environment():
            sys.exit(1)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        if not is_interactive_environment():
            sys.exit(1)
