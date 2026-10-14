# Network Data Lakehouse - Installer

This folder contains the automated installer for the Network Data Lakehouse application.

## Prerequisites

Before running the installer, ensure you have:

- **Python 3.8+** - For running the backend
- **Node.js 22+** - For the frontend (auto-installed via nvm if missing)
- **npm** - Comes with Node.js
- **PostgreSQL** - Database server (auto-installed if missing)

## Usage

Run the installer from this directory:

```bash
python install.py
```

The installer will automatically:

1. Check all prerequisites (install Node.js 22 via nvm if missing)
2. Install PostgreSQL if not already installed
3. Install npm dependencies for the frontend
4. Create a Python virtual environment for the backend
5. Install Python packages from requirements.txt
6. Build the frontend for production

No prompts or user input required.

## Directory Structure

```
installer/
  install.py      # This installer script
  README.md       # This file

application/   # Application files (sibling directory)
  start.py        # Start servers
  stop.py         # Stop servers
  src/            # Frontend source
  backend/        # Backend source
  ...
```

## After Installation

Navigate to the application directory and start the servers:

```bash
cd ../application
python start.py
```
