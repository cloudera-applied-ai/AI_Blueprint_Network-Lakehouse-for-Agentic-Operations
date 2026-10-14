"""Health and root endpoints"""
from datetime import datetime
from fastapi import APIRouter
from sqlalchemy import select, func
from ..config import settings
from ..database import SessionLocal
from ..models import FiberNodeModel
from . import app_state

router = APIRouter(tags=["health"])

# Cache the data-ready check so we don't query the DB on every health poll.
# Once True it stays True for the lifetime of this worker process.
_data_ready_cache = False


def _check_data_ready() -> bool:
    """Check if data is ready, using the background generator flag or a DB fallback.

    In multi-worker deployments only the leader worker runs background tasks and
    sets ``background_generator.data_ready``.  Non-leader workers never set the
    flag, so we fall back to a cheap DB query: if fiber_nodes exist the backend
    is functional and the frontend should be allowed to connect.
    """
    global _data_ready_cache
    if _data_ready_cache:
        return True

    # Fast path: background generator on leader worker already marked ready
    from ..background_tasks import background_generator
    if getattr(background_generator, 'data_ready', False):
        _data_ready_cache = True
        return True

    # Slow path (non-leader workers): check DB for existing node data.
    # This is a COUNT(*) on an indexed table — fast even with millions of rows.
    try:
        db = SessionLocal()
        try:
            count = db.execute(select(func.count(FiberNodeModel.node_id))).scalar()
            if count and count > 0:
                _data_ready_cache = True
                return True
        finally:
            db.close()
    except Exception:
        pass

    return False


@router.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "name": settings.PROJECT_NAME,
        "version": "1.0.0",
        "status": "running",
        "docs_url": "/docs",
        "endpoints": {
            "fiber_nodes": "/api/v1/nodes",
            "headends": "/api/v1/headends",
            "cmts": "/api/v1/cmts",
            "hubs": "/api/v1/hubs",
            "amplifiers": "/api/v1/amplifiers",
            "customers": "/api/v1/customers",
            "kpi_metrics": "/api/v1/kpis",
            "alerts": "/api/v1/alerts",
            "actions": "/api/v1/actions",
            "generate_nodes": "/api/v1/generate/nodes",
            "generate_kpis": "/api/v1/generate/kpis",
            "generate_alerts": "/api/v1/generate/alerts",
            "generate_actions": "/api/v1/generate/actions",
            "maintenance": "/api/v1/maintenance",
            "dark_noc": "/api/v1/dark-noc",
            "agent_studio": "/api/v1/agent-studio",
        },
    }


@router.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    data_ready = _check_data_ready()

    return {
        "status": "healthy" if app_state.startup_complete and data_ready else "starting",
        "ready": app_state.startup_complete and data_ready,
        "startup_complete": app_state.startup_complete,
        "data_ready": data_ready,
        "timestamp": datetime.now().isoformat()
    }
