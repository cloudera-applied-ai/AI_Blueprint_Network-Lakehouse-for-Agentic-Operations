"""Main FastAPI application - thin orchestrator that includes all route modules"""
import fcntl
import os
import logging
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import select
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from .config import settings
from .database import get_db, init_db, SessionLocal
from .models import LLMConfigModel
from .routes import app_state, limiter
from .auth import require_api_key

# File lock to ensure only one worker runs background tasks (prevents deadlocks)
_bg_lock_file = None

# Configure logging
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="Backend data generator for Network Data Lakehouse - NiFi Integration",
)

# Attach rate limiter to app
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware
# In CML environments the reverse proxy already injects Access-Control-Allow-Origin
# headers (reflecting the requesting *.cloudera.site origin).  Adding our own on top
# creates a duplicate-value header that browsers reject, so we skip the middleware.
# Outside CML we use allow_origin_regex so that any *.cloudera.site subdomain plus
# localhost (for development) is accepted.
_is_cml = bool(os.getenv('CDSW_PROJECT') or os.getenv('CDSW_APP_PORT') or os.getenv('CDSW_READONLY_PORT'))
if not _is_cml:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[],
        allow_origin_regex=settings.CORS_ORIGIN_REGEX,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# ===== INCLUDE ROUTE MODULES =====
from .routes.health import router as health_router
from .routes.system import router as system_router
from .routes.nodes import router as nodes_router
from .routes.headends import router as headends_router
from .routes.kpis import router as kpis_router
from .routes.alerts import router as alerts_router
from .routes.actions import router as actions_router
from .routes.stats import router as stats_router
from .routes.weather import router as weather_router
from .routes.generator import router as generator_router
from .routes.ai_optimization import router as ai_optimization_router
from .routes.retention import router as retention_router
from .routes.slack import router as slack_router
from .routes.llm import router as llm_router
from .routes.cloudera import router as cloudera_router
from .routes.equipment import router as equipment_router
from .routes.core_network import router as core_network_router
from .routes.ai import router as ai_router
from .routes.sla import router as sla_router
from .routes.financial import router as financial_router
from .routes.simulation import router as simulation_router
from .routes.capacity_planning import router as capacity_planning_router
from .routes.executive import router as executive_router
from .routes.config_management import router as config_management_router
from .routes.customers import router as customers_router

# Include all routers - health is public, all others require API key
_auth = [Depends(require_api_key)]

app.include_router(health_router)  # public – no auth
app.include_router(system_router, dependencies=_auth)
app.include_router(nodes_router, dependencies=_auth)
app.include_router(headends_router, dependencies=_auth)
app.include_router(kpis_router, dependencies=_auth)
app.include_router(alerts_router, dependencies=_auth)
app.include_router(actions_router, dependencies=_auth)
app.include_router(stats_router, dependencies=_auth)
app.include_router(weather_router, dependencies=_auth)
app.include_router(generator_router, dependencies=_auth)
app.include_router(ai_optimization_router, dependencies=_auth)
app.include_router(retention_router, dependencies=_auth)
app.include_router(slack_router, dependencies=_auth)
app.include_router(llm_router, dependencies=_auth)
app.include_router(cloudera_router, dependencies=_auth)
app.include_router(equipment_router, dependencies=_auth)
app.include_router(core_network_router, dependencies=_auth)
app.include_router(ai_router, dependencies=_auth)
app.include_router(sla_router, dependencies=_auth)
app.include_router(financial_router, dependencies=_auth)
app.include_router(simulation_router, dependencies=_auth)
app.include_router(capacity_planning_router, dependencies=_auth)
app.include_router(executive_router, dependencies=_auth)
app.include_router(config_management_router, dependencies=_auth)
app.include_router(customers_router, dependencies=_auth)

# Include Agent Studio router
from .agent_studio.router import router as agent_studio_router
app.include_router(agent_studio_router, dependencies=_auth)

# Packet-capture analysis + edge anomaly flow
from .routes.pcap import router as pcap_router
from .routes.edge import router as edge_router
app.include_router(pcap_router, dependencies=_auth)
app.include_router(edge_router, dependencies=_auth)


# ===== STARTUP / SHUTDOWN =====

def _auto_enable_llm_config(db: Session) -> bool:
    """
    Auto-enable LLM configuration if valid credentials exist in the database.
    Returns True if LLM was auto-enabled.
    """
    query = select(LLMConfigModel).where(LLMConfigModel.id == 1)
    result = db.execute(query)
    config = result.scalar_one_or_none()

    if not config:
        print("No LLM configuration found - configure via API or UI")
        return False

    if config.enabled:
        print(f"LLM already enabled: provider={config.provider}")
        return True

    provider = config.provider
    has_api_key = bool(config.api_key)
    has_jwt_token = bool(config.jwt_token)
    has_endpoint = bool(config.endpoint_url)

    can_enable = False
    if provider in ["openai", "anthropic"]:
        can_enable = has_api_key
    elif provider in ["cloudera", "custom"]:
        can_enable = (has_api_key or has_jwt_token) and has_endpoint
    elif provider == "ollama":
        can_enable = has_endpoint  # Ollama runs locally without auth
    else:
        can_enable = has_api_key or has_jwt_token

    if can_enable:
        try:
            config.enabled = True
            db.commit()
            print(f"LLM auto-enabled at startup: provider={provider}")
            return True
        except Exception as e:
            print(f"Failed to auto-enable LLM: {e}")
            db.rollback()
            return False
    else:
        print(f"LLM config exists but missing credentials (provider={provider}) - configure via API")
        return False


def _try_acquire_bg_lock():
    """Try to become the background task leader using a file lock.

    With multiple uvicorn workers, each worker runs startup_event().
    Only one worker should run background tasks to avoid deadlocks
    from concurrent updates to the same database rows.
    Returns the lock file handle (keep open to hold lock) or None.
    """
    try:
        fh = open('/tmp/cable_network_bg_leader.lock', 'w')
        fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fh.write(str(os.getpid()))
        fh.flush()
        return fh
    except (IOError, OSError):
        return None


@app.on_event("startup")
async def startup_event():
    """Initialize database and start background tasks on startup"""
    global _bg_lock_file

    # Dispose inherited connection pool so each worker starts fresh.
    # uvicorn uses "spawn" context, but this is a safety net against
    # stale connections from a previous worker occupying this process slot.
    from .database import engine
    engine.dispose()

    init_db()
    print(f"{settings.PROJECT_NAME} started successfully")
    print(f"Database: {settings.DATABASE_URL}")
    print(f"API docs: http://localhost:8000/docs")

    # Auto-enable LLM if valid credentials exist in database
    db = SessionLocal()
    try:
        _auto_enable_llm_config(db)
    finally:
        db.close()

    # Only one worker should run background tasks to prevent deadlocks
    _bg_lock_file = _try_acquire_bg_lock()
    if _bg_lock_file:
        print(f"Worker {os.getpid()} elected as background task leader")

        # Start background data generation
        from .background_tasks import background_generator
        await background_generator.start()

        # Start data retention service (rollup + cleanup)
        from .data_retention import data_retention_service
        await data_retention_service.start()
        print("Data retention service started (tiered rollup + cleanup)")

        # Start the edge staging poller (ingests edge-staged pcaps)
        from .edge import poller as edge_poller
        await edge_poller.start()
        print("Edge staging poller started")
    else:
        print(f"Worker {os.getpid()} is a request-only worker (background tasks run on another worker)")

    # Mark startup as complete - frontend can now connect
    app_state.startup_complete = True
    print("Backend ready to accept connections")


@app.on_event("shutdown")
async def shutdown_event():
    """Stop background tasks and cleanup resources on shutdown"""
    global _bg_lock_file
    from .performance import shutdown_executor

    if _bg_lock_file:
        from .background_tasks import background_generator
        from .data_retention import data_retention_service
        from .edge import poller as edge_poller
        await background_generator.stop()
        await data_retention_service.stop()
        await edge_poller.stop()
        _bg_lock_file.close()
        _bg_lock_file = None

    shutdown_executor()
    print("Server shutdown complete")
