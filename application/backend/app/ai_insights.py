"""
AI Insights Module - Rule-based insight generators for autonomous network analysis.

This module provides rule-based analysis that works WITHOUT requiring an LLM.
It generates insights from network data patterns, sensor readings, and historical trends.

Ported from src/services/aiAgentService.ts generateRuleBasedInsights()
"""

import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Set
from enum import Enum
from dataclasses import dataclass, field
from collections import defaultdict

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from .models import FiberNodeModel as FiberNode, KPIMetricsModel as KPIMetrics, AlertModel as Alert, SelfHealingActionModel as SelfHealingAction
from .sensor_generator import (
    generate_equipment_sensor_data,
    generate_rf_plant_sensor_data,
    generate_environmental_sensor,
)


class InsightType(str, Enum):
    """Types of AI insights"""
    PATTERN_DETECTED = "pattern_detected"
    ANOMALY_FORECAST = "anomaly_forecast"
    ROOT_CAUSE = "root_cause"
    OPTIMIZATION = "optimization"
    CAPACITY_WARNING = "capacity_warning"
    DEGRADATION_TREND = "degradation_trend"


@dataclass
class ChartDataPoint:
    """Single data point for insight charts"""
    date: str
    value: float
    label: Optional[str] = None


@dataclass
class ChartSeries:
    """Chart series data"""
    name: str
    data: List[ChartDataPoint]


@dataclass
class InsightChartData:
    """Chart data for insights"""
    type: str  # 'line', 'bar', 'area', 'pie'
    title: str
    x_axis_label: Optional[str] = None
    y_axis_label: Optional[str] = None
    data: List[ChartDataPoint] = field(default_factory=list)
    series: List[ChartSeries] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "title": self.title,
            "xAxisLabel": self.x_axis_label,
            "yAxisLabel": self.y_axis_label,
            "data": [{"date": d.date, "value": d.value, "label": d.label} for d in self.data],
            "series": [
                {"name": s.name, "data": [{"date": d.date, "value": d.value, "label": d.label} for d in s.data]}
                for s in self.series
            ],
        }


@dataclass
class AIInsight:
    """AI-generated insight about network state"""
    id: str
    timestamp: datetime
    insight_type: InsightType
    severity: str  # 'info', 'warning', 'critical'
    title: str
    description: str
    recommendation: str
    confidence: float
    affected_node_ids: List[str]
    related_alert_ids: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    expires_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "type": self.insight_type.value,
            "severity": self.severity,
            "title": self.title,
            "description": self.description,
            "recommendation": self.recommendation,
            "confidence": self.confidence,
            "affectedNodes": self.affected_node_ids,
            "relatedAlerts": self.related_alert_ids,
            "metadata": self.metadata,
            "expiresAt": self.expires_at.isoformat() if self.expires_at else None,
        }


def get_daily_aggregated_kpis(db: Session, days: int = 30) -> List[Dict[str, Any]]:
    """Get daily aggregated KPI statistics for the last N days using a single efficient query"""
    start_date = datetime.utcnow() - timedelta(days=days)

    # Single query with GROUP BY instead of 30 separate queries
    results = db.query(
        func.date(KPIMetrics.timestamp).label('day'),
        func.avg(KPIMetrics.ds_snr_db).label('avg_ds_snr'),
        func.avg(KPIMetrics.us_snr_db).label('avg_us_snr'),
        func.avg(KPIMetrics.fec_uncorrected_codewords).label('avg_fec_uncorrected'),
        func.count(KPIMetrics.metric_id).label('count')
    ).filter(
        KPIMetrics.timestamp >= start_date
    ).group_by(
        func.date(KPIMetrics.timestamp)
    ).order_by(
        func.date(KPIMetrics.timestamp)
    ).all()

    daily_data = []
    for row in results:
        if row.count > 0:
            daily_data.append({
                "date": row.day.strftime("%Y-%m-%d") if hasattr(row.day, 'strftime') else str(row.day),
                "avgDsSNR": float(row.avg_ds_snr or 0),
                "avgUsSNR": float(row.avg_us_snr or 0),
                "avgFECUncorrected": float(row.avg_fec_uncorrected or 0),
                "count": row.count,
            })

    return daily_data


def get_daily_alert_counts(db: Session, days: int = 30) -> List[Dict[str, Any]]:
    """Get daily alert counts by severity for the last N days using a single efficient query"""
    start_date = datetime.utcnow() - timedelta(days=days)

    # Single query with GROUP BY instead of 30 separate queries
    results = db.query(
        func.date(Alert.timestamp).label('day'),
        Alert.severity,
        func.count(Alert.alert_id).label('count')
    ).filter(
        Alert.timestamp >= start_date
    ).group_by(
        func.date(Alert.timestamp),
        Alert.severity
    ).order_by(
        func.date(Alert.timestamp)
    ).all()

    # Aggregate results by day
    daily_counts: Dict[str, Dict[str, int]] = defaultdict(lambda: {"total": 0, "critical": 0, "warning": 0, "info": 0})
    for row in results:
        day_str = row.day.strftime("%Y-%m-%d") if hasattr(row.day, 'strftime') else str(row.day)
        daily_counts[day_str]["total"] += row.count
        if row.severity in ('critical', 'warning', 'info'):
            daily_counts[day_str][row.severity] += row.count

    # Convert to sorted list
    daily_data = [
        {"date": day, **counts}
        for day, counts in sorted(daily_counts.items())
    ]

    return daily_data


def get_daily_action_stats(db: Session, days: int = 30) -> List[Dict[str, Any]]:
    """Get daily self-healing action statistics for the last N days using a single efficient query"""
    start_date = datetime.utcnow() - timedelta(days=days)

    # Single query with GROUP BY instead of 30 separate queries
    results = db.query(
        func.date(SelfHealingAction.start_time).label('day'),
        SelfHealingAction.status,
        func.count(SelfHealingAction.action_id).label('count'),
        func.avg(SelfHealingAction.effectiveness_score).label('avg_effectiveness')
    ).filter(
        SelfHealingAction.start_time >= start_date
    ).group_by(
        func.date(SelfHealingAction.start_time),
        SelfHealingAction.status
    ).order_by(
        func.date(SelfHealingAction.start_time)
    ).all()

    # Aggregate results by day
    daily_stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
        "total": 0, "completed": 0, "failed": 0, "effectiveness_sum": 0, "effectiveness_count": 0
    })
    for row in results:
        day_str = row.day.strftime("%Y-%m-%d") if hasattr(row.day, 'strftime') else str(row.day)
        daily_stats[day_str]["total"] += row.count
        if row.status == 'COMPLETED':
            daily_stats[day_str]["completed"] += row.count
        elif row.status == 'FAILED':
            daily_stats[day_str]["failed"] += row.count
        if row.avg_effectiveness is not None:
            daily_stats[day_str]["effectiveness_sum"] += float(row.avg_effectiveness) * row.count
            daily_stats[day_str]["effectiveness_count"] += row.count

    # Convert to sorted list with computed averages
    daily_data = []
    for day, stats in sorted(daily_stats.items()):
        avg_eff = stats["effectiveness_sum"] / stats["effectiveness_count"] if stats["effectiveness_count"] > 0 else 0
        daily_data.append({
            "date": day,
            "total": stats["total"],
            "completed": stats["completed"],
            "failed": stats["failed"],
            "avgEffectiveness": avg_eff,
        })

    return daily_data


def generate_rule_based_insights(
    db: Session,
    nodes: Optional[List[FiberNode]] = None,
    alerts: Optional[List[Alert]] = None,
    actions: Optional[List[SelfHealingAction]] = None,
) -> List[AIInsight]:
    """
    Generate rule-based insights from network data.

    This is the main entry point that generates 13+ categories of insights
    without requiring an LLM. Runs automatically in the backend.
    """
    insights: List[AIInsight] = []
    now = datetime.utcnow()

    # Fetch data if not provided
    if nodes is None:
        nodes = db.query(FiberNode).all()
    if alerts is None:
        # Get active alerts (not resolved)
        alerts = db.query(Alert).filter(Alert.status == 'active').all()
    if actions is None:
        # Get recent actions (last 30 days)
        actions = db.query(SelfHealingAction).filter(
            SelfHealingAction.start_time >= now - timedelta(days=30)
        ).all()

    # Get 30-day historical data for charts
    daily_kpis = get_daily_aggregated_kpis(db, 30)
    daily_alerts = get_daily_alert_counts(db, 30)
    daily_actions = get_daily_action_stats(db, 30)

    # Generate sensor data for analysis
    equipment_sensors = []
    rf_plant_sensors = []
    environmental_sensors = []

    for node in nodes[:50]:  # Sample first 50 nodes for performance
        # Convert SQLAlchemy model to dict for sensor generators
        node_dict = {
            'node_id': node.node_id,
            'status': node.status,
            'latitude': node.latitude,
            'longitude': node.longitude,
            'region': node.region,
            'climate_zone': getattr(node, 'climate_zone', None),
            'manufacturer': node.manufacturer,
            'hardware_model': node.hardware_model,
        }
        equipment_sensors.append(generate_equipment_sensor_data(node_dict))
        rf_plant_sensors.append(generate_rf_plant_sensor_data(node_dict))
        environmental_sensors.append(generate_environmental_sensor(node_dict))

    # ============================================
    # 1. NETWORK HEALTH OVERVIEW (30-day Analysis)
    # ============================================
    healthy_nodes = [t for t in nodes if t.status == 'healthy']
    degraded_nodes = [t for t in nodes if t.status == 'degraded']
    outage_nodes = [t for t in nodes if t.status == 'outage']
    maintenance_nodes = [t for t in nodes if t.status == 'maintenance']
    health_score = (len(healthy_nodes) / len(nodes)) * 100 if nodes else 0

    # Build KPI trend chart
    kpi_trend_chart = InsightChartData(
        type="line",
        title="30-Day Network KPI Trends",
        x_axis_label="Date",
        y_axis_label="Value",
        series=[
            ChartSeries(
                name="DS SNR (dB)",
                data=[ChartDataPoint(date=d["date"], value=d["avgDsSNR"], label=f"{d['avgDsSNR']:.1f} dB") for d in daily_kpis]
            ),
            ChartSeries(
                name="US SNR (dB)",
                data=[ChartDataPoint(date=d["date"], value=d["avgUsSNR"], label=f"{d['avgUsSNR']:.1f} dB") for d in daily_kpis]
            ),
            ChartSeries(
                name="FEC Uncorrected (inverted)",
                data=[ChartDataPoint(date=d["date"], value=100-d["avgFECUncorrected"], label=f"{100-d['avgFECUncorrected']:.1f}") for d in daily_kpis]
            ),
        ]
    )

    # Build alert trend chart
    alert_trend_chart = InsightChartData(
        type="bar",
        title="30-Day Alert History",
        x_axis_label="Date",
        y_axis_label="Alert Count",
        data=[ChartDataPoint(date=d["date"], value=d["total"], label=f"{d['total']} alerts") for d in daily_alerts],
        series=[
            ChartSeries(name="Critical", data=[ChartDataPoint(date=d["date"], value=d["critical"], label=str(d["critical"])) for d in daily_alerts]),
            ChartSeries(name="Warning", data=[ChartDataPoint(date=d["date"], value=d["warning"], label=str(d["warning"])) for d in daily_alerts]),
            ChartSeries(name="Info", data=[ChartDataPoint(date=d["date"], value=d["info"], label=str(d["info"])) for d in daily_alerts]),
        ]
    )

    # Calculate 30-day averages
    avg_ds_snr = sum(d["avgDsSNR"] for d in daily_kpis) / len(daily_kpis) if daily_kpis else 0
    avg_us_snr = sum(d["avgUsSNR"] for d in daily_kpis) / len(daily_kpis) if daily_kpis else 0
    total_alerts_30d = sum(d["total"] for d in daily_alerts)
    total_actions_30d = sum(d["total"] for d in daily_actions)

    insights.append(AIInsight(
        id=f"rule-network-health-{int(now.timestamp())}",
        timestamp=now,
        insight_type=InsightType.PATTERN_DETECTED,
        severity="info" if health_score >= 95 else "warning" if health_score >= 85 else "critical",
        title="Network Health Overview (30-Day Analysis)",
        description=f"Overall network health: {health_score:.1f}%. {len(healthy_nodes)} healthy, {len(degraded_nodes)} degraded, {len(outage_nodes)} outage, {len(maintenance_nodes)} in maintenance out of {len(nodes)} total nodes.\n\n30-Day Summary:\n- Avg DS SNR: {avg_ds_snr:.1f} dB\n- Avg US SNR: {avg_us_snr:.1f} dB\n- Total Alerts: {total_alerts_30d}\n- Total Self-Healing Actions: {total_actions_30d}",
        recommendation=(
            "Network is operating within normal parameters. Continue monitoring."
            if health_score >= 95 else
            "Some nodes need attention. Review degraded nodes for preventive maintenance."
            if health_score >= 85 else
            "Network health below threshold. Immediate attention required for outage nodes."
        ),
        confidence=0.95,
        affected_node_ids=[t.node_id for t in nodes],
        related_alert_ids=[a.alert_id for a in alerts],
        metadata={
            "charts": [kpi_trend_chart.to_dict(), alert_trend_chart.to_dict()],
            "thirtyDayStats": {
                "avgDsSNR": avg_ds_snr,
                "avgUsSNR": avg_us_snr,
                "totalAlerts": total_alerts_30d,
                "totalActions": total_actions_30d,
                "dataPointCount": len(daily_kpis),
            },
        },
        expires_at=now + timedelta(hours=1),
    ))

    # ============================================
    # 2. MAINTENANCE DUE ANALYSIS
    # ============================================
    overdue_maintenance = [t for t in nodes if getattr(t, 'next_maintenance_due', None) and t.next_maintenance_due < now]
    upcoming_maintenance = [
        t for t in nodes
        if getattr(t, 'next_maintenance_due', None) and now <= t.next_maintenance_due <= now + timedelta(days=7)
    ]

    if overdue_maintenance:
        regions = set(t.region for t in overdue_maintenance)
        critical_count = len([t for t in overdue_maintenance if (getattr(t, 'homes_active', 0) or 0) > 2000])
        insights.append(AIInsight(
            id=f"rule-overdue-maintenance-{int(now.timestamp())}",
            timestamp=now,
            insight_type=InsightType.ANOMALY_FORECAST,
            severity="critical" if len(overdue_maintenance) > 10 else "warning",
            title=f"Overdue Maintenance: {len(overdue_maintenance)} Nodes",
            description=f"{len(overdue_maintenance)} nodes have overdue maintenance. This increases risk of equipment failure and service degradation. Affected regions: {', '.join(regions)}.",
            recommendation=f"Schedule maintenance for overdue nodes immediately. Priority: {critical_count} Critical SLA nodes.",
            confidence=0.90,
            affected_node_ids=[t.node_id for t in overdue_maintenance],
            expires_at=now + timedelta(hours=6),
        ))

    if upcoming_maintenance:
        insights.append(AIInsight(
            id=f"rule-upcoming-maintenance-{int(now.timestamp())}",
            timestamp=now,
            insight_type=InsightType.PATTERN_DETECTED,
            severity="info",
            title=f"Upcoming Maintenance: {len(upcoming_maintenance)} Nodes",
            description=f"{len(upcoming_maintenance)} nodes have maintenance due within 7 days. Plan maintenance windows to minimize service impact.",
            recommendation="Schedule maintenance during low-traffic periods. Coordinate with NOC for traffic rerouting.",
            confidence=0.95,
            affected_node_ids=[t.node_id for t in upcoming_maintenance],
            expires_at=now + timedelta(days=1),
        ))

    # ============================================
    # 3. EQUIPMENT AGE/LIFECYCLE ANALYSIS
    # ============================================
    old_equipment = [
        t for t in nodes
        if getattr(t, 'commissioned_date', None) and (now - t.commissioned_date).days > (7 * 365)
    ]

    if old_equipment:
        by_manufacturer: Dict[str, int] = defaultdict(int)
        for t in old_equipment:
            by_manufacturer[t.manufacturer] += 1
        mfr_breakdown = ", ".join(f"{m}: {c}" for m, c in by_manufacturer.items())

        insights.append(AIInsight(
            id=f"rule-aging-equipment-{int(now.timestamp())}",
            timestamp=now,
            insight_type=InsightType.ANOMALY_FORECAST,
            severity="warning" if len(old_equipment) > len(nodes) * 0.2 else "info",
            title=f"Aging Equipment: {len(old_equipment)} Nodes (>7 years)",
            description=f"{len(old_equipment)} nodes ({(len(old_equipment) / len(nodes)) * 100:.1f}%) have equipment older than 7 years. By manufacturer: {mfr_breakdown}. Older equipment has higher failure rates.",
            recommendation="Plan equipment refresh cycle. Prioritize nodes with Critical SLA tier and high-density service areas.",
            confidence=0.85,
            affected_node_ids=[t.node_id for t in old_equipment],
            expires_at=now + timedelta(days=1),
        ))

    # ============================================
    # 4. REGIONAL DISTRIBUTION ANALYSIS
    # ============================================
    region_stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {"total": 0, "healthy": 0, "homes_passed": 0})
    for t in nodes:
        region_stats[t.region]["total"] += 1
        if t.status == "healthy":
            region_stats[t.region]["healthy"] += 1
        region_stats[t.region]["homes_passed"] += t.homes_passed or 0

    for region, stats in region_stats.items():
        health_rate = (stats["healthy"] / stats["total"]) * 100 if stats["total"] > 0 else 0
        if health_rate < 90:
            region_node_ids = [t.node_id for t in nodes if t.region == region]
            region_alert_ids = [a.alert_id for a in alerts if any(t.node_id == a.node_id for t in nodes if t.region == region)]

            insights.append(AIInsight(
                id=f"rule-region-health-{region}-{int(now.timestamp())}",
                timestamp=now,
                insight_type=InsightType.ROOT_CAUSE,
                severity="critical" if health_rate < 80 else "warning",
                title=f"{region} Region Health: {health_rate:.1f}%",
                description=f"{region} has {stats['healthy']}/{stats['total']} healthy nodes ({health_rate:.1f}%). Total homes passed: {stats['homes_passed']:,}. Below optimal threshold.",
                recommendation=f"Investigate degraded nodes in {region}. Consider load balancing to neighboring regions.",
                confidence=0.90,
                affected_node_ids=region_node_ids,
                related_alert_ids=region_alert_ids,
                expires_at=now + timedelta(hours=2),
            ))

    # ============================================
    # 5. DOCSIS VERSION DISTRIBUTION INSIGHT
    # ============================================
    docsis_distribution: Dict[str, List[str]] = defaultdict(list)
    for t in nodes:
        if t.docsis_version:
            docsis_distribution[t.docsis_version].append(t.node_id)

    docsis_30_nodes = len(docsis_distribution.get("3.0", []))
    docsis_31_nodes = len(docsis_distribution.get("3.1", []))
    docsis_40_nodes = len(docsis_distribution.get("4.0", []))

    if docsis_distribution:
        all_docsis_node_ids = [nid for nids in docsis_distribution.values() for nid in nids]
        version_breakdown = ", ".join(
            f"DOCSIS {v}: {len(ids)} ({(len(ids) / len(nodes)) * 100:.1f}%)"
            for v, ids in sorted(docsis_distribution.items())
        )
        insights.append(AIInsight(
            id=f"rule-docsis-coverage-{int(now.timestamp())}",
            timestamp=now,
            insight_type=InsightType.PATTERN_DETECTED,
            severity="info",
            title=f"DOCSIS Version Distribution",
            description=f"DOCSIS version distribution across {len(nodes)} nodes: {version_breakdown}. DOCSIS 4.0 coverage: {(docsis_40_nodes / len(nodes)) * 100:.1f}%. DOCSIS 3.1 coverage: {(docsis_31_nodes / len(nodes)) * 100:.1f}%. DOCSIS 3.0 (legacy): {(docsis_30_nodes / len(nodes)) * 100:.1f}%.",
            recommendation="Continue DOCSIS 4.0 upgrades in high-density service areas. Plan migration path for remaining DOCSIS 3.0 nodes.",
            confidence=0.95,
            affected_node_ids=all_docsis_node_ids,
            expires_at=now + timedelta(days=1),
        ))

    # ============================================
    # 6. PLANT REDUNDANCY ANALYSIS
    # ============================================
    no_redundancy = [t for t in nodes if not getattr(t, 'has_redundancy', True)]
    critical_no_redundancy = [t for t in no_redundancy if (getattr(t, 'homes_active', 0) or 0) > 2000]

    if critical_no_redundancy:
        node_types = set(t.node_type for t in critical_no_redundancy if t.node_type)
        insights.append(AIInsight(
            id=f"rule-critical-redundancy-{int(now.timestamp())}",
            timestamp=now,
            insight_type=InsightType.ANOMALY_FORECAST,
            severity="warning",
            title=f"Critical SLA Nodes Without Path Redundancy: {len(critical_no_redundancy)}",
            description=f"{len(critical_no_redundancy)} Critical SLA tier nodes lack path redundancy. Single point of failure risk. Node types: {', '.join(node_types)}.",
            recommendation="Prioritize redundancy upgrades for Critical SLA nodes. Consider alternate fiber paths and ring topology for high-priority plant segments.",
            confidence=0.85,
            affected_node_ids=[t.node_id for t in critical_no_redundancy],
            expires_at=now + timedelta(days=1),
        ))

    # ============================================
    # 7. POWER RESILIENCE ANALYSIS
    # ============================================
    low_battery = [t for t in nodes if (t.battery_backup_hours or 0) < 4]
    no_generator = [t for t in nodes if not getattr(t, 'has_generator', True) and (getattr(t, 'homes_active', 0) or 0) > 2000]

    if low_battery or no_generator:
        affected = list(set([t.node_id for t in low_battery] + [t.node_id for t in no_generator]))
        insights.append(AIInsight(
            id=f"rule-power-resilience-{int(now.timestamp())}",
            timestamp=now,
            insight_type=InsightType.ANOMALY_FORECAST,
            severity="warning" if len(no_generator) > 5 else "info",
            title="Power Resilience Alert",
            description=f"{len(low_battery)} nodes have <4 hours battery backup. {len(no_generator)} Critical SLA nodes lack generator backup. Power grid failures could cause extended outages.",
            recommendation="Upgrade battery capacity for low-backup nodes. Install generators at Critical SLA sites.",
            confidence=0.80,
            affected_node_ids=affected,
            expires_at=now + timedelta(days=1),
        ))

    # ============================================
    # 8. EQUIPMENT COMPONENT HEALTH ANALYSIS
    # ============================================
    if equipment_sensors:
        critical_components = []
        degraded_components = []
        low_remaining_life = []

        for sensor in equipment_sensors:
            for comp in sensor.get("component_health", []):
                if comp["status"] in ("critical", "failed"):
                    critical_components.append({
                        "node_id": sensor["node_id"],
                        "component": f"{comp['component_name']} ({comp['component_type']})",
                        "health": comp["health_score"],
                        "status": comp["status"],
                        "remaining_days": comp["estimated_remaining_life_days"],
                    })
                elif comp["status"] == "degraded":
                    degraded_components.append({
                        "node_id": sensor["node_id"],
                        "component": f"{comp['component_name']} ({comp['component_type']})",
                        "health": comp["health_score"],
                        "remaining_days": comp["estimated_remaining_life_days"],
                    })

                if comp["estimated_remaining_life_days"] < 30 and comp["status"] != "failed":
                    low_remaining_life.append({
                        "node_id": sensor["node_id"],
                        "component": f"{comp['component_name']} ({comp['component_type']})",
                        "remaining_days": comp["estimated_remaining_life_days"],
                    })

        # Critical/Failed Components Insight
        if critical_components:
            affected_node_ids = list(set(c["node_id"] for c in critical_components))
            component_breakdown: Dict[str, int] = defaultdict(int)
            for c in critical_components:
                comp_type = c["component"].split("(")[1].rstrip(")") if "(" in c["component"] else "unknown"
                component_breakdown[comp_type] += 1
            breakdown_str = ", ".join(f"{k}: {v}" for k, v in component_breakdown.items())

            top_affected = "\n".join(
                f"- {c['node_id']}: {c['component']} - {c['health']:.0f}% health ({c['status']})"
                for c in critical_components[:5]
            )

            insights.append(AIInsight(
                id=f"rule-critical-components-{int(now.timestamp())}",
                timestamp=now,
                insight_type=InsightType.ROOT_CAUSE,
                severity="critical",
                title=f"Critical Equipment Components: {len(critical_components)}",
                description=f"{len(critical_components)} equipment components are in critical or failed state across {len(affected_node_ids)} nodes.\n\nComponent breakdown: {breakdown_str}\n\nTop affected:\n{top_affected}",
                recommendation="Immediate replacement required for failed components. Schedule emergency maintenance for critical components. Prioritize by SLA tier.",
                confidence=0.95,
                affected_node_ids=affected_node_ids,
                metadata={
                    "criticalComponents": critical_components[:20],
                    "componentBreakdown": dict(component_breakdown),
                },
                expires_at=now + timedelta(hours=1),
            ))

        # Degraded Components Insight
        if degraded_components:
            affected_node_ids = list(set(c["node_id"] for c in degraded_components))
            avg_health = sum(c["health"] for c in degraded_components) / len(degraded_components)
            sample = "\n".join(
                f"- {c['node_id']}: {c['component']} - {c['health']:.0f}% health"
                for c in degraded_components[:5]
            )

            insights.append(AIInsight(
                id=f"rule-degraded-components-{int(now.timestamp())}",
                timestamp=now,
                insight_type=InsightType.ANOMALY_FORECAST,
                severity="warning" if len(degraded_components) > 20 else "info",
                title=f"Degraded Equipment Components: {len(degraded_components)}",
                description=f"{len(degraded_components)} components showing degraded performance across {len(affected_node_ids)} nodes. Average health: {avg_health:.1f}%.\n\nSample:\n{sample}",
                recommendation="Schedule preventive maintenance for degraded components before they reach critical state. Order replacement parts.",
                confidence=0.85,
                affected_node_ids=affected_node_ids,
                metadata={"degradedComponents": degraded_components[:20]},
                expires_at=now + timedelta(hours=6),
            ))

        # Predictive: Components with low remaining life
        if low_remaining_life:
            affected_node_ids = list(set(c["node_id"] for c in low_remaining_life))
            urgent_count = len([c for c in low_remaining_life if c["remaining_days"] < 7])
            week_count = len([c for c in low_remaining_life if 7 <= c["remaining_days"] < 14])
            month_count = len([c for c in low_remaining_life if c["remaining_days"] >= 14])

            urgent_list = "\n".join(
                f"- {c['node_id']}: {c['component']} - {c['remaining_days']} days remaining"
                for c in low_remaining_life if c["remaining_days"] < 7
            )[:500]  # Limit description length

            insights.append(AIInsight(
                id=f"rule-predictive-failures-{int(now.timestamp())}",
                timestamp=now,
                insight_type=InsightType.ANOMALY_FORECAST,
                severity="critical" if urgent_count > 0 else "warning",
                title=f"Predicted Equipment Failures: {len(low_remaining_life)} Components",
                description=f"Predictive analysis indicates {len(low_remaining_life)} components approaching end-of-life across {len(affected_node_ids)} nodes.\n\nTimeline:\n- <7 days (URGENT): {urgent_count} components\n- 7-14 days: {week_count} components\n- 14-30 days: {month_count} components\n\nMost urgent:\n{urgent_list}",
                recommendation="Order replacement parts immediately for urgent components. Schedule maintenance windows. Pre-position spares at regional depots.",
                confidence=0.82,
                affected_node_ids=affected_node_ids,
                metadata={
                    "predictedFailures": low_remaining_life,
                    "urgentCount": urgent_count,
                    "weekCount": week_count,
                    "monthCount": month_count,
                },
                expires_at=now + timedelta(hours=4),
            ))

        # Equipment Error Log Analysis
        high_error_nodes = [s for s in equipment_sensors if s.get("error_log_count", 0) > 50]
        if high_error_nodes:
            top_errors = "\n".join(
                f"- {s['node_id']}: {s['error_log_count']} errors, {s['warning_log_count']} warnings"
                for s in sorted(high_error_nodes, key=lambda x: x.get("error_log_count", 0), reverse=True)[:5]
            )
            avg_errors = sum(s.get("error_log_count", 0) for s in high_error_nodes) / len(high_error_nodes)

            insights.append(AIInsight(
                id=f"rule-error-logs-{int(now.timestamp())}",
                timestamp=now,
                insight_type=InsightType.PATTERN_DETECTED,
                severity="warning" if len(high_error_nodes) > 10 else "info",
                title=f"High Error Log Count: {len(high_error_nodes)} Nodes",
                description=f"{len(high_error_nodes)} nodes have >50 errors in the last 24 hours.\n\nTop error producers:\n{top_errors}\n\nAverage errors: {avg_errors:.0f}",
                recommendation="Review error logs for patterns. Check for firmware issues or environmental factors causing repeated errors.",
                confidence=0.78,
                affected_node_ids=[s["node_id"] for s in high_error_nodes],
                expires_at=now + timedelta(hours=2),
            ))

        # Firmware Version Analysis
        firmware_versions: Dict[str, List[str]] = defaultdict(list)
        for s in equipment_sensors:
            if s.get("firmware_version"):
                firmware_versions[s["firmware_version"]].append(s["node_id"])

        if len(firmware_versions) > 1:
            sorted_versions = sorted(firmware_versions.items(), key=lambda x: len(x[1]), reverse=True)
            latest_version = sorted_versions[0][0]
            outdated_nodes = [nid for v, nids in sorted_versions[1:] for nid in nids]

            version_dist = "\n".join(
                f"- {v}: {len(ids)} nodes ({(len(ids) / len(equipment_sensors)) * 100:.1f}%)"
                for v, ids in sorted_versions
            )

            if outdated_nodes:
                insights.append(AIInsight(
                    id=f"rule-firmware-versions-{int(now.timestamp())}",
                    timestamp=now,
                    insight_type=InsightType.PATTERN_DETECTED,
                    severity="warning" if len(outdated_nodes) > len(equipment_sensors) * 0.3 else "info",
                    title=f"Firmware Version Inconsistency: {len(firmware_versions)} Versions",
                    description=f"{len(firmware_versions)} different firmware versions detected across {len(equipment_sensors)} nodes.\n\nVersion distribution:\n{version_dist}\n\n{len(outdated_nodes)} nodes not on latest version ({latest_version}).",
                    recommendation=f"Plan firmware upgrade for nodes not on {latest_version}. Test in staging environment first. Schedule during maintenance windows.",
                    confidence=0.75,
                    affected_node_ids=outdated_nodes,
                    metadata={
                        "firmwareVersions": {v: ids for v, ids in firmware_versions.items()},
                        "latestVersion": latest_version,
                    },
                    expires_at=now + timedelta(days=1),
                ))

    # ============================================
    # 9. RF PLANT SIGNAL ANALYSIS
    # ============================================
    if rf_plant_sensors:
        signal_issues = []
        for s in rf_plant_sensors:
            has_issue = False
            issue_details = []
            if s.get("ds_snr_db", 99) < 33:
                has_issue = True
                issue_details.append(f"DS SNR {s['ds_snr_db']:.1f} dB (threshold: 33 dB)")
            if s.get("us_snr_db", 99) < 25:
                has_issue = True
                issue_details.append(f"US SNR {s['us_snr_db']:.1f} dB (threshold: 25 dB)")
            if s.get("fec_uncorrected_codewords", 0) > 100:
                has_issue = True
                issue_details.append(f"FEC uncorrected: {s['fec_uncorrected_codewords']}")
            if has_issue:
                signal_issues.append({
                    "node_id": s["node_id"],
                    "issues": issue_details,
                    "ds_snr_db": s.get("ds_snr_db", 0),
                    "us_snr_db": s.get("us_snr_db", 0),
                    "fec_uncorrected": s.get("fec_uncorrected_codewords", 0),
                })

        if signal_issues:
            worst_cases = "\n".join(
                f"- {si['node_id']}: {'; '.join(si['issues'])}"
                for si in sorted(signal_issues, key=lambda x: x.get("ds_snr_db", 99))[:5]
            )

            insights.append(AIInsight(
                id=f"rule-rf-signal-quality-{int(now.timestamp())}",
                timestamp=now,
                insight_type=InsightType.ANOMALY_FORECAST,
                severity="warning" if len(signal_issues) > 10 else "info",
                title=f"RF Signal Quality Issues: {len(signal_issues)} Nodes",
                description=f"{len(signal_issues)} nodes showing RF signal quality degradation (DS SNR <33 dB, US SNR <25 dB, or high FEC uncorrected codewords).\n\nWorst cases:\n{worst_cases}\n\nThis can cause service degradation and increased subscriber complaints.",
                recommendation="Schedule signal level adjustment and plant maintenance. Check for ingress, loose connectors, or damaged coax. Inspect amplifier cascade for issues.",
                confidence=0.88,
                affected_node_ids=[si["node_id"] for si in signal_issues],
                expires_at=now + timedelta(hours=6),
            ))

        # RF plant health issues (check ingress detection)
        rf_ingress_issues = [s for s in rf_plant_sensors if s.get("fec_uncorrected_codewords", 0) > 500]
        if rf_ingress_issues:
            critical_cases = [s for s in rf_ingress_issues if s.get("fec_uncorrected_codewords", 0) > 2000]
            critical_list = "\n".join(
                f"- {s['node_id']}: {s.get('fec_uncorrected_codewords', 0)} uncorrected codewords, DS SNR: {s.get('ds_snr_db', 0):.1f} dB"
                for s in critical_cases[:5]
            ) if critical_cases else "None with >2000 uncorrected"
            avg_fec = sum(s.get("fec_uncorrected_codewords", 0) for s in rf_ingress_issues) / len(rf_ingress_issues)

            insights.append(AIInsight(
                id=f"rule-rf-plant-health-{int(now.timestamp())}",
                timestamp=now,
                insight_type=InsightType.ROOT_CAUSE,
                severity="warning" if critical_cases else "info",
                title=f"RF Plant Health Issues: {len(rf_ingress_issues)} Nodes",
                description=f"{len(rf_ingress_issues)} nodes showing significant RF plant health issues (>500 FEC uncorrected codewords).\n\nCritical cases:\n{critical_list}\n\nAverage FEC uncorrected: {avg_fec:.0f}",
                recommendation="Inspect plant for ingress sources, damaged cable, and corroded connectors. Check amplifier pads and equalizers. Schedule plant maintenance for affected nodes.",
                confidence=0.85,
                affected_node_ids=[s["node_id"] for s in rf_ingress_issues],
                expires_at=now + timedelta(hours=6),
            ))

    # ============================================
    # 10. ENVIRONMENTAL SENSOR ANALYSIS
    # ============================================
    if environmental_sensors:
        # Power quality issues
        power_issues = [s for s in environmental_sensors if s.get("power_quality_percent", 100) < 90 or s.get("power_fluctuations_count", 0) > 10]
        if power_issues:
            details = "\n".join(
                f"- {s['node_id']}: Quality {s.get('power_quality_percent', 0):.0f}%, Fluctuations: {s.get('power_fluctuations_count', 0)}/hr"
                for s in power_issues[:5]
            )

            insights.append(AIInsight(
                id=f"rule-power-quality-{int(now.timestamp())}",
                timestamp=now,
                insight_type=InsightType.ANOMALY_FORECAST,
                severity="warning" if len(power_issues) > 15 else "info",
                title=f"Power Quality Issues: {len(power_issues)} Nodes",
                description=f"{len(power_issues)} nodes experiencing power quality issues.\n\nDetails:\n{details}\n\nPoor power quality can cause equipment damage and service interruptions.",
                recommendation="Install UPS or power conditioning equipment. Review utility supply agreements. Consider backup power upgrades.",
                confidence=0.80,
                affected_node_ids=[s["node_id"] for s in power_issues],
                expires_at=now + timedelta(hours=4),
            ))

        # RF ingress/interference issues
        interference_issues = [s for s in environmental_sensors if s.get("ingress_level_dbmv", -60) > -20]
        if interference_issues:
            high_interference = [s for s in interference_issues if s.get("ingress_level_dbmv", -60) > -15]
            high_list = "\n".join(
                f"- {s['node_id']}: {s.get('ingress_level_dbmv', 0):.1f} dBmV ingress level"
                for s in high_interference[:5]
            ) if high_interference else "None above -15 dBmV"

            insights.append(AIInsight(
                id=f"rule-interference-{int(now.timestamp())}",
                timestamp=now,
                insight_type=InsightType.ROOT_CAUSE,
                severity="warning" if len(high_interference) > 5 else "info",
                title=f"RF Ingress Detected: {len(interference_issues)} Nodes",
                description=f"{len(interference_issues)} nodes detecting significant RF ingress (>-20 dBmV).\n\nHigh ingress sites:\n{high_list}\n\nIngress can degrade signal quality and throughput for subscribers.",
                recommendation="Investigate ingress sources (loose connectors, damaged cable, unterminated drops). Check housing seals. Install ingress filters if needed.",
                confidence=0.75,
                affected_node_ids=[s["node_id"] for s in interference_issues],
                expires_at=now + timedelta(hours=4),
            ))

        # Cabinet temperature issues
        temp_issues = [s for s in environmental_sensors if s.get("cabinet_temperature_celsius", 0) > 40]
        if temp_issues:
            critical_temp = [s for s in temp_issues if s.get("cabinet_temperature_celsius", 0) > 50]
            critical_list = "\n".join(
                f"- {s['node_id']}: {s.get('cabinet_temperature_celsius', 0):.1f} C"
                for s in critical_temp[:5]
            ) if critical_temp else "None >50 C"

            insights.append(AIInsight(
                id=f"rule-cabinet-temp-{int(now.timestamp())}",
                timestamp=now,
                insight_type=InsightType.ANOMALY_FORECAST,
                severity="warning" if critical_temp else "info",
                title=f"Cabinet Overheating: {len(temp_issues)} Nodes",
                description=f"{len(temp_issues)} equipment cabinets running hot (>40 C).\n\nCritical temperatures:\n{critical_list}\n\nOverheating accelerates equipment degradation and can cause failures.",
                recommendation="Check cooling systems and air filters. Consider additional cooling capacity. Ensure proper ventilation around cabinets.",
                confidence=0.85,
                affected_node_ids=[s["node_id"] for s in temp_issues],
                expires_at=now + timedelta(hours=2),
            ))

    # ============================================
    # 11. REGIONAL CASCADE RISK ANALYSIS
    # ============================================
    alerts_by_region: Dict[str, List[Alert]] = defaultdict(list)
    for alert in alerts:
        node = next((t for t in nodes if t.node_id == alert.node_id), None)
        if node:
            alerts_by_region[node.region].append(alert)

    for region, region_alerts in alerts_by_region.items():
        region_nodes = [t for t in nodes if t.region == region]
        if not region_nodes:
            continue
        alert_rate = (len(region_alerts) / len(region_nodes)) * 100
        critical_count = len([a for a in region_alerts if a.severity == "critical"])

        if len(region_alerts) >= 3 or alert_rate > 10:
            insights.append(AIInsight(
                id=f"rule-cascade-{region}-{int(now.timestamp())}",
                timestamp=now,
                insight_type=InsightType.ANOMALY_FORECAST,
                severity="critical" if critical_count >= 2 else "warning",
                title=f"Cascade Risk Alert: {region}",
                description=f"High alert concentration detected in {region}. {len(region_alerts)} active alerts affecting {alert_rate:.1f}% of nodes ({len(region_alerts)}/{len(region_nodes)}). {critical_count} critical, {len(region_alerts) - critical_count} warning. Adjacent node failures may cause subscriber impact and service degradation.",
                recommendation=f"Prioritize {region} region. Consider proactive load balancing to neighboring regions. Monitor plant capacity. Have field crews on standby for {region}.",
                confidence=0.85,
                affected_node_ids=[a.node_id for a in region_alerts],
                related_alert_ids=[a.alert_id for a in region_alerts],
                expires_at=now + timedelta(hours=1),
            ))

    # ============================================
    # 12. MANUFACTURER PATTERN ANALYSIS
    # ============================================
    alerts_by_manufacturer: Dict[str, Dict[str, Any]] = defaultdict(lambda: {"alerts": [], "nodes": set()})
    for alert in alerts:
        node = next((t for t in nodes if t.node_id == alert.node_id), None)
        if node:
            alerts_by_manufacturer[node.manufacturer]["alerts"].append(alert)
            alerts_by_manufacturer[node.manufacturer]["nodes"].add(node.node_id)

    for manufacturer, data in alerts_by_manufacturer.items():
        manufacturer_nodes = [t for t in nodes if t.manufacturer == manufacturer]
        if not manufacturer_nodes:
            continue
        alert_rate = (len(data["alerts"]) / len(manufacturer_nodes)) * 100

        if len(data["alerts"]) >= 3 and alert_rate > 5:
            models = set()
            for a in data["alerts"]:
                node = next((t for t in nodes if t.node_id == a.node_id), None)
                if node and node.hardware_model:
                    models.add(node.hardware_model)

            insights.append(AIInsight(
                id=f"rule-manufacturer-{manufacturer.replace(' ', '_')}-{int(now.timestamp())}",
                timestamp=now,
                insight_type=InsightType.PATTERN_DETECTED,
                severity="critical" if alert_rate > 15 else "warning",
                title=f"{manufacturer} Equipment Pattern",
                description=f"Pattern detected across {manufacturer} equipment: {len(data['alerts'])} alerts on {len(data['nodes'])} nodes ({alert_rate:.1f}% of {manufacturer} fleet). Models affected: {', '.join(models)}. This may indicate a firmware issue, batch defect, or shared vulnerability.",
                recommendation=f"Review {manufacturer} firmware versions. Check for vendor advisories. Consider scheduling preventive maintenance for {manufacturer} equipment in affected regions.",
                confidence=0.80,
                affected_node_ids=list(data["nodes"]),
                related_alert_ids=[a.alert_id for a in data["alerts"]],
                expires_at=now + timedelta(hours=2),
            ))

    # ============================================
    # 13. ALERT TYPE CONCENTRATION
    # ============================================
    alerts_by_type: Dict[str, List[Alert]] = defaultdict(list)
    for alert in alerts:
        alerts_by_type[alert.type].append(alert)

    for alert_type, type_alerts in alerts_by_type.items():
        if len(type_alerts) >= 3:
            regions: Set[str] = set()
            for a in type_alerts:
                node = next((t for t in nodes if t.node_id == a.node_id), None)
                if node:
                    regions.add(node.region)

            insights.append(AIInsight(
                id=f"rule-type-{alert_type.replace(' ', '_')}-{int(now.timestamp())}",
                timestamp=now,
                insight_type=InsightType.ROOT_CAUSE,
                severity="critical" if len([a for a in type_alerts if a.severity == "critical"]) >= 2 else "warning",
                title=f"{alert_type.replace('_', ' ')} Pattern",
                description=f"Multiple {alert_type.replace('_', ' ').lower()} incidents: {len(type_alerts)} occurrences across {len(regions)} regions ({', '.join(regions)}). This suggests a systemic issue requiring coordinated response rather than individual node remediation.",
                recommendation="Investigate common root cause. Check for network-wide configuration changes, weather events, or external interference affecting this alert type.",
                confidence=0.75,
                affected_node_ids=[a.node_id for a in type_alerts],
                related_alert_ids=[a.alert_id for a in type_alerts],
                expires_at=now + timedelta(hours=2),
            ))

    # ============================================
    # 14. SELF-HEALING EFFECTIVENESS ANALYSIS
    # ============================================
    completed_actions = [a for a in actions if a.status == "COMPLETED"]
    failed_actions = [a for a in actions if a.status == "FAILED"]
    total_processed = len(completed_actions) + len(failed_actions)
    success_rate = (len(completed_actions) / total_processed) * 100 if total_processed > 0 else 0

    # Build self-healing effectiveness chart
    effectiveness_chart = InsightChartData(
        type="line",
        title="30-Day Self-Healing Effectiveness",
        x_axis_label="Date",
        y_axis_label="Success Rate %",
        data=[
            ChartDataPoint(
                date=d["date"],
                value=(d["completed"] / d["total"]) * 100 if d["total"] > 0 else 100,
                label=f"{(d['completed'] / d['total']) * 100:.1f}%" if d["total"] > 0 else "100%"
            )
            for d in daily_actions
        ],
        series=[
            ChartSeries(name="Completed", data=[ChartDataPoint(date=d["date"], value=d["completed"], label=str(d["completed"])) for d in daily_actions]),
            ChartSeries(name="Failed", data=[ChartDataPoint(date=d["date"], value=d["failed"], label=str(d["failed"])) for d in daily_actions]),
        ]
    )

    # Average effectiveness
    avg_effectiveness = sum(d["avgEffectiveness"] for d in daily_actions) / len(daily_actions) if daily_actions else 0

    insights.append(AIInsight(
        id=f"rule-healing-effectiveness-{int(now.timestamp())}",
        timestamp=now,
        insight_type=InsightType.PATTERN_DETECTED,
        severity="critical" if success_rate < 70 else "warning" if success_rate < 85 else "info",
        title=f"Self-Healing Effectiveness: {success_rate:.1f}%",
        description=f"30-day self-healing performance:\n- Completed: {len(completed_actions)} actions\n- Failed: {len(failed_actions)} actions\n- Success Rate: {success_rate:.1f}%\n- Total Actions: {total_processed}\n\nAvg Effectiveness Score: {avg_effectiveness:.1f}%",
        recommendation=(
            "Self-healing system is performing well. Continue monitoring for edge cases."
            if success_rate >= 85 else
            "Some remediation actions are failing. Review failed action types and root causes."
            if success_rate >= 70 else
            "Self-healing effectiveness is below target. Investigate systematic issues in automated remediation."
        ),
        confidence=0.92,
        affected_node_ids=list(set(a.node_id for a in actions)),
        related_alert_ids=list(set(a.alert_id for a in actions if a.alert_id)),
        metadata={
            "charts": [effectiveness_chart.to_dict()],
            "thirtyDayStats": {
                "successRate": success_rate,
                "completedActions": len(completed_actions),
                "failedActions": len(failed_actions),
                "totalActions": total_processed,
                "dailyBreakdown": daily_actions,
            },
        },
        expires_at=now + timedelta(hours=1),
    ))

    # Additional insight for failed actions if significant
    if len(failed_actions) >= 2:
        affected_node_ids = list(set(a.node_id for a in failed_actions))
        action_types = set(a.action_type for a in failed_actions if a.action_type)

        insights.append(AIInsight(
            id=f"rule-failed-actions-{int(now.timestamp())}",
            timestamp=now,
            insight_type=InsightType.ROOT_CAUSE,
            severity="warning",
            title="Automated Remediation Failures",
            description=f"{len(failed_actions)} self-healing actions have failed on {len(affected_node_ids)} nodes. Action types: {', '.join(action_types)}. Automated remediation may be insufficient for these issues.",
            recommendation="Manual intervention required. Dispatch field crews to affected sites. Review action logs to determine why automated remediation failed.",
            confidence=0.90,
            affected_node_ids=affected_node_ids,
            related_alert_ids=[a.alert_id for a in failed_actions if a.alert_id],
            expires_at=now + timedelta(hours=2),
        ))

    # ============================================
    # 15. CRITICAL ALERTS SUMMARY
    # ============================================
    critical_alerts = [a for a in alerts if a.severity == "critical"]
    if critical_alerts:
        alert_types = set(a.type for a in critical_alerts if a.type)
        insights.append(AIInsight(
            id=f"rule-critical-alerts-{int(now.timestamp())}",
            timestamp=now,
            insight_type=InsightType.ROOT_CAUSE,
            severity="critical" if len(critical_alerts) >= 3 else "warning",
            title=f"Critical Alerts Active: {len(critical_alerts)}",
            description=f"{len(critical_alerts)} critical alerts require immediate attention. Alert types: {', '.join(alert_types)}.",
            recommendation="Prioritize resolution of critical alerts. Escalate to on-call engineers if automated remediation fails.",
            confidence=0.95,
            affected_node_ids=[a.node_id for a in critical_alerts],
            related_alert_ids=[a.alert_id for a in critical_alerts],
            expires_at=now + timedelta(minutes=30),
        ))

    print(f"Generated {len(insights)} rule-based insights")
    return insights


def get_cached_insights(
    db: Session,
    max_age_minutes: int = 60,
) -> List[AIInsight]:
    """
    Get cached insights from database if available and not expired.
    Returns empty list if no valid cache exists.
    """
    # This will be implemented when we add the AIInsight model
    # For now, return empty list to regenerate insights
    return []


def cache_insights(db: Session, insights: List[AIInsight]) -> None:
    """
    Cache insights to database for future retrieval.
    """
    # This will be implemented when we add the AIInsight model
    pass
