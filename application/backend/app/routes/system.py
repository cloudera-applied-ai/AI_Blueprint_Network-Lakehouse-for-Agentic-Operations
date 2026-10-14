"""System control endpoints - pause/resume, status, settings"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from ..config import settings
from ..database import get_db
from ..models import SystemSettingsModel
from ..schemas import SystemSettings, SystemSettingsCreate
from . import app_state, safe_error_response, logger

router = APIRouter(prefix=settings.API_V1_STR, tags=["system"])


@router.get("/system/status")
async def get_system_status():
    """Get overall system status including data generation and LLM states"""
    from ..background_tasks import background_generator

    return {
        "data_generation": {
            "running": background_generator.running,
            "paused": background_generator.is_paused(),
            "stats": background_generator.get_stats()
        },
        "llm": {
            "paused": app_state.llm_paused
        },
        "timestamp": datetime.now().isoformat()
    }


@router.post("/system/pause")
async def pause_system(
    data_generation: bool = Query(True, description="Pause data generation"),
    llm: bool = Query(True, description="Pause LLM queries")
):
    """Pause data generation and/or LLM queries to reduce system load"""
    from ..background_tasks import background_generator

    results = {}

    if data_generation:
        background_generator.pause()
        results["data_generation"] = "paused"

    if llm:
        app_state.llm_paused = True
        results["llm"] = "paused"

    print(f"⏸️ System paused: {results}")
    return {
        "status": "paused",
        "paused": results,
        "timestamp": datetime.now().isoformat()
    }


@router.post("/system/resume")
async def resume_system(
    data_generation: bool = Query(True, description="Resume data generation"),
    llm: bool = Query(True, description="Resume LLM queries")
):
    """Resume data generation and/or LLM queries"""
    from ..background_tasks import background_generator

    results = {}

    if data_generation:
        background_generator.resume()
        results["data_generation"] = "resumed"

    if llm:
        app_state.llm_paused = False
        results["llm"] = "resumed"

    print(f"▶️ System resumed: {results}")
    return {
        "status": "resumed",
        "resumed": results,
        "timestamp": datetime.now().isoformat()
    }


@router.get("/system/llm-paused")
async def is_llm_paused():
    """Check if LLM queries are paused (used by frontend to skip LLM calls)"""
    return {"paused": app_state.llm_paused}


# ===== SYSTEM SETTINGS =====

@router.get("/system/settings", response_model=SystemSettings)
def get_system_settings(db: Session = Depends(get_db)):
    """Get system settings"""
    from sqlalchemy import select
    query = select(SystemSettingsModel).where(SystemSettingsModel.id == 1)
    result = db.execute(query)
    settings_obj = result.scalar_one_or_none()

    if not settings_obj:
        # Return default settings
        return SystemSettings(
            id=1,
            ai_enabled=False,
            auto_healing_enabled=False,
            data_generation_enabled=True,
            refresh_interval_seconds=5,
            theme="dark",
        )

    return settings_obj


@router.post("/system/settings", response_model=SystemSettings)
def create_or_update_system_settings(
    settings_data: SystemSettingsCreate,
    db: Session = Depends(get_db),
):
    """Create or update system settings"""
    from sqlalchemy import select
    try:
        query = select(SystemSettingsModel).where(SystemSettingsModel.id == 1)
        result = db.execute(query)
        existing = result.scalar_one_or_none()

        if existing:
            # Update existing settings
            update_data = settings_data.model_dump(exclude_unset=True)
            for key, value in update_data.items():
                if hasattr(existing, key):
                    setattr(existing, key, value)
            db.commit()
            db.refresh(existing)
            return existing
        else:
            # Create new settings
            new_settings = SystemSettingsModel(id=1, **settings_data.model_dump())
            db.add(new_settings)
            db.commit()
            db.refresh(new_settings)
            return new_settings

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=safe_error_response(e, "system settings update"))
