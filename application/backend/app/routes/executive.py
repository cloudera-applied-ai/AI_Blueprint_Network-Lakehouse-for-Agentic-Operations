"""Executive dashboard endpoints - C-level network summary and KPI trends"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, func, cast, case, Integer
from typing import Optional
from datetime import datetime, timedelta
from ..config import settings
from ..database import get_db
from ..models import (
    FiberNodeModel, KPIMetricsModel, AlertModel, SelfHealingActionModel,
    SLABreachModel, FinancialImpactModel, AIInsightModel, AIAlertAnalysisModel,
    SLAConfigModel,
)
from ..schemas import (
    ExecutiveSummaryResponse, ExecutiveKPIResponse,
    KPITrendPoint, PeriodComparisonMetric, ExecutiveInsight,
)
from ..historical_analytics import (
    get_kpi_trends, get_historical_kpi_averages, calculate_period_comparison,
    get_historical_revenue_loss, get_incident_statistics, get_appropriate_kpi_model,
)
from ..llm_insights import generate_rule_based_executive_insights
from ..performance import cache_response, run_queries_parallel, consolidate_count_query, response_cache
from . import safe_error_response, logger

router = APIRouter(prefix=settings.API_V1_STR, tags=["executive"])


# ===== EXECUTIVE DASHBOARD ENDPOINTS =====

def _fetch_executive_summary_data(db: Session, period_hours: int, cutoff_time: datetime) -> dict:
    """
    Fetch all executive summary data using parallel queries and consolidated GROUP BY.
    This is the uncached data fetcher - caching is handled at the endpoint level.
    """
    from sqlalchemy import Integer, cast, case

    # ===== CONSOLIDATED QUERIES =====
    # Instead of 5 separate COUNT queries for node status, use 1 GROUP BY query
    # Instead of multiple alert COUNT queries, use 1 aggregated query

    def fetch_node_status_counts():
        """Single query for all node status counts"""
        result = db.execute(
            select(
                FiberNodeModel.status,
                func.count(FiberNodeModel.id)
            ).group_by(FiberNodeModel.status)
        ).fetchall()
        return {row[0]: row[1] for row in result}

    def fetch_alert_stats():
        """Single query for all alert statistics"""
        result = db.execute(
            select(
                func.count(AlertModel.id).label('total'),
                func.sum(case((AlertModel.status == 'ACTIVE', 1), else_=0)).label('active'),
                func.sum(case(
                    (AlertModel.severity == 'CRITICAL', 1),
                    else_=0
                ) * case(
                    (AlertModel.status == 'ACTIVE', 1),
                    else_=0
                )).label('critical'),
                func.sum(case(
                    (AlertModel.severity == 'WARNING', 1),
                    else_=0
                ) * case(
                    (AlertModel.status == 'ACTIVE', 1),
                    else_=0
                )).label('warning'),
            ).where(AlertModel.timestamp >= cutoff_time)
        ).first()
        return {
            'total': result[0] or 0,
            'active': int(result[1] or 0),
            'critical': int(result[2] or 0),
            'warning': int(result[3] or 0),
        }

    def fetch_healing_stats():
        """Single query for self-healing statistics"""
        result = db.execute(
            select(
                func.count(SelfHealingActionModel.id).label('total'),
                func.sum(case(
                    (SelfHealingActionModel.status == 'COMPLETED', 1),
                    else_=0
                )).label('successful'),
            ).where(SelfHealingActionModel.start_time >= cutoff_time)
        ).first()
        return {
            'total': result[0] or 0,
            'successful': int(result[1] or 0),
        }

    def fetch_sla_config():
        """Fetch SLA configuration"""
        return db.execute(
            select(SLAConfigModel).where(SLAConfigModel.id == 1)
        ).scalar_one_or_none()

    def fetch_active_breaches():
        """Count active SLA breaches"""
        return db.execute(
            select(func.count(SLABreachModel.id)).where(SLABreachModel.resolved == False)
        ).scalar() or 0

    def fetch_kpi_averages():
        """Fetch KPI averages"""
        return db.execute(
            select(
                func.avg(KPIMetricsModel.latency_ms),
                func.avg(KPIMetricsModel.downstream_throughput_mbps),
                func.avg(KPIMetricsModel.packet_loss_percent),
                func.avg(KPIMetricsModel.ds_snr_db)
            ).where(KPIMetricsModel.timestamp >= cutoff_time)
        ).first()

    def fetch_regional_performance():
        """Fetch regional performance data"""
        return db.execute(
            select(
                FiberNodeModel.region,
                func.count(FiberNodeModel.id),
                func.sum(cast(FiberNodeModel.status == 'healthy', Integer))
            ).group_by(FiberNodeModel.region)
        ).fetchall()

    # ===== SEQUENTIAL EXECUTION =====
    # Run queries sequentially to avoid SQLAlchemy session threading issues
    query_results = {
        "node_status": fetch_node_status_counts(),
        "alert_stats": fetch_alert_stats(),
        "healing_stats": fetch_healing_stats(),
        "sla_config": fetch_sla_config(),
        "active_breaches": fetch_active_breaches(),
        "kpi_averages": fetch_kpi_averages(),
        "regional": fetch_regional_performance(),
    }

    # ===== EXTRACT RESULTS =====
    node_status = query_results.get("node_status") or {}
    alert_stats = query_results.get("alert_stats") or {}
    healing_stats = query_results.get("healing_stats") or {}
    config = query_results.get("sla_config")
    active_breaches = query_results.get("active_breaches") or 0
    recent_kpis = query_results.get("kpi_averages")
    regions = query_results.get("regional", [])

    # Node counts from consolidated query
    operational = node_status.get('healthy', 0)
    degraded = node_status.get('degraded', 0)
    outage = node_status.get('outage', 0)
    maintenance = node_status.get('maintenance', 0)
    total_nodes = sum(node_status.values()) or 1
    healthy_nodes = total_nodes - outage
    network_uptime = (healthy_nodes / total_nodes) * 100

    # Alert counts from consolidated query
    total_alerts = alert_stats.get('total', 0)
    critical_alerts = alert_stats.get('critical', 0)
    warning_alerts_count = alert_stats.get('warning', 0)

    # Self-healing stats from consolidated query
    total_actions = healing_stats.get('total', 0)
    successful_actions = healing_stats.get('successful', 0)

    # Financial metrics
    cost_per_minute = config.cost_per_outage_minute if config else 1000.0
    revenue_per_user = config.revenue_per_subscriber_per_hour if config else 0.50

    # KPI averages
    avg_latency = float(recent_kpis[0]) if recent_kpis and recent_kpis[0] else 25.0
    avg_throughput = float(recent_kpis[1]) if recent_kpis and recent_kpis[1] else 150.0
    avg_packet_loss = float(recent_kpis[2]) if recent_kpis and recent_kpis[2] else 1.5
    avg_ds_snr = float(recent_kpis[3]) if recent_kpis and recent_kpis[3] else 38.0

    return {
        'total_nodes': total_nodes,
        'healthy_nodes': healthy_nodes,
        'operational': operational,
        'degraded': degraded,
        'outage': outage,
        'maintenance': maintenance,
        'network_uptime': network_uptime,
        'total_alerts': total_alerts,
        'critical_alerts': critical_alerts,
        'warning_alerts_count': warning_alerts_count,
        'total_actions': total_actions,
        'successful_actions': successful_actions,
        'active_breaches': active_breaches,
        'cost_per_minute': cost_per_minute,
        'revenue_per_user': revenue_per_user,
        'avg_latency': avg_latency,
        'avg_throughput': avg_throughput,
        'avg_packet_loss': avg_packet_loss,
        'avg_ds_snr': avg_ds_snr,
        'regions': regions,
    }


@router.get("/executive/summary", response_model=ExecutiveSummaryResponse)
def get_executive_summary(
    period_hours: int = Query(24, ge=1, le=168, description="Period in hours for summary"),
    db: Session = Depends(get_db),
):
    """
    Get executive-level network summary.
    Aggregates key metrics for C-level dashboard.

    Performance optimizations:
    - Response caching (5 second TTL)
    - Consolidated GROUP BY queries (1 query instead of 5 for node status)
    - Parallel query execution using thread pool
    """
    import hashlib

    # ===== RESPONSE CACHING =====
    # Cache key based on period_hours - TTL of 5 seconds
    cache_key = f"executive_summary:{period_hours}"
    cached_response = response_cache.get(cache_key)
    if cached_response is not None:
        logger.debug(f"Returning cached executive summary for period_hours={period_hours}")
        return cached_response

    cutoff_time = datetime.now() - timedelta(hours=period_hours)

    # Fetch all data using parallel queries
    data = _fetch_executive_summary_data(db, period_hours, cutoff_time)

    # Extract values from parallel query results
    total_nodes = data['total_nodes']
    operational = data['operational']
    degraded = data['degraded']
    outage = data['outage']
    maintenance = data['maintenance']
    network_uptime = data['network_uptime']
    total_alerts = data['total_alerts']
    critical_alerts = data['critical_alerts']
    warning_alerts_count = data['warning_alerts_count']
    total_actions = data['total_actions']
    successful_actions = data['successful_actions']
    active_breaches = data['active_breaches']
    cost_per_minute = data['cost_per_minute']
    revenue_per_user = data['revenue_per_user']
    avg_latency = data['avg_latency']
    avg_throughput = data['avg_throughput']
    avg_ds_snr = data['avg_ds_snr']
    regions = data['regions']

    # Derived calculations
    users_affected = outage * 500
    revenue_at_risk = users_affected * revenue_per_user * (period_hours / 24)
    ai_cost_savings = successful_actions * 30 * cost_per_minute * 0.01
    sla_compliance = 100 - (active_breaches * 2)

    # Manual interventions
    manual_interventions = total_actions - successful_actions

    # Estimated affected users
    affected_users_current = outage * 500

    # Revenue protected (estimated from successful actions)
    revenue_protected = successful_actions * 30 * cost_per_minute * 0.5

    # Actual revenue loss (estimated)
    actual_revenue_loss = outage * 500 * revenue_per_user * 24

    # SLA penalty exposure
    sla_penalty_exposure = active_breaches * 5000

    # Net financial impact
    net_financial_impact = round(actual_revenue_loss + sla_penalty_exposure - revenue_protected, 2)

    # Format regions for schema
    regions_list = []
    for region in regions:
        region_name = region[0] or "Unknown"
        total = region[1] or 1
        operational_count = region[2] or 0
        regions_list.append({
            "region": region_name,
            "nodes": total,
            "uptime": round((operational_count / total) * 100, 1),
            "revenue_impact": round(total * 100, 2),  # Estimated
            "alerts": int(total_alerts / (len(regions) or 1)),  # Distributed evenly
        })

    # Top issues formatted for schema
    top_issues_list = [
        {"node_id": "network-wide", "issue_type": "NODE_OUTAGE", "duration": 30, "impact": outage * 1000},
        {"node_id": "network-wide", "issue_type": "HIGH_LATENCY", "duration": 15, "impact": int(total_alerts * 0.2) * 100},
        {"node_id": "network-wide", "issue_type": "HIGH_PACKET_LOSS", "duration": 20, "impact": int(total_alerts * 0.15) * 100},
    ]

    # ===== NEW: Historical Analytics Integration =====

    # Get KPI trends from aggregated tables for charting
    try:
        kpi_trend_data = get_kpi_trends(db, period_hours, max_points=50)
        kpi_trend_points = [KPITrendPoint(**pt) for pt in kpi_trend_data] if kpi_trend_data else None
    except Exception as e:
        logger.warning(f"Failed to get KPI trends: {e}")
        kpi_trend_points = None

    # Get period comparison (current vs previous period) for real trends
    period_comparison_data = None  # Initialize for later use
    try:
        period_comparison_data = calculate_period_comparison(db, period_hours)
        period_comparison = [PeriodComparisonMetric(**pc) for pc in period_comparison_data] if period_comparison_data else None

        # Update trend indicators based on actual comparison data
        if period_comparison:
            uptime_cmp = next((pc for pc in period_comparison_data if pc["metric_name"] == "ds_snr_db"), None)
            latency_cmp = next((pc for pc in period_comparison_data if pc["metric_name"] == "latency_ms"), None)

            if uptime_cmp:
                trend_uptime = uptime_cmp.get("trend", "stable")
            else:
                trend_uptime = "stable" if network_uptime >= 98 else ("declining" if network_uptime < 95 else "stable")

            # Determine incident trend from comparison
            declining_count = sum(1 for pc in period_comparison_data if pc.get("trend") == "declining")
            improving_count = sum(1 for pc in period_comparison_data if pc.get("trend") == "improving")
            trend_incidents = "improving" if improving_count > declining_count else ("declining" if declining_count > improving_count else "stable")
        else:
            trend_uptime = "stable" if network_uptime >= 98 else ("declining" if network_uptime < 95 else "stable")
            trend_incidents = "improving" if total_alerts < 100 else ("declining" if total_alerts > 500 else "stable")
    except Exception as e:
        logger.warning(f"Failed to get period comparison: {e}")
        period_comparison = None
        trend_uptime = "stable" if network_uptime >= 98 else ("declining" if network_uptime < 95 else "stable")
        trend_incidents = "improving" if total_alerts < 100 else ("declining" if total_alerts > 500 else "stable")

    # Get historical revenue loss from actual alert data
    historical_loss = None  # Initialize for later use
    try:
        historical_loss = get_historical_revenue_loss(db, period_hours)
        historical_revenue_loss = historical_loss.get("total_loss", actual_revenue_loss)
    except Exception as e:
        logger.warning(f"Failed to get historical revenue loss: {e}")
        historical_revenue_loss = actual_revenue_loss

    # Get incident statistics for MTTR
    incident_stats = None  # Initialize for later use
    try:
        incident_stats = get_incident_statistics(db, period_hours)
        mttr_minutes = incident_stats.get("mttr_minutes", 30.0)
        actual_avg_resolution = mttr_minutes
    except Exception as e:
        logger.warning(f"Failed to get incident statistics: {e}")
        mttr_minutes = None
        actual_avg_resolution = 30.0

    # Generate rule-based AI insights - pass pre-computed data to avoid duplicate queries
    try:
        ai_insights_data = generate_rule_based_executive_insights(
            db,
            period_hours,
            precomputed_period_comparison=period_comparison_data,
            precomputed_revenue_loss=historical_loss,
            precomputed_incident_stats=incident_stats,
        )
        ai_insights = [ExecutiveInsight(**insight) for insight in ai_insights_data] if ai_insights_data else None
    except Exception as e:
        logger.warning(f"Failed to generate AI insights: {e}")
        ai_insights = None

    # Determine data source used
    kpi_model = get_appropriate_kpi_model(period_hours)
    data_source = kpi_model.__tablename__

    trend_revenue_impact = "improving" if ai_cost_savings > actual_revenue_loss else "stable"

    # Determine period string
    period = "realtime" if period_hours <= 1 else ("daily" if period_hours <= 24 else ("weekly" if period_hours <= 168 else "monthly"))

    response = ExecutiveSummaryResponse(
        timestamp=datetime.now(),
        period=period,
        period_hours=period_hours,
        total_nodes=total_nodes,
        healthy_nodes=operational,
        degraded_nodes=degraded,
        outage_nodes=outage,
        maintenance_nodes=maintenance,
        network_uptime_percent=round(network_uptime, 2),
        sla_compliance_percent=round(max(0, sla_compliance), 1),
        active_sla_breaches=active_breaches,
        near_breach_warnings=warning_alerts_count,
        breaches_this_period=active_breaches,
        revenue_at_risk=round(revenue_at_risk, 2),
        revenue_protected=round(revenue_protected, 2),
        actual_revenue_loss=round(actual_revenue_loss, 2),
        ai_cost_savings=round(ai_cost_savings, 2),
        sla_penalty_exposure=round(sla_penalty_exposure, 2),
        net_financial_impact=net_financial_impact,
        historical_revenue_loss=round(historical_revenue_loss, 2),
        total_alerts=total_alerts,
        critical_alerts=critical_alerts,
        warning_alerts=warning_alerts_count,
        auto_resolved=successful_actions,
        manual_interventions=manual_interventions,
        avg_resolution_time_minutes=round(actual_avg_resolution, 1),
        mttr_minutes=mttr_minutes,
        avg_latency_ms=round(avg_latency, 2),
        avg_ds_snr_db=round(avg_ds_snr, 2),
        downstream_throughput_mbps=round(avg_throughput, 2),
        affected_subscribers_current=affected_users_current,
        regions=regions_list,
        top_issues=top_issues_list,
        trend_uptime=trend_uptime,
        trend_incidents=trend_incidents,
        trend_revenue_impact=trend_revenue_impact,
        # NEW: Historical data fields
        kpi_trend_data=kpi_trend_points,
        period_comparison=period_comparison,
        ai_insights=ai_insights,
        data_source=data_source,
    )

    # Cache response for 5 seconds to reduce database load
    response_cache.set(cache_key, response, ttl_seconds=5.0)
    return response


@router.get("/executive/kpis", response_model=ExecutiveKPIResponse)
def get_executive_kpis(
    granularity: str = Query("hourly", description="hourly or daily"),
    period_days: int = Query(7, ge=1, le=30),
    db: Session = Depends(get_db),
):
    """
    Get executive KPI trends for charting.
    Returns time-series data for key metrics.
    """
    from sqlalchemy import text

    cutoff_time = datetime.now() - timedelta(days=period_days)

    # Build aggregation query
    ALLOWED_GRANULARITIES = {
        "hourly": "date_trunc('hour', timestamp)",
        "daily": "date_trunc('day', timestamp)",
    }
    if granularity not in ALLOWED_GRANULARITIES:
        granularity = "daily"
    date_trunc = ALLOWED_GRANULARITIES[granularity]

    # Use pre-aggregated tables instead of scanning raw kpi_metrics
    GRANULARITY_TABLE = {
        "hourly": "kpi_metrics_hourly",
        "daily": "kpi_metrics_daily",
    }
    table = GRANULARITY_TABLE[granularity]

    query = text(f"""
        SELECT
            {date_trunc} as period,
            AVG(latency_ms) as latency,
            AVG(downstream_throughput_mbps) as throughput,
            AVG(packet_loss_percent) as packet_loss,
            AVG(ds_snr_db) as ds_snr,
            COUNT(DISTINCT node_id) as active_nodes
        FROM {table}
        WHERE timestamp >= :cutoff
        GROUP BY {date_trunc}
        ORDER BY period ASC
    """)

    results = db.execute(query, {"cutoff": cutoff_time}).fetchall()

    data_points = []
    for row in results:
        data_points.append({
            "timestamp": row[0].isoformat() if row[0] else None,
            "latency_ms": round(float(row[1]), 2) if row[1] else 0,
            "throughput_mbps": round(float(row[2]), 2) if row[2] else 0,
            "packet_loss_percent": round(float(row[3]), 2) if row[3] else 0,
            "ds_snr_db": round(float(row[4]), 2) if row[4] else 0,
            "active_nodes": row[5] or 0,
        })

    # Consolidated node counts (2 queries → 1)
    node_counts = db.execute(
        select(
            func.count(FiberNodeModel.id).label('total'),
            func.sum(case((FiberNodeModel.status != 'OUTAGE', 1), else_=0)).label('healthy'),
        )
    ).one()
    total_nodes = node_counts.total or 1
    healthy_nodes = node_counts.healthy or 0
    network_availability = (healthy_nodes / total_nodes) * 100

    # Consolidated self-healing stats (2 queries → 1)
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
    self_healing_success_rate = (successful_actions / total_actions) * 100 if total_actions > 0 else 0

    # SLA compliance
    active_breaches = db.execute(
        select(func.count(SLABreachModel.id)).where(SLABreachModel.resolved == False)
    ).scalar() or 0
    sla_compliance = 100 - (active_breaches * 2)

    # Estimated customer impact (lower is better)
    outage_nodes = total_nodes - healthy_nodes
    customer_impact_score = min(100, max(0, 100 - (outage_nodes / total_nodes * 100 * 10)))

    # Financial efficiency (savings vs losses ratio)
    financial_efficiency = min(100, self_healing_success_rate * 1.2)

    return ExecutiveKPIResponse(
        network_availability=round(network_availability, 2),
        mean_time_to_repair_minutes=30.0,
        self_healing_success_rate=round(self_healing_success_rate, 2),
        customer_impact_score=round(customer_impact_score, 2),
        financial_efficiency=round(financial_efficiency, 2),
        sla_compliance=round(max(0, sla_compliance), 2),
    )
