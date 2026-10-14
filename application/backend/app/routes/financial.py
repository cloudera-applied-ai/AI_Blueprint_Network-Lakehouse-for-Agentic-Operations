"""Financial impact endpoints - revenue, cost avoidance, and ROI metrics"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, func, case, Integer
from typing import Optional
from datetime import datetime, timedelta
from ..config import settings
from ..database import get_db
from ..models import (
    FiberNodeModel,
    AlertModel,
    SLABreachModel,
    FinancialImpactModel,
    FinancialSummaryModel,
    SLAConfigModel,
    SelfHealingActionModel,
)
from ..schemas import FinancialImpact, FinancialImpactListResponse, FinancialSummary
from . import safe_error_response, logger

router = APIRouter(prefix=settings.API_V1_STR, tags=["financial"])


# ===== FINANCIAL IMPACT ENDPOINTS =====

@router.get("/financial/impacts", response_model=FinancialImpactListResponse)
def get_financial_impacts(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    impact_type: Optional[str] = Query(None, description="Filter by type: revenue_loss, cost_avoidance, penalty, savings"),
    node_id: Optional[str] = Query(None, description="Filter by node ID"),
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
):
    """
    Get financial impact records with filtering.
    """
    query = select(FinancialImpactModel)

    if impact_type:
        query = query.where(FinancialImpactModel.impact_type == impact_type)
    if node_id:
        query = query.where(FinancialImpactModel.node_id == node_id)
    if start_time:
        query = query.where(FinancialImpactModel.event_timestamp >= start_time)
    if end_time:
        query = query.where(FinancialImpactModel.event_timestamp <= end_time)

    query = query.order_by(FinancialImpactModel.event_timestamp.desc())

    # Get total count
    count_query = select(func.count()).select_from(query.alias())
    total = db.execute(count_query).scalar()

    # Get paginated results
    query = query.offset(skip).limit(limit)
    impacts = db.execute(query).scalars().all()

    return FinancialImpactListResponse(
        total=total,
        page=skip // limit + 1,
        page_size=limit,
        items=impacts,
    )


@router.get("/financial/summary", response_model=FinancialSummary)
def get_financial_summary(
    period_days: int = Query(30, ge=1, le=365, description="Period in days for summary"),
    db: Session = Depends(get_db),
):
    """
    Get financial summary for a period.
    Calculates total impacts, cost avoidance, and ROI metrics.
    """
    cutoff_time = datetime.now() - timedelta(days=period_days)

    # Get SLA config for cost parameters
    config = db.execute(select(SLAConfigModel).where(SLAConfigModel.id == 1)).scalar_one_or_none()
    cost_per_outage_minute = config.cost_per_outage_minute if config else 1000.0
    revenue_per_user_per_hour = config.revenue_per_subscriber_per_hour if config else 0.50

    # === Consolidated query 1: Node counts (total + outage in one query) ===
    node_counts = db.execute(
        select(
            func.count(FiberNodeModel.id).label('total'),
            func.sum(case((FiberNodeModel.status == 'outage', 1), else_=0)).label('outage'),
        )
    ).one()
    total_nodes = node_counts.total or 1
    outage_nodes = node_counts.outage or 0
    healthy_nodes = total_nodes - outage_nodes

    users_affected = outage_nodes * 500
    revenue_at_risk = users_affected * revenue_per_user_per_hour * 24

    # === Consolidated query 2: Actions + alerts in period (3 queries → 1) ===
    action_counts = db.execute(
        select(
            func.count(SelfHealingActionModel.id).label('total'),
            func.sum(case(
                (SelfHealingActionModel.status == 'COMPLETED', 1), else_=0
            )).label('completed'),
        ).where(SelfHealingActionModel.start_time >= cutoff_time)
    ).one()
    total_actions = action_counts.total or 1
    successful_actions = action_counts.completed or 0

    minutes_saved = successful_actions * 30
    cost_avoidance = minutes_saved * cost_per_outage_minute

    outage_alerts = db.execute(
        select(func.count(AlertModel.id)).where(
            AlertModel.type == 'NODE_OUTAGE',
            AlertModel.timestamp >= cutoff_time
        )
    ).scalar() or 0

    total_outage_minutes = outage_alerts * 60
    actual_revenue_loss = total_outage_minutes * cost_per_outage_minute * 0.01

    # === Consolidated query 3: SLA breaches (total + warnings in one query) ===
    breach_counts = db.execute(
        select(
            func.count(SLABreachModel.id).label('total'),
            func.sum(case(
                (SLABreachModel.severity == 'warning', 1), else_=0
            )).label('warnings'),
        ).where(SLABreachModel.breach_start >= cutoff_time)
    ).one()
    breach_count = breach_counts.total or 0
    near_breaches = breach_counts.warnings or 0
    sla_penalties = breach_count * 5000

    uptime_percent = (healthy_nodes / total_nodes) * 100
    manual_interventions = total_actions - successful_actions

    return FinancialSummary(
        id=1,
        summary_id=f"summary-{period_days}d",
        period_type="daily" if period_days <= 1 else ("weekly" if period_days <= 7 else "monthly"),
        period_start=cutoff_time,
        period_end=datetime.now(),
        region=None,
        total_revenue_at_risk=round(revenue_at_risk, 2),
        actual_revenue_loss=round(actual_revenue_loss, 2),
        revenue_protected=round(cost_avoidance, 2),
        operational_costs=round(actual_revenue_loss * 0.1, 2),  # Estimated at 10% of losses
        sla_penalties=round(sla_penalties, 2),
        ai_savings=round(cost_avoidance * 0.8, 2),  # 80% attributed to AI
        total_incidents=outage_alerts,
        auto_resolved_incidents=successful_actions,
        manual_interventions=manual_interventions,
        avg_resolution_time_minutes=30.0,  # Default 30 minutes
        uptime_percent=round(uptime_percent, 2),
        sla_breaches=breach_count,
        near_breaches=near_breaches,
        created_at=datetime.now(),
    )
