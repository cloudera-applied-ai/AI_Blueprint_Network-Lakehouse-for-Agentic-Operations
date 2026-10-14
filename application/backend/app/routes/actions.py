"""Self-healing action endpoints"""
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from typing import Optional
from ..config import settings
from ..database import get_db
from ..models import FiberNodeModel, SelfHealingActionModel
from ..schemas import ActionListResponse, GenerateActionsRequest
from ..generator import generate_auto_resolution_action as generate_self_healing_action
from . import safe_error_response, logger

router = APIRouter(prefix=settings.API_V1_STR, tags=["actions"])


@router.post("/generate/actions", response_model=dict)
def generate_actions_endpoint(
    request: GenerateActionsRequest,
    regenerate: bool = Query(False, description="Clear existing actions before generating new ones"),
    db: Session = Depends(get_db),
):
    """Generate self-healing actions"""
    try:
        if regenerate:
            db.execute(SelfHealingActionModel.__table__.delete())
            db.commit()

        query = select(FiberNodeModel.node_id)
        result = db.execute(query)
        node_ids = [row[0] for row in result.all()]

        if not node_ids:
            raise HTTPException(status_code=400, detail="No nodes found. Generate nodes first.")

        alert_ids = request.alert_ids if request.alert_ids else []

        max_id_result = db.execute(select(func.max(SelfHealingActionModel.id))).scalar()
        next_id = (max_id_result or 0) + 1

        action_batch = []
        for i in range(request.count):
            node_id = node_ids[i % len(node_ids)]
            alert_id = alert_ids[i % len(alert_ids)] if alert_ids else None
            action_data = generate_self_healing_action(node_id, alert_id)
            action_data['id'] = next_id + i
            action_batch.append(action_data)

        if action_batch:
            insert_stmt = pg_insert(SelfHealingActionModel.__table__).values(action_batch)
            insert_stmt = insert_stmt.on_conflict_do_nothing(index_elements=['id'])
            db.execute(insert_stmt)
            db.commit()

        return {
            "status": "success",
            "message": f"Generated {request.count} actions",
            "count": request.count,
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=safe_error_response(e, "action generation"))


@router.get("/actions", response_model=ActionListResponse)
def get_actions(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=10000, description="Number of records to return (max 10000)"),
    node_id: Optional[str] = Query(None),
    action_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    since_minutes: Optional[int] = Query(None, ge=1, le=1440, description="Only return actions from last N minutes"),
    db: Session = Depends(get_db),
):
    """Get self-healing actions with pagination and filtering"""
    query = select(SelfHealingActionModel)

    if node_id:
        query = query.where(SelfHealingActionModel.node_id == node_id)
    if action_type:
        query = query.where(SelfHealingActionModel.action_type == action_type)
    if status:
        query = query.where(SelfHealingActionModel.status == status)
    if since_minutes:
        cutoff_time = datetime.now() - timedelta(minutes=since_minutes)
        query = query.where(SelfHealingActionModel.start_time >= cutoff_time)

    query = query.order_by(SelfHealingActionModel.start_time.desc())

    count_query = select(func.count()).select_from(query.alias())
    total = db.execute(count_query).scalar()

    query = query.offset(skip).limit(limit)
    actions = db.execute(query).scalars().all()

    return {
        "total": total,
        "page": skip // limit + 1,
        "page_size": limit,
        "items": actions,
    }


@router.get("/actions/status-summary")
def get_action_status_summary(db: Session = Depends(get_db)):
    """Get summary of action statuses"""
    query = select(
        SelfHealingActionModel.status,
        func.count(SelfHealingActionModel.id)
    ).group_by(SelfHealingActionModel.status)

    results = db.execute(query).all()
    return {
        "status_counts": {row[0]: row[1] for row in results if row[0]},
        "total": sum(row[1] for row in results),
    }


@router.post("/actions/cleanup")
def cleanup_old_actions(
    older_than_hours: int = Query(24, ge=1, le=720, description="Delete actions older than N hours"),
    status: Optional[str] = Query(None, description="Only cleanup actions with this status"),
    db: Session = Depends(get_db),
):
    """Clean up old self-healing actions in batches to avoid long table locks"""
    try:
        cutoff_time = datetime.now() - timedelta(hours=older_than_hours)
        deleted_count = 0
        batch_size = 5000

        while True:
            # Find IDs to delete in this batch
            id_subq = select(SelfHealingActionModel.id).where(
                SelfHealingActionModel.start_time < cutoff_time
            )
            if status:
                id_subq = id_subq.where(SelfHealingActionModel.status == status)
            id_subq = id_subq.limit(batch_size)

            delete_query = SelfHealingActionModel.__table__.delete().where(
                SelfHealingActionModel.id.in_(id_subq)
            )
            result = db.execute(delete_query)
            db.commit()
            batch_deleted = result.rowcount
            deleted_count += batch_deleted

            if batch_deleted < batch_size:
                break

        return {
            "status": "success",
            "message": f"Deleted {deleted_count} actions older than {older_than_hours} hours",
            "deleted_count": deleted_count,
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=safe_error_response(e, "action cleanup"))
