"""Edge data center anomaly flow endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..edge import engine, poller, scenarios, staging
from ..models import EdgeAnomalyExecutionModel, HeadendModel

router = APIRouter(prefix=settings.API_V1_STR, tags=["edge"])


class CreateEventBody(BaseModel):
    headend_id: str
    scenario_id: str
    pcap_source: str | None = None  # "bundled" | "synthesized"


def _execution_dict(row: EdgeAnomalyExecutionModel) -> dict:
    return {
        "execution_id": row.execution_id,
        "headend_id": row.headend_id,
        "headend_name": row.headend_name,
        "scenario_id": row.scenario_id,
        "status": row.status,
        "progress_percent": row.progress_percent,
        "pcap_source": row.pcap_source,
        "staging_backend": row.staging_backend,
        "staged_uri": row.staged_uri,
        "thoughts": row.thoughts or [],
        "edge_actions": row.edge_actions or [],
        "analysis_id": row.analysis_id,
        "error": row.error,
        "started_at": row.started_at.isoformat() if row.started_at else None,
        "completed_at": row.completed_at.isoformat() if row.completed_at else None,
    }


@router.get("/edge/scenarios")
def list_scenarios() -> list[dict]:
    return scenarios.scenario_list()


@router.get("/edge/staging/status")
def staging_status() -> dict:
    return staging.status()


@router.post("/edge/events", status_code=202)
def create_event(body: CreateEventBody, db: Session = Depends(get_db)) -> dict:
    headend = db.query(HeadendModel).filter(HeadendModel.headend_id == body.headend_id).first()
    if headend is None:
        raise HTTPException(status_code=404, detail=f"Unknown headend: {body.headend_id}")
    if body.scenario_id not in scenarios.SCENARIOS:
        raise HTTPException(status_code=400, detail=f"Unknown scenario: {body.scenario_id}")
    try:
        execution_id = engine.start(
            body.headend_id, headend.name or body.headend_id, body.scenario_id, body.pcap_source
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"execution_id": execution_id, "status": "running"}


@router.get("/edge/events")
def list_events(limit: int = 25, db: Session = Depends(get_db)) -> list[dict]:
    rows = (
        db.execute(
            select(EdgeAnomalyExecutionModel)
            .order_by(EdgeAnomalyExecutionModel.created_at.desc())
            .limit(min(limit, 100))
        )
        .scalars()
        .all()
    )
    return [_execution_dict(r) for r in rows]


@router.get("/edge/events/{execution_id}")
def get_event(execution_id: str, db: Session = Depends(get_db)) -> dict:
    row = db.query(EdgeAnomalyExecutionModel).filter_by(execution_id=execution_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Edge event not found")
    return _execution_dict(row)


@router.post("/edge/poll")
async def poll_now() -> dict:
    """Run one ingest cycle inline — instant analysis for live demos."""
    processed = await poller.poll_once()
    return {"processed": processed}
