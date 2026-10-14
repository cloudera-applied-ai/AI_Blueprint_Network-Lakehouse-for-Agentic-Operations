"""Alert endpoints - generate and query alerts"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from typing import Optional
from ..config import settings
from ..database import get_db
from ..models import FiberNodeModel, AlertModel
from ..schemas import AlertListResponse, GenerateAlertsRequest
from ..generator import generate_cable_alert as generate_alert
from . import safe_error_response, logger

router = APIRouter(prefix=settings.API_V1_STR, tags=["alerts"])


@router.post("/generate/alerts", response_model=dict)
def generate_alerts_endpoint(
    request: GenerateAlertsRequest,
    regenerate: bool = Query(False, description="Clear existing alerts before generating new ones"),
    db: Session = Depends(get_db),
):
    """Generate alerts for nodes"""
    try:
        if regenerate:
            db.execute(AlertModel.__table__.delete())
            db.commit()

        if request.node_ids:
            node_ids = request.node_ids
        else:
            query = select(FiberNodeModel.node_id)
            result = db.execute(query)
            node_ids = [row[0] for row in result.all()]

        if not node_ids:
            raise HTTPException(status_code=400, detail="No nodes found. Generate nodes first.")

        alert_batch = []
        for i in range(request.count):
            node_id = node_ids[i % len(node_ids)]
            alert_data = generate_alert(node_id)
            alert_data['id'] = i + 1
            alert_batch.append(alert_data)

        if alert_batch:
            db.execute(AlertModel.__table__.insert(), alert_batch)
            db.commit()

        return {
            "status": "success",
            "message": f"Generated {request.count} alerts",
            "count": request.count,
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=safe_error_response(e, "alert generation"))


@router.get("/alerts", response_model=AlertListResponse)
def get_alerts(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=10000, description="Number of records to return (max 10000)"),
    node_id: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    start_time: Optional[str] = Query(None, description="ISO format datetime to filter alerts from"),
    end_time: Optional[str] = Query(None, description="ISO format datetime to filter alerts until"),
    db: Session = Depends(get_db),
):
    """Get alerts with pagination and filtering"""
    query = select(AlertModel)

    if node_id:
        query = query.where(AlertModel.node_id == node_id)
    if severity:
        query = query.where(AlertModel.severity == severity)
    if status:
        query = query.where(AlertModel.status == status)
    if start_time:
        try:
            start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            query = query.where(AlertModel.timestamp >= start_dt)
        except ValueError:
            pass
    if end_time:
        try:
            end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            query = query.where(AlertModel.timestamp <= end_dt)
        except ValueError:
            pass

    query = query.order_by(AlertModel.timestamp.desc())

    count_query = select(func.count()).select_from(query.alias())
    total = db.execute(count_query).scalar()

    query = query.offset(skip).limit(limit)
    alerts = db.execute(query).scalars().all()

    return {
        "total": total,
        "page": skip // limit + 1,
        "page_size": limit,
        "items": alerts,
    }
