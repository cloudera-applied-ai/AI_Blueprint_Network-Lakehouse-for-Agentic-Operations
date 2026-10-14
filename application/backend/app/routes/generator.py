"""Background generator control endpoints"""
from fastapi import APIRouter
from ..config import settings

router = APIRouter(prefix=settings.API_V1_STR, tags=["generator"])


@router.get("/generator/status")
def get_generator_status():
    """Get background data generator status"""
    from ..background_tasks import background_generator
    return background_generator.get_stats()


@router.post("/generator/start")
async def start_generator():
    """Start background data generator"""
    from ..background_tasks import background_generator
    await background_generator.start()
    return {"status": "started"}


@router.post("/generator/stop")
async def stop_generator():
    """Stop background data generator"""
    from ..background_tasks import background_generator
    await background_generator.stop()
    return {"status": "stopped"}
