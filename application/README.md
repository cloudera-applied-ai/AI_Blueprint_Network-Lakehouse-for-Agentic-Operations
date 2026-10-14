# Network Data Lakehouse - Application

AI-powered telecommunications NOC platform with real-time monitoring, anomaly detection, and autonomous self-healing capabilities.

## Quick Start

### Start Services

```bash
python start.py
```

This will start both:
- **Backend API** on http://localhost:8000
- **Frontend UI** on http://localhost:8100

### Stop Services

```bash
python stop.py
```

## First Time Setup

Before starting the application, run the installer:

```bash
cd ../installer
python install.py
```

## Configuration

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

Key settings:
- `ANTHROPIC_API_KEY` - Your Anthropic API key
- `DATABASE_URL` - PostgreSQL connection string

## Architecture

- **Frontend**: React 19 + TypeScript + Vite
- **Backend**: FastAPI + SQLAlchemy + PostgreSQL
- **AI**: LLM API via Anthropic SDK

## Logs

Logs are written to:
- `frontend.log` - Frontend server logs
- `backend.log` - Backend server logs
