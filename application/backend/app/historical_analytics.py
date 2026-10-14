"""
Historical Analytics Service - Queries aggregated KPI tables for efficient trend analysis.

This module provides functions to query historical data from the tiered aggregation tables:
- KPIMetrics1MinModel - 1-min aggregates (use for period_hours <= 6)
- KPIMetrics5MinModel - 5-min aggregates (use for period_hours <= 24)
- KPIMetricsHourlyModel - Hourly aggregates (use for period_hours <= 168 / 7 days)
- KPIMetricsDailyModel - Daily aggregates (use for longer periods)

These tables provide much faster queries than raw KPI data for trend analysis and reporting.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc

from .models import (
    KPIMetricsModel,
    KPIMetrics1MinModel,
    KPIMetrics5MinModel,
    KPIMetricsHourlyModel,
    KPIMetricsDailyModel,
    AlertModel,
    SelfHealingActionModel,
    FiberNodeModel,
    SLAConfigModel,
)


@dataclass
class KPITrendPoint:
    """Single point in a KPI trend time series"""
    timestamp: datetime
    ds_snr_db: float
    us_snr_db: float
    ds_power_level_dbmv: float
    latency_ms: float
    downstream_throughput_mbps: float
    packet_loss_percent: float
    active_modems: float
    node_cpu_utilization: float
    node_memory_utilization: float
    node_temperature: float
    sample_count: int


@dataclass
class PeriodComparison:
    """Comparison between current and previous period"""
    metric_name: str
    current_value: float
    previous_value: float
    change_percent: float
    trend: str  # 'improving', 'stable', 'declining'


def get_appropriate_kpi_model(period_hours: int):
    """
    Select the finest aggregated KPI table whose retention covers the requested
    period (retention is configured in config.py / env):

    - 1-min aggregates while period <= RETENTION_1MIN_HOURS (default 6h)
    - 5-min aggregates while period <= RETENTION_5MIN_HOURS (default 12h)
    - hourly aggregates while period <= RETENTION_HOURLY_DAYS (default 3d)
    - daily aggregates otherwise
    """
    from .config import settings

    if period_hours <= settings.RETENTION_1MIN_HOURS:
        return KPIMetrics1MinModel
    elif period_hours <= settings.RETENTION_5MIN_HOURS:
        return KPIMetrics5MinModel
    elif period_hours <= settings.RETENTION_HOURLY_DAYS * 24:
        return KPIMetricsHourlyModel
    else:
        return KPIMetricsDailyModel


def get_kpi_trends(
    db: Session,
    period_hours: int = 24,
    node_id: Optional[str] = None,
    max_points: int = 100
) -> List[Dict[str, Any]]:
    """
    Get KPI trend data from the appropriate aggregated table.

    Returns time-series data points for charting.
    """
    cutoff_time = datetime.now() - timedelta(hours=period_hours)
    model = get_appropriate_kpi_model(period_hours)

    query = db.query(
        model.timestamp,
        func.avg(model.ds_snr_db).label('ds_snr_db'),
        func.avg(model.us_snr_db).label('us_snr_db'),
        func.avg(model.ds_power_level_dbmv).label('ds_power_level_dbmv'),
        func.avg(model.latency_ms).label('latency_ms'),
        func.avg(model.downstream_throughput_mbps).label('downstream_throughput_mbps'),
        func.avg(model.packet_loss_percent).label('packet_loss_percent'),
        func.avg(model.active_modems).label('active_modems'),
        func.avg(model.node_cpu_utilization).label('node_cpu_utilization'),
        func.avg(model.node_memory_utilization).label('node_memory_utilization'),
        func.avg(model.node_temperature).label('node_temperature'),
        func.sum(model.sample_count).label('sample_count'),
    ).filter(model.timestamp >= cutoff_time)

    if node_id:
        query = query.filter(model.node_id == node_id)

    # Group by timestamp bucket for network-wide trends
    query = query.group_by(model.timestamp).order_by(model.timestamp)

    # Limit to max_points
    results = query.limit(max_points).all()

    trend_data = []
    for row in results:
        trend_data.append({
            "timestamp": row.timestamp.isoformat() if row.timestamp else None,
            "ds_snr_db": round(float(row.ds_snr_db or 0), 2),
            "us_snr_db": round(float(row.us_snr_db or 0), 2),
            "ds_power_level_dbmv": round(float(row.ds_power_level_dbmv or 0), 2),
            "latency_ms": round(float(row.latency_ms or 0), 2),
            "downstream_throughput_mbps": round(float(row.downstream_throughput_mbps or 0), 2),
            "packet_loss_percent": round(float(row.packet_loss_percent or 0), 3),
            "active_modems": round(float(row.active_modems or 0), 0),
            "node_cpu_utilization": round(float(row.node_cpu_utilization or 0), 2),
            "node_memory_utilization": round(float(row.node_memory_utilization or 0), 2),
            "node_temperature": round(float(row.node_temperature or 0), 1),
            "sample_count": int(row.sample_count or 0),
        })

    return trend_data


def get_historical_kpi_averages(
    db: Session,
    period_hours: int = 24,
    node_id: Optional[str] = None
) -> Dict[str, float]:
    """
    Get average KPI values from historical data for the specified period.

    This is used for baseline calculations in simulations.
    """
    cutoff_time = datetime.now() - timedelta(hours=period_hours)
    model = get_appropriate_kpi_model(period_hours)

    query = db.query(
        func.avg(model.ds_snr_db).label('ds_snr_db'),
        func.avg(model.us_snr_db).label('us_snr_db'),
        func.avg(model.ds_power_level_dbmv).label('ds_power_level_dbmv'),
        func.avg(model.latency_ms).label('latency_ms'),
        func.avg(model.downstream_throughput_mbps).label('downstream_throughput_mbps'),
        func.avg(model.packet_loss_percent).label('packet_loss_percent'),
        func.avg(model.active_modems).label('active_modems'),
        func.avg(model.node_cpu_utilization).label('node_cpu_utilization'),
        func.avg(model.node_memory_utilization).label('node_memory_utilization'),
        func.avg(model.node_temperature).label('node_temperature'),
        func.sum(model.sample_count).label('total_samples'),
    ).filter(model.timestamp >= cutoff_time)

    if node_id:
        query = query.filter(model.node_id == node_id)

    result = query.first()

    if not result or result.total_samples == 0:
        # Fallback to raw KPIs if no aggregated data
        return get_fallback_kpi_averages(db, period_hours, node_id)

    return {
        "ds_snr_db": round(float(result.ds_snr_db or 38.0), 2),
        "us_snr_db": round(float(result.us_snr_db or 30.0), 2),
        "ds_power_level_dbmv": round(float(result.ds_power_level_dbmv or 0.0), 2),
        "latency_ms": round(float(result.latency_ms or 15.0), 2),
        "downstream_throughput_mbps": round(float(result.downstream_throughput_mbps or 500.0), 2),
        "packet_loss_percent": round(float(result.packet_loss_percent or 0.3), 3),
        "active_modems": round(float(result.active_modems or 200), 0),
        "node_cpu_utilization": round(float(result.node_cpu_utilization or 45.0), 2),
        "node_memory_utilization": round(float(result.node_memory_utilization or 55.0), 2),
        "node_temperature": round(float(result.node_temperature or 35.0), 1),
        "total_samples": int(result.total_samples or 0),
        "data_source": model.__tablename__,
    }


def get_fallback_kpi_averages(
    db: Session,
    period_hours: int = 24,
    node_id: Optional[str] = None
) -> Dict[str, float]:
    """Fallback to raw KPI data if no aggregated data available."""
    cutoff_time = datetime.now() - timedelta(hours=period_hours)

    query = db.query(
        func.avg(KPIMetricsModel.ds_snr_db).label('ds_snr_db'),
        func.avg(KPIMetricsModel.us_snr_db).label('us_snr_db'),
        func.avg(KPIMetricsModel.ds_power_level_dbmv).label('ds_power_level_dbmv'),
        func.avg(KPIMetricsModel.latency_ms).label('latency_ms'),
        func.avg(KPIMetricsModel.downstream_throughput_mbps).label('downstream_throughput_mbps'),
        func.avg(KPIMetricsModel.packet_loss_percent).label('packet_loss_percent'),
        func.avg(KPIMetricsModel.active_modems).label('active_modems'),
        func.avg(KPIMetricsModel.node_cpu_utilization).label('node_cpu_utilization'),
        func.avg(KPIMetricsModel.node_memory_utilization).label('node_memory_utilization'),
        func.avg(KPIMetricsModel.node_temperature).label('node_temperature'),
        func.count(KPIMetricsModel.id).label('total_samples'),
    ).filter(KPIMetricsModel.timestamp >= cutoff_time)

    if node_id:
        query = query.filter(KPIMetricsModel.node_id == node_id)

    result = query.first()

    return {
        "ds_snr_db": round(float(result.ds_snr_db or 38.0), 2),
        "us_snr_db": round(float(result.us_snr_db or 30.0), 2),
        "ds_power_level_dbmv": round(float(result.ds_power_level_dbmv or 0.0), 2),
        "latency_ms": round(float(result.latency_ms or 15.0), 2),
        "downstream_throughput_mbps": round(float(result.downstream_throughput_mbps or 500.0), 2),
        "packet_loss_percent": round(float(result.packet_loss_percent or 0.3), 3),
        "active_modems": round(float(result.active_modems or 200), 0),
        "node_cpu_utilization": round(float(result.node_cpu_utilization or 45.0), 2),
        "node_memory_utilization": round(float(result.node_memory_utilization or 55.0), 2),
        "node_temperature": round(float(result.node_temperature or 35.0), 1),
        "total_samples": int(result.total_samples or 0),
        "data_source": "kpi_metrics (raw)",
    }


def calculate_period_comparison(
    db: Session,
    period_hours: int = 24
) -> List[Dict[str, Any]]:
    """
    Calculate comparison between current period and the previous period of same length.

    Returns a list of metric comparisons with trend indicators.
    Falls back to raw KPI data if aggregated tables are empty.
    """
    now = datetime.now()
    current_cutoff = now - timedelta(hours=period_hours)
    previous_cutoff = now - timedelta(hours=period_hours * 2)

    model = get_appropriate_kpi_model(period_hours)

    # Current period averages
    current = db.query(
        func.avg(model.ds_snr_db).label('ds_snr_db'),
        func.avg(model.us_snr_db).label('us_snr_db'),
        func.avg(model.latency_ms).label('latency_ms'),
        func.avg(model.downstream_throughput_mbps).label('downstream_throughput_mbps'),
        func.avg(model.node_cpu_utilization).label('node_cpu_utilization'),
    ).filter(model.timestamp >= current_cutoff).first()

    # Check if we got any data - if not, fall back to raw KPIs
    if current is None or current.ds_snr_db is None:
        model = KPIMetricsModel  # Fall back to raw table
        current = db.query(
            func.avg(model.ds_snr_db).label('ds_snr_db'),
            func.avg(model.us_snr_db).label('us_snr_db'),
            func.avg(model.latency_ms).label('latency_ms'),
            func.avg(model.downstream_throughput_mbps).label('downstream_throughput_mbps'),
            func.avg(model.node_cpu_utilization).label('node_cpu_utilization'),
        ).filter(model.timestamp >= current_cutoff).first()

    # Previous period averages
    previous = db.query(
        func.avg(model.ds_snr_db).label('ds_snr_db'),
        func.avg(model.us_snr_db).label('us_snr_db'),
        func.avg(model.latency_ms).label('latency_ms'),
        func.avg(model.downstream_throughput_mbps).label('downstream_throughput_mbps'),
        func.avg(model.node_cpu_utilization).label('node_cpu_utilization'),
    ).filter(
        and_(model.timestamp >= previous_cutoff, model.timestamp < current_cutoff)
    ).first()

    comparisons = []

    def make_comparison(name: str, current_val: float, previous_val: float, higher_is_better: bool = True) -> Dict[str, Any]:
        if previous_val == 0:
            change_pct = 0
        else:
            change_pct = ((current_val - previous_val) / previous_val) * 100

        if abs(change_pct) < 2:
            trend = "stable"
        elif (change_pct > 0 and higher_is_better) or (change_pct < 0 and not higher_is_better):
            trend = "improving"
        else:
            trend = "declining"

        return {
            "metric_name": name,
            "current_value": round(current_val, 2),
            "previous_value": round(previous_val, 2),
            "change_percent": round(change_pct, 2),
            "trend": trend,
        }

    comparisons.append(make_comparison(
        "ds_snr_db",
        float(current.ds_snr_db or 0),
        float(previous.ds_snr_db or 0),
        higher_is_better=True
    ))
    comparisons.append(make_comparison(
        "us_snr_db",
        float(current.us_snr_db or 0),
        float(previous.us_snr_db or 0),
        higher_is_better=True
    ))
    comparisons.append(make_comparison(
        "latency_ms",
        float(current.latency_ms or 0),
        float(previous.latency_ms or 0),
        higher_is_better=False
    ))
    comparisons.append(make_comparison(
        "downstream_throughput_mbps",
        float(current.downstream_throughput_mbps or 0),
        float(previous.downstream_throughput_mbps or 0),
        higher_is_better=True
    ))
    comparisons.append(make_comparison(
        "node_cpu_utilization",
        float(current.node_cpu_utilization or 0),
        float(previous.node_cpu_utilization or 0),
        higher_is_better=False
    ))

    return comparisons


def get_historical_revenue_loss(
    db: Session,
    period_hours: int = 24
) -> Dict[str, float]:
    """
    Calculate actual revenue loss from alerts and outages in the period.

    Uses alert duration and impacted users to calculate real loss.
    Optimized to use SQL aggregation instead of loading all alerts into memory.
    """
    from sqlalchemy import case, extract

    cutoff_time = datetime.now() - timedelta(hours=period_hours)
    now = datetime.now()

    # Get SLA config for revenue calculations
    config = db.query(SLAConfigModel).filter(SLAConfigModel.id == 1).first()
    revenue_per_user_hour = config.revenue_per_subscriber_per_hour if config else 0.50
    cost_per_outage_minute = config.cost_per_outage_minute if config else 1000.0

    # Use SQL aggregation instead of loading all alerts
    # Calculate duration in minutes: (resolved_at or now) - timestamp
    duration_expr = case(
        (AlertModel.resolved_at != None,
         extract('epoch', AlertModel.resolved_at - AlertModel.timestamp) / 60),
        else_=extract('epoch', func.now() - AlertModel.timestamp) / 60
    )

    # Aggregate query for all metrics
    result = db.query(
        func.count(AlertModel.id).label('alert_count'),
        func.sum(case((AlertModel.severity == 'CRITICAL', 1), else_=0)).label('critical_count'),
        func.sum(
            func.coalesce(AlertModel.impacted_users, 0) * duration_expr
        ).label('total_user_minutes'),
        func.sum(
            case((AlertModel.severity == 'CRITICAL', duration_expr), else_=0)
        ).label('total_outage_minutes'),
    ).filter(
        AlertModel.timestamp >= cutoff_time
    ).first()

    alert_count = result.alert_count or 0
    critical_count = int(result.critical_count or 0)
    total_user_minutes = float(result.total_user_minutes or 0)
    total_outage_minutes = float(result.total_outage_minutes or 0)

    # Calculate revenue loss
    user_hours_lost = total_user_minutes / 60
    revenue_loss = user_hours_lost * revenue_per_user_hour
    outage_cost = total_outage_minutes * cost_per_outage_minute

    return {
        "revenue_loss": round(revenue_loss, 2),
        "outage_cost": round(outage_cost, 2),
        "total_loss": round(revenue_loss + outage_cost, 2),
        "total_alerts": alert_count,
        "critical_alerts": critical_count,
        "total_user_minutes_impacted": round(total_user_minutes, 0),
        "total_outage_minutes": round(total_outage_minutes, 0),
    }


def get_incident_statistics(
    db: Session,
    period_hours: int = 24
) -> Dict[str, Any]:
    """
    Get incident/resolution statistics from historical data.

    Returns actual MTTR, resolution times, and action effectiveness.
    Optimized to use SQL aggregation instead of loading all actions into memory.
    """
    from sqlalchemy import case, extract

    cutoff_time = datetime.now() - timedelta(hours=period_hours)

    # Use SQL aggregation instead of loading all actions
    # Duration in minutes for completed actions with both start and end times
    duration_expr = case(
        (and_(
            SelfHealingActionModel.status == 'COMPLETED',
            SelfHealingActionModel.end_time != None,
            SelfHealingActionModel.start_time != None
        ), extract('epoch', SelfHealingActionModel.end_time - SelfHealingActionModel.start_time) / 60),
        else_=None
    )

    result = db.query(
        func.count(SelfHealingActionModel.id).label('total_actions'),
        func.sum(case((SelfHealingActionModel.status == 'COMPLETED', 1), else_=0)).label('completed_count'),
        func.sum(case((SelfHealingActionModel.status == 'FAILED', 1), else_=0)).label('failed_count'),
        func.avg(duration_expr).label('avg_resolution_time'),
        func.min(duration_expr).label('min_resolution_time'),
        func.max(duration_expr).label('max_resolution_time'),
        func.avg(case(
            (SelfHealingActionModel.status == 'COMPLETED', SelfHealingActionModel.effectiveness_score),
            else_=None
        )).label('avg_effectiveness'),
    ).filter(
        SelfHealingActionModel.start_time >= cutoff_time
    ).first()

    total_actions = result.total_actions or 0
    completed_count = int(result.completed_count or 0)
    failed_count = int(result.failed_count or 0)
    pending_count = total_actions - completed_count - failed_count

    avg_resolution_time = float(result.avg_resolution_time) if result.avg_resolution_time else 30.0
    min_resolution_time = float(result.min_resolution_time) if result.min_resolution_time else 0.0
    max_resolution_time = float(result.max_resolution_time) if result.max_resolution_time else 60.0
    avg_effectiveness = float(result.avg_effectiveness) if result.avg_effectiveness else 0.85

    # Success rate
    success_rate = (completed_count / total_actions * 100) if total_actions > 0 else 0

    return {
        "total_actions": total_actions,
        "completed_actions": completed_count,
        "failed_actions": failed_count,
        "pending_actions": pending_count,
        "success_rate": round(success_rate, 2),
        "mttr_minutes": round(avg_resolution_time, 1),
        "min_resolution_time_minutes": round(min_resolution_time, 1),
        "max_resolution_time_minutes": round(max_resolution_time, 1),
        "avg_effectiveness": round(avg_effectiveness * 100, 1),
    }


def get_historical_baselines(
    db: Session,
    period_hours: int = 168  # Default to 7 days for robust baselines
) -> Dict[str, Any]:
    """
    Get historical baselines for Digital Twin simulations.

    Returns averaged metrics that can be used as baseline for simulations.
    """
    kpi_averages = get_historical_kpi_averages(db, period_hours)
    incident_stats = get_incident_statistics(db, period_hours)

    # Get node status distribution
    total_nodes = db.query(func.count(FiberNodeModel.id)).scalar() or 1
    healthy_nodes = db.query(func.count(FiberNodeModel.id)).filter(
        FiberNodeModel.status == 'OPERATIONAL'
    ).scalar() or 0

    # Historical alert frequency
    cutoff_time = datetime.now() - timedelta(hours=period_hours)
    alerts_count = db.query(func.count(AlertModel.id)).filter(
        AlertModel.timestamp >= cutoff_time
    ).scalar() or 0

    alerts_per_hour = alerts_count / period_hours if period_hours > 0 else 0

    return {
        "kpi_baselines": kpi_averages,
        "incident_baselines": incident_stats,
        "network_baselines": {
            "total_nodes": total_nodes,
            "healthy_nodes": healthy_nodes,
            "uptime_percent": round((healthy_nodes / total_nodes) * 100, 2) if total_nodes > 0 else 100.0,
            "avg_alerts_per_hour": round(alerts_per_hour, 2),
        },
        "period_hours": period_hours,
        "calculated_at": datetime.now().isoformat(),
    }


def get_historical_alert_patterns(
    db: Session,
    period_hours: int = 168
) -> Dict[str, Any]:
    """
    Analyze historical alert patterns for trend analysis and prediction.

    Returns alert type distribution, severity trends, and timing patterns.
    """
    cutoff_time = datetime.now() - timedelta(hours=period_hours)

    alerts = db.query(AlertModel).filter(
        AlertModel.timestamp >= cutoff_time
    ).all()

    # Count by type
    by_type: Dict[str, int] = {}
    by_severity: Dict[str, int] = {}
    by_hour: Dict[int, int] = {i: 0 for i in range(24)}

    for alert in alerts:
        # By type
        alert_type = alert.type or "UNKNOWN"
        by_type[alert_type] = by_type.get(alert_type, 0) + 1

        # By severity
        severity = alert.severity or "INFO"
        by_severity[severity] = by_severity.get(severity, 0) + 1

        # By hour of day
        hour = alert.timestamp.hour
        by_hour[hour] += 1

    # Find peak hours
    peak_hours = sorted(by_hour.items(), key=lambda x: x[1], reverse=True)[:3]

    return {
        "total_alerts": len(alerts),
        "by_type": by_type,
        "by_severity": by_severity,
        "by_hour": by_hour,
        "peak_hours": [{"hour": h, "count": c} for h, c in peak_hours],
        "period_hours": period_hours,
    }


def get_similar_historical_incidents(
    db: Session,
    scenario_type: str,
    affected_nodes: int,
    limit: int = 5
) -> List[Dict[str, Any]]:
    """
    Find similar historical incidents for comparison in Digital Twin.

    Matches by scenario type and similar impact scale.
    """
    # Get historical self-healing actions that match the scenario type
    # Map scenario types to action types
    type_mapping = {
        "failure": ["MODEM_REMOTE_REBOOT", "CMTS_PORT_RESET", "PROVISIONING_REFRESH"],
        "capacity": ["NODE_CAPACITY_REBALANCE", "TRAFFIC_REROUTE", "SIGNAL_LEVEL_ADJUSTMENT"],
        "maintenance": ["FIRMWARE_PUSH", "SIGNAL_LEVEL_ADJUSTMENT"],
        "disaster": ["TRAFFIC_REROUTE", "PROVISIONING_REFRESH"],
    }

    action_types = type_mapping.get(scenario_type, ["MODEM_REMOTE_REBOOT"])

    # Query for similar historical actions
    actions = db.query(SelfHealingActionModel).filter(
        SelfHealingActionModel.action_type.in_(action_types),
        SelfHealingActionModel.status == 'COMPLETED'
    ).order_by(desc(SelfHealingActionModel.start_time)).limit(limit * 2).all()

    similar_incidents = []
    for action in actions:
        if action.end_time and action.start_time:
            duration = (action.end_time - action.start_time).total_seconds() / 60
        else:
            duration = 30.0

        similar_incidents.append({
            "action_id": action.action_id,
            "action_type": action.action_type,
            "node_id": action.node_id,
            "duration_minutes": round(duration, 1),
            "effectiveness_score": round(action.effectiveness_score * 100, 1) if action.effectiveness_score else None,
            "timestamp": action.start_time.isoformat() if action.start_time else None,
            "outcome": "success" if action.status == 'COMPLETED' else "failed",
        })

    return similar_incidents[:limit]
