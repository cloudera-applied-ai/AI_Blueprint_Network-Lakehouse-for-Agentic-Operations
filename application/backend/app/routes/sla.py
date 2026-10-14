"""SLA Management endpoints - configuration, status, and breach tracking"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from typing import Optional
from datetime import datetime, timedelta
from ..config import settings
from ..database import get_db
from ..models import FiberNodeModel, KPIMetricsModel, AlertModel, SLAConfigModel, SLABreachModel
from ..schemas import SLAConfig, SLAConfigCreate, SLAConfigUpdate, SLABreach, SLABreachListResponse, SLAStatusResponse
from . import safe_error_response, logger

router = APIRouter(prefix=settings.API_V1_STR, tags=["sla"])


# ===== SLA MANAGEMENT ENDPOINTS =====

@router.get("/sla/config", response_model=SLAConfig)
def get_sla_config(db: Session = Depends(get_db)):
    """
    Get current SLA configuration.
    Returns default configuration if none exists.
    """
    query = select(SLAConfigModel).where(SLAConfigModel.id == 1)
    result = db.execute(query)
    config = result.scalar_one_or_none()

    if not config:
        # Create and persist default configuration
        config = SLAConfigModel(
            id=1,
            config_key="default",
            uptime_target_percent=99.9,
            max_outage_duration_minutes=30,
            max_monthly_downtime_minutes=43,
            max_latency_ms=50.0,
            latency_p95_target_ms=30.0,
            latency_p99_target_ms=100.0,
            min_ds_snr_db=33.0,
            min_us_snr_db=25.0,
            max_packet_loss_percent=0.5,
            min_throughput_mbps=100.0,
            max_fec_uncorrected_rate=0.01,
            critical_response_minutes=15,
            warning_response_minutes=60,
            resolution_target_hours=4,
            revenue_per_subscriber_per_hour=0.50,
            cost_per_outage_minute=1000.0,
            sla_breach_penalty_percent=10.0,
            warning_threshold_percent=90.0,
            critical_threshold_percent=95.0,
        )
        db.add(config)
        db.commit()
        db.refresh(config)

    return config


@router.post("/sla/config", response_model=SLAConfig)
def create_sla_config(config_data: SLAConfigCreate, db: Session = Depends(get_db)):
    """
    Create or replace SLA configuration.
    Only one config can exist (id=1).
    """
    # Delete existing config if any
    db.execute(SLAConfigModel.__table__.delete())

    # Create new config with required config_key
    new_config = SLAConfigModel(
        id=1,
        config_key="default",
        **config_data.model_dump()
    )
    db.add(new_config)
    db.commit()
    db.refresh(new_config)

    return new_config


@router.patch("/sla/config", response_model=SLAConfig)
def update_sla_config(config_update: SLAConfigUpdate, db: Session = Depends(get_db)):
    """
    Update SLA configuration with partial data.
    Creates default config if none exists.
    """
    query = select(SLAConfigModel).where(SLAConfigModel.id == 1)
    config = db.execute(query).scalar_one_or_none()

    if not config:
        # Create default config first with required config_key
        config = SLAConfigModel(id=1, config_key="default")
        db.add(config)

    # Update only provided fields
    update_data = config_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(config, field, value)

    config.updated_at = datetime.now()
    db.commit()
    db.refresh(config)

    return config


@router.get("/sla/status", response_model=SLAStatusResponse)
def get_sla_status(db: Session = Depends(get_db)):
    """
    Get current SLA compliance status.
    Calculates real-time metrics against SLA targets.
    """
    # Get SLA config (create default if needed)
    config_query = select(SLAConfigModel).where(SLAConfigModel.id == 1)
    config = db.execute(config_query).scalar_one_or_none()

    if not config:
        # Create and persist default configuration
        config = SLAConfigModel(
            id=1,
            config_key="default",
            uptime_target_percent=99.9,
            max_outage_duration_minutes=30,
            max_monthly_downtime_minutes=43,
            max_latency_ms=50.0,
            latency_p95_target_ms=30.0,
            latency_p99_target_ms=100.0,
            min_ds_snr_db=33.0,
            min_us_snr_db=25.0,
            max_packet_loss_percent=0.5,
            min_throughput_mbps=100.0,
            max_fec_uncorrected_rate=0.01,
            critical_response_minutes=15,
            warning_response_minutes=60,
            resolution_target_hours=4,
            revenue_per_subscriber_per_hour=0.50,
            cost_per_outage_minute=1000.0,
            sla_breach_penalty_percent=10.0,
            warning_threshold_percent=90.0,
            critical_threshold_percent=95.0,
        )
        db.add(config)
        db.commit()
        db.refresh(config)

    # Calculate current metrics (last 24 hours)
    cutoff_time = datetime.now() - timedelta(hours=24)
    month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Get node uptime (nodes with status != 'outage')
    total_nodes = db.execute(select(func.count(FiberNodeModel.id))).scalar() or 1
    healthy_nodes = db.execute(
        select(func.count(FiberNodeModel.id)).where(FiberNodeModel.status != 'OUTAGE')
    ).scalar() or 0
    current_uptime = (healthy_nodes / total_nodes) * 100

    # Calculate monthly downtime
    outage_nodes = total_nodes - healthy_nodes
    days_elapsed = (datetime.now() - month_start).days + 1
    monthly_downtime_minutes = (100 - current_uptime) / 100 * days_elapsed * 24 * 60

    # Get average KPI metrics from recent data
    kpi_stats = db.execute(
        select(
            func.avg(KPIMetricsModel.latency_ms),
            func.avg(KPIMetricsModel.ds_snr_db),
            func.avg(KPIMetricsModel.packet_loss_percent)
        ).where(KPIMetricsModel.timestamp >= cutoff_time)
    ).first()

    current_latency = float(kpi_stats[0]) if kpi_stats[0] else 25.0
    current_ds_snr = float(kpi_stats[1]) if kpi_stats[1] else 38.0
    current_packet_loss = float(kpi_stats[2]) if kpi_stats[2] else 1.5

    # Count active (unresolved) breaches
    active_breaches = db.execute(
        select(func.count(SLABreachModel.id)).where(
            SLABreachModel.resolved == False
        )
    ).scalar() or 0

    # Count warning alerts
    warning_alerts = db.execute(
        select(func.count(AlertModel.id)).where(
            AlertModel.severity == 'WARNING',
            AlertModel.status == 'ACTIVE',
            AlertModel.timestamp >= cutoff_time
        )
    ).scalar() or 0

    # Count breaches this month
    breaches_this_month = db.execute(
        select(func.count(SLABreachModel.id)).where(
            SLABreachModel.breach_start >= month_start
        )
    ).scalar() or 0

    # Calculate total penalty exposure
    penalty_per_breach = config.sla_breach_penalty_percent * 1000  # Estimated base
    total_penalty_exposure = breaches_this_month * penalty_per_breach

    # Calculate status
    uptime_compliant = current_uptime >= config.uptime_target_percent
    latency_compliant = current_latency <= config.max_latency_ms

    if uptime_compliant and latency_compliant and active_breaches == 0:
        status = "healthy"
    elif active_breaches > 0 or not uptime_compliant:
        status = "breach"
    else:
        status = "warning"

    return SLAStatusResponse(
        config=config,
        current_uptime_percent=round(current_uptime, 3),
        monthly_downtime_minutes=round(monthly_downtime_minutes, 2),
        current_latency_avg_ms=round(current_latency, 2),
        current_ds_snr_avg=round(current_ds_snr, 2),
        current_us_snr_avg=0.0,
        active_breaches=active_breaches,
        warning_alerts=warning_alerts,
        breaches_this_month=breaches_this_month,
        total_penalty_exposure=round(total_penalty_exposure, 2),
        status=status,
    )


@router.get("/sla/breaches", response_model=SLABreachListResponse)
def get_sla_breaches(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[str] = Query(None, description="Filter by status: active, resolved, acknowledged"),
    breach_type: Optional[str] = Query(None, description="Filter by type: uptime, latency, quality, response"),
    db: Session = Depends(get_db),
):
    """
    Get SLA breach history with filtering.
    """
    query = select(SLABreachModel)

    if status:
        query = query.where(SLABreachModel.status == status)
    if breach_type:
        query = query.where(SLABreachModel.breach_type == breach_type)

    query = query.order_by(SLABreachModel.breach_start.desc())

    # Get total count
    count_query = select(func.count()).select_from(query.alias())
    total = db.execute(count_query).scalar()

    # Get paginated results
    query = query.offset(skip).limit(limit)
    breaches = db.execute(query).scalars().all()

    return SLABreachListResponse(
        total=total,
        page=skip // limit + 1,
        page_size=limit,
        items=breaches,
    )


@router.post("/sla/breaches/{breach_id}/acknowledge")
def acknowledge_sla_breach(breach_id: str, db: Session = Depends(get_db)):
    """
    Acknowledge an SLA breach.
    """
    query = select(SLABreachModel).where(SLABreachModel.breach_id == breach_id)
    breach = db.execute(query).scalar_one_or_none()

    if not breach:
        raise HTTPException(status_code=404, detail=f"Breach {breach_id} not found")

    breach.status = "acknowledged"
    breach.acknowledged_at = datetime.now()
    db.commit()

    return {"message": f"Breach {breach_id} acknowledged", "status": "acknowledged"}


@router.post("/sla/breaches/{breach_id}/resolve")
def resolve_sla_breach(breach_id: str, db: Session = Depends(get_db)):
    """
    Resolve an SLA breach.
    """
    query = select(SLABreachModel).where(SLABreachModel.breach_id == breach_id)
    breach = db.execute(query).scalar_one_or_none()

    if not breach:
        raise HTTPException(status_code=404, detail=f"Breach {breach_id} not found")

    breach.status = "resolved"
    breach.resolved_at = datetime.now()
    if breach.started_at:
        breach.duration_minutes = (datetime.now() - breach.started_at).total_seconds() / 60
    db.commit()

    return {"message": f"Breach {breach_id} resolved", "status": "resolved"}
