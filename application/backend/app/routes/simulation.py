"""Digital Twin / Simulation endpoints"""
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, func, case
from typing import Optional, List
from datetime import datetime, timedelta
from ..config import settings
from ..database import get_db
from ..models import (
    FiberNodeModel, KPIMetricsModel, AlertModel, SelfHealingActionModel,
    SimulationScenarioModel, SimulationResultModel, SLAConfigModel,
)
from ..schemas import (
    SimulationScenario, SimulationScenarioCreate, SimulationScenarioListResponse,
    SimulationResult, SimulationResultListResponse, RunSimulationRequest, SimulationComparisonResponse,
    HistoricalBaselines, SimilarHistoricalIncident, SimulationHistoricalContext,
)
from ..historical_analytics import (
    get_historical_baselines, get_historical_alert_patterns,
    get_similar_historical_incidents, get_historical_kpi_averages,
)
from . import safe_error_response, logger

router = APIRouter(prefix=settings.API_V1_STR, tags=["simulation"])


# ===== DIGITAL TWIN / SIMULATION ENDPOINTS =====

@router.get("/simulation/scenarios", response_model=SimulationScenarioListResponse)
def get_simulation_scenarios(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    scenario_type: Optional[str] = Query(None, description="Filter by type: failure, capacity, maintenance, disaster"),
    db: Session = Depends(get_db),
):
    """
    Get saved simulation scenarios.
    """
    query = select(SimulationScenarioModel)

    if scenario_type:
        query = query.where(SimulationScenarioModel.scenario_type == scenario_type)

    query = query.order_by(SimulationScenarioModel.created_at.desc())

    # Get total count
    count_query = select(func.count()).select_from(query.alias())
    total = db.execute(count_query).scalar()

    # Get paginated results
    query = query.offset(skip).limit(limit)
    scenarios = db.execute(query).scalars().all()

    return SimulationScenarioListResponse(
        total=total,
        page=skip // limit + 1,
        page_size=limit,
        items=scenarios,
    )


@router.post("/simulation/scenarios", response_model=SimulationScenario)
def create_simulation_scenario(
    scenario_data: SimulationScenarioCreate,
    db: Session = Depends(get_db),
):
    """
    Create a new simulation scenario.
    """
    scenario = SimulationScenarioModel(
        scenario_id=f"scenario-{uuid.uuid4().hex[:8]}",
        **scenario_data.model_dump()
    )
    db.add(scenario)
    db.commit()
    db.refresh(scenario)

    return scenario


@router.post("/simulation/run", response_model=SimulationResult)
def run_simulation(
    request: RunSimulationRequest,
    db: Session = Depends(get_db),
):
    """
    Run a network simulation (Digital Twin).

    Simulates impact of various scenarios with extended parameters:
    - failure: Node/equipment failures
    - capacity: Traffic surge scenarios
    - maintenance: Planned maintenance impact
    - disaster: Regional disaster scenarios

    Extended parameters:
    - region: Filter by geographic region
    - time_of_day: peak (1.5x load) or off_peak (0.7x load)
    - node_types: List of node types to target (N+0, N+1, N+2, N+3)
    - cascading_failure: Enable cascading failure modeling
    - recovery_strategy: manual or ai_assisted
    - custom_sla_uptime: Custom uptime threshold for SLA calculation
    - custom_sla_latency: Custom latency threshold
    - backhaul_capacity_percent: Backhaul connection capacity (0-100)
    - datacenter_latency_ms: Additional datacenter latency
    - network_congestion_factor: Network congestion multiplier (1.0-3.0)
    - packet_loss_percent: Simulated packet loss rate
    """
    import random

    scenario_type = request.scenario_type or "failure"
    target_nodes = request.target_nodes or []
    parameters = request.parameters or {}

    # Extract extended parameters
    region_filter = parameters.get("region")
    time_of_day = parameters.get("time_of_day", "normal")  # peak, off_peak, normal
    node_types = parameters.get("node_types", [])  # ["5G", "LTE", "3G"]
    cascading_failure = parameters.get("cascading_failure", False)
    recovery_strategy = parameters.get("recovery_strategy", "manual")  # manual, ai_assisted
    custom_sla_uptime = parameters.get("custom_sla_uptime")  # e.g., 99.5
    custom_sla_latency = parameters.get("custom_sla_latency")  # e.g., 50ms

    # Network connectivity parameters
    backhaul_capacity_percent = parameters.get("backhaul_capacity_percent", 100)  # 0-100
    datacenter_latency_ms = parameters.get("datacenter_latency_ms", 0)  # Additional DC latency
    network_congestion_factor = parameters.get("network_congestion_factor", 1.0)  # 1.0-3.0
    packet_loss_percent = parameters.get("packet_loss_percent", 0)  # 0-100

    # Consolidated node count query (2 queries → 1)
    node_query = select(
        func.count(FiberNodeModel.id).label('total'),
        func.sum(case((FiberNodeModel.status != 'OUTAGE', 1), else_=0)).label('healthy'),
    )
    if region_filter:
        node_query = node_query.where(FiberNodeModel.region == region_filter)
    if node_types:
        node_query = node_query.where(FiberNodeModel.node_type.in_(node_types))

    node_counts = db.execute(node_query).one()
    total_nodes = node_counts.total or 1000
    if total_nodes == 0:
        fallback = db.execute(select(func.count(FiberNodeModel.id))).scalar() or 1000
        total_nodes = fallback
    healthy_nodes = node_counts.healthy or 0

    current_uptime = (healthy_nodes / total_nodes) * 100 if total_nodes > 0 else 100

    # Get baseline KPI averages from historical data (7 days) for more robust baselines
    # This uses aggregated tables for efficiency and more representative averages
    use_historical_baseline = parameters.get("use_historical_baseline", True)

    if use_historical_baseline:
        try:
            # Use historical averages from aggregated tables (default: 168 hours = 7 days)
            historical_baselines = get_historical_kpi_averages(db, period_hours=168)
            baseline_latency = historical_baselines.get("latency_ms", 25.0)
            baseline_throughput = historical_baselines.get("downstream_throughput_mbps", 150.0)
            baseline_call_drop = historical_baselines.get("packet_loss_percent", 1.5)
            baseline_users = historical_baselines.get("active_modems", 500.0)
            baseline_data_source = historical_baselines.get("data_source", "historical")
        except Exception as e:
            logger.warning(f"Failed to get historical baselines, falling back to recent data: {e}")
            use_historical_baseline = False

    if not use_historical_baseline:
        # Fallback to recent KPIs (last hour)
        recent_kpis = db.execute(
            select(
                func.avg(KPIMetricsModel.latency_ms),
                func.avg(KPIMetricsModel.downstream_throughput_mbps),
                func.avg(KPIMetricsModel.packet_loss_percent),
                func.avg(KPIMetricsModel.active_modems)
            ).where(KPIMetricsModel.timestamp >= datetime.now() - timedelta(hours=1))
        ).first()

        baseline_latency = float(recent_kpis[0]) if recent_kpis[0] else 25.0
        baseline_throughput = float(recent_kpis[1]) if recent_kpis[1] else 150.0
        baseline_call_drop = float(recent_kpis[2]) if recent_kpis[2] else 1.5
        baseline_users = float(recent_kpis[3]) if recent_kpis[3] else 500.0
        baseline_data_source = "kpi_metrics (recent)"

    # Apply time of day modifier to baseline
    time_multiplier = 1.0
    if time_of_day == "peak":
        time_multiplier = 1.5
        baseline_users *= 1.5
        baseline_latency *= 1.2
    elif time_of_day == "off_peak":
        time_multiplier = 0.7
        baseline_users *= 0.6
        baseline_latency *= 0.8

    # Determine number of nodes affected
    if target_nodes:
        nodes_affected = len(target_nodes)
    else:
        nodes_affected = max(1, int(total_nodes * parameters.get("affected_percent", 5) / 100))

    # Apply cascading failure model
    cascade_multiplier = 1.0
    if cascading_failure:
        # Cascading failures affect 20-50% more nodes over time
        cascade_multiplier = 1.0 + random.uniform(0.2, 0.5)
        nodes_affected = min(total_nodes, int(nodes_affected * cascade_multiplier))

    # Calculate simulated impact based on scenario type
    if scenario_type == "failure":
        uptime_impact = (nodes_affected / total_nodes) * 100
        latency_impact = 1 + (nodes_affected / total_nodes) * 0.5
        throughput_impact = 1 - (nodes_affected / total_nodes) * 0.3
        call_drop_impact = 1 + (nodes_affected / total_nodes) * 2

    elif scenario_type == "capacity":
        surge_factor = parameters.get("surge_factor", 1.5)
        uptime_impact = (nodes_affected / total_nodes) * 10 * (surge_factor - 1)
        latency_impact = surge_factor
        throughput_impact = 1 / surge_factor
        call_drop_impact = surge_factor

    elif scenario_type == "maintenance":
        uptime_impact = (nodes_affected / total_nodes) * 100
        latency_impact = 1.1
        throughput_impact = 0.95
        call_drop_impact = 1.05

    elif scenario_type == "disaster":
        severity = parameters.get("severity", 0.5)
        uptime_impact = (nodes_affected / total_nodes) * 100 * severity * 2
        latency_impact = 1 + severity * 2
        throughput_impact = 1 - severity * 0.7
        call_drop_impact = 1 + severity * 5

    elif scenario_type == "capacity_planning":
        # Capacity Planning - uses LLM to analyze trends and forecast capacity needs
        import asyncio
        from ..capacity_planner import run_capacity_planning

        print(f"Running capacity planning analysis...")

        # Run the async capacity planning
        loop = asyncio.new_event_loop()
        try:
            planning_result = loop.run_until_complete(
                run_capacity_planning(db, parameters)
            )
        finally:
            loop.close()

        # Generate a unique ID for the result
        max_result_id = db.execute(select(func.max(SimulationResultModel.id))).scalar() or 0
        new_result_id = max_result_id + 1

        # Build recommendations from planning result
        recommended_actions = [
            {"action": rec, "priority": i + 1}
            for i, rec in enumerate(planning_result.recommendations)
        ]

        # Determine overall risk level from forecasts
        risk_score = 0
        if planning_result.forecasts:
            risk_levels = {"low": 20, "medium": 50, "high": 75, "critical": 95}
            for forecast in planning_result.forecasts:
                if isinstance(forecast, dict):
                    risk_score = max(risk_score, risk_levels.get(forecast.get("risk_level", "low"), 20))

        # Create result with capacity planning specific metrics
        result = SimulationResultModel(
            id=new_result_id,
            result_id=f"result-{uuid.uuid4().hex[:8]}",
            scenario_id=f"adhoc-capacity_planning",
            simulation_start=datetime.now(),
            baseline_metrics={
                "node_utilization": round(planning_result.current_node_capacity_utilization, 1),
                "dc_utilization": round(planning_result.current_dc_capacity_utilization, 1),
                "bandwidth_utilization": round(planning_result.current_bandwidth_utilization_percent, 1),
                "total_active_modems": planning_result.total_active_modems,
                "total_throughput_gbps": planning_result.total_throughput_gbps,
                "data_source": ", ".join(planning_result.data_sources_used),
            },
            simulated_metrics={
                "scenario_type": "capacity_planning",
                "trend_direction": planning_result.trend_direction,
                "growth_rate_percent_per_month": planning_result.growth_rate_percent_per_month,
                "forecasts": planning_result.forecasts,
                "bandwidth_bottlenecks": planning_result.bandwidth_bottlenecks,
                "capacity_constraints": planning_result.capacity_constraints,
                "current_node_utilization": round(planning_result.current_node_capacity_utilization, 1),
                "current_dc_utilization": round(planning_result.current_dc_capacity_utilization, 1),
                "current_bandwidth_utilization": round(planning_result.current_bandwidth_utilization_percent, 1),
                "total_active_modems": planning_result.total_active_modems,
                "total_throughput_gbps": planning_result.total_throughput_gbps,
                "analysis_time_ms": planning_result.analysis_time_ms,
            },
            affected_nodes=[],
            affected_node_count=total_nodes,
            affected_customers_estimated=planning_result.total_active_modems,
            affected_regions=[region_filter] if region_filter else [],
            cascading_failures=[],
            projected_revenue_loss=0,  # Capacity planning doesn't project revenue loss
            projected_sla_breaches=len(planning_result.bandwidth_bottlenecks),
            estimated_recovery_time_minutes=0,
            recommended_actions=recommended_actions,
            risk_score=risk_score,
            executive_summary=(
                f"Capacity Planning Analysis: {planning_result.trend_direction.title()} trend detected. "
                f"Growth rate: {planning_result.growth_rate_percent_per_month:.1f}%/month. "
                f"Node utilization: {planning_result.current_node_capacity_utilization:.1f}%, "
                f"DC utilization: {planning_result.current_dc_capacity_utilization:.1f}%. "
                f"Total throughput: {planning_result.total_throughput_gbps:.2f} Gbps. "
                f"{planning_result.llm_analysis}"
            ),
        )

        db.add(result)
        db.commit()
        db.refresh(result)

        return result

    else:
        uptime_impact = 1.0
        latency_impact = 1.0
        throughput_impact = 1.0
        call_drop_impact = 1.0

    # Apply network connectivity impacts
    # Backhaul capacity reduction increases latency and reduces throughput
    if backhaul_capacity_percent < 100:
        backhaul_factor = backhaul_capacity_percent / 100
        throughput_impact *= backhaul_factor
        latency_impact *= (2 - backhaul_factor)  # Lower capacity = higher latency

    # Datacenter latency adds directly to latency
    dc_latency_impact = datacenter_latency_ms

    # Network congestion affects all metrics
    if network_congestion_factor > 1.0:
        latency_impact *= network_congestion_factor
        throughput_impact /= network_congestion_factor
        call_drop_impact *= (1 + (network_congestion_factor - 1) * 0.5)

    # Packet loss affects call quality significantly
    if packet_loss_percent > 0:
        call_drop_impact *= (1 + packet_loss_percent / 10)
        throughput_impact *= (1 - packet_loss_percent / 100)

    # Calculate simulated metrics
    simulated_uptime = max(0, current_uptime - uptime_impact)
    simulated_latency = baseline_latency * latency_impact + dc_latency_impact
    simulated_throughput = max(0, baseline_throughput * throughput_impact)
    simulated_call_drop = min(100, baseline_call_drop * call_drop_impact)
    simulated_packet_loss = min(100, packet_loss_percent + (100 - simulated_uptime) * 0.1)

    # Get SLA config for financial calculations
    config = db.execute(select(SLAConfigModel).where(SLAConfigModel.id == 1)).scalar_one_or_none()
    cost_per_minute = config.cost_per_outage_minute if config else 1000.0
    revenue_per_user = config.revenue_per_subscriber_per_hour if config else 0.50

    # Use custom SLA thresholds if provided
    sla_uptime_target = custom_sla_uptime if custom_sla_uptime else (config.uptime_target_percent if config else 99.9)
    sla_latency_target = custom_sla_latency if custom_sla_latency else (config.max_latency_ms if config else 50.0)

    # Estimate duration based on recovery strategy
    estimated_duration_hours = parameters.get("duration_hours", 2)
    if recovery_strategy == "ai_assisted":
        # AI-assisted recovery is 40% faster
        estimated_duration_hours *= 0.6
        recovery_time_minutes = int(estimated_duration_hours * 60)
    else:
        recovery_time_minutes = int(estimated_duration_hours * 60)

    # Revenue loss calculation
    users_affected = nodes_affected * 500 * time_multiplier
    projected_revenue_loss = users_affected * revenue_per_user * estimated_duration_hours

    # SLA breach risk based on custom thresholds
    uptime_breach_risk = max(0, (sla_uptime_target - simulated_uptime) / sla_uptime_target * 100)
    latency_breach_risk = max(0, (simulated_latency - sla_latency_target) / sla_latency_target * 100)
    sla_breach_risk = min(100, max(uptime_breach_risk, latency_breach_risk))

    # Capacity utilization during incident
    remaining_nodes = total_nodes - nodes_affected
    capacity_utilization = min(100, (total_nodes / remaining_nodes) * 100) if remaining_nodes > 0 else 100

    # Calculate backhaul utilization
    backhaul_utilization = min(100, (100 / backhaul_capacity_percent) * 100 * network_congestion_factor) if backhaul_capacity_percent > 0 else 100

    # Generate context-aware recommendations
    recommendations = []

    # Node-related recommendations
    if nodes_affected > 10:
        recommendations.append(f"Pre-position {min(nodes_affected, 20)} mobile service units for rapid deployment")
    recommendations.append("Activate traffic steering to neighboring nodes")

    # Recovery strategy recommendations
    if recovery_strategy == "ai_assisted":
        recommendations.append(f"AI-assisted recovery enabled - estimated {recovery_time_minutes} min resolution")
        recommendations.append("Autonomous healing will attempt parameter optimization and remote restart")
    else:
        recommendations.append(f"Manual recovery estimated at {recovery_time_minutes} min - consider AI-assisted mode")
        recommendations.append("Dispatch field crews to affected sites")

    # Cascading failure recommendations
    if cascading_failure:
        recommendations.append(f"Cascading failure model active - {int((cascade_multiplier - 1) * 100)}% additional impact expected")
        recommendations.append("Implement circuit breakers to isolate affected network segments")

    # Network connectivity recommendations
    if backhaul_capacity_percent < 80:
        recommendations.append(f"Backhaul at {backhaul_capacity_percent}% capacity - activate backup links")
    if datacenter_latency_ms > 20:
        recommendations.append(f"High DC latency ({datacenter_latency_ms}ms) - consider edge caching activation")
    if network_congestion_factor > 1.5:
        recommendations.append(f"Network congestion at {network_congestion_factor:.1f}x - implement QoS traffic shaping")
    if packet_loss_percent > 2:
        recommendations.append(f"Packet loss at {packet_loss_percent}% - check physical layer and routing")

    # Time-based recommendations
    if time_of_day == "peak":
        recommendations.append("Peak hours simulation - prioritize voice traffic and critical services")
    elif time_of_day == "off_peak":
        recommendations.append("Off-peak window - optimal time for maintenance activities")

    # Region-specific recommendations
    if region_filter:
        recommendations.append(f"Regional impact limited to {region_filter} - coordinate with regional NOC")

    # Generate a unique ID for the result
    max_result_id = db.execute(select(func.max(SimulationResultModel.id))).scalar() or 0
    new_result_id = max_result_id + 1

    # Build affected node list (simulate which nodes are affected)
    affected_node_ids = []
    if target_nodes:
        affected_node_ids = target_nodes
    else:
        # Get random node IDs for simulation
        sample_nodes = db.execute(
            select(FiberNodeModel.node_id).limit(nodes_affected)
        ).scalars().all()
        affected_node_ids = list(sample_nodes)

    # Build recommendations as list of dicts for JSON storage
    recommended_actions = [{"action": rec, "priority": i + 1} for i, rec in enumerate(recommendations)]

    # Create result with extended metrics
    result = SimulationResultModel(
        id=new_result_id,
        result_id=f"result-{uuid.uuid4().hex[:8]}",
        scenario_id=f"adhoc-{scenario_type}",
        simulation_start=datetime.now(),
        baseline_metrics={
            "uptime_percent": round(current_uptime, 2),
            "latency_ms": round(baseline_latency, 2),
            "throughput_mbps": round(baseline_throughput, 2),
            "packet_loss_percent": round(baseline_call_drop, 2),
            "active_modems": round(baseline_users, 0),
            "backhaul_capacity": 100,
            "datacenter_latency_ms": 0,
            "packet_loss_percent": 0,
            "data_source": baseline_data_source,
        },
        simulated_metrics={
            "uptime_percent": round(simulated_uptime, 2),
            "latency_ms": round(simulated_latency, 2),
            "throughput_mbps": round(simulated_throughput, 2),
            "packet_loss_percent": round(simulated_call_drop, 2),
            "users_affected": int(users_affected),
            "packet_loss_percent": round(simulated_packet_loss, 2),
            "backhaul_utilization": round(backhaul_utilization, 1),
            "recovery_time_minutes": recovery_time_minutes,
            "cascade_impact": round((cascade_multiplier - 1) * 100, 1) if cascading_failure else 0,
            "capacity_utilization": round(capacity_utilization, 1),
            "scenario_type": scenario_type,
        },
        affected_nodes=affected_node_ids,
        affected_node_count=nodes_affected,
        affected_customers_estimated=int(users_affected),
        affected_regions=[region_filter] if region_filter else [],
        cascading_failures=[] if not cascading_failure else [f"cascade-impact-{int((cascade_multiplier - 1) * 100)}pct"],
        projected_revenue_loss=round(projected_revenue_loss, 2),
        projected_sla_breaches=1 if sla_breach_risk > 50 else 0,
        estimated_recovery_time_minutes=recovery_time_minutes,
        recommended_actions=recommended_actions,
        risk_score=int(min(100, sla_breach_risk)),
        executive_summary=f"{scenario_type.title()} scenario affecting {nodes_affected} nodes ({nodes_affected/total_nodes*100:.1f}%). "
                          f"Uptime: {round(simulated_uptime, 2)}%, Latency: {round(simulated_latency, 1)}ms. "
                          f"Revenue at risk: ${round(projected_revenue_loss, 0):,.0f}. "
                          f"Recovery: {recovery_time_minutes} min ({recovery_strategy}).",
    )

    db.add(result)
    db.commit()
    db.refresh(result)

    return result


@router.get("/simulation/results", response_model=SimulationResultListResponse)
def get_simulation_results(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    scenario_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """
    Get historical simulation results.
    """
    query = select(SimulationResultModel)

    if scenario_type:
        # Filter by scenario_id which contains the scenario type
        query = query.where(SimulationResultModel.scenario_id.contains(scenario_type))

    query = query.order_by(SimulationResultModel.created_at.desc())

    # Get total count
    count_query = select(func.count()).select_from(query.alias())
    total = db.execute(count_query).scalar()

    # Get paginated results
    query = query.offset(skip).limit(limit)
    results = db.execute(query).scalars().all()

    return SimulationResultListResponse(
        total=total,
        items=results,
    )


@router.delete("/simulation/results/{result_id}")
def delete_simulation_result(
    result_id: str,
    db: Session = Depends(get_db),
):
    """
    Delete a single simulation result by ID.
    """
    result = db.execute(
        select(SimulationResultModel).where(SimulationResultModel.result_id == result_id)
    ).scalar_one_or_none()

    if not result:
        raise HTTPException(status_code=404, detail=f"Simulation result {result_id} not found")

    db.delete(result)
    db.commit()

    return {"message": f"Simulation result {result_id} deleted successfully"}


@router.post("/simulation/results/delete-batch")
def delete_simulation_results_batch(
    result_ids: List[str],
    db: Session = Depends(get_db),
):
    """
    Delete multiple simulation results by IDs.
    Pass an array of result_ids in the request body.
    """
    if not result_ids:
        raise HTTPException(status_code=400, detail="No result IDs provided")

    deleted_count = 0
    for result_id in result_ids:
        result = db.execute(
            select(SimulationResultModel).where(SimulationResultModel.result_id == result_id)
        ).scalar_one_or_none()
        if result:
            db.delete(result)
            deleted_count += 1

    db.commit()

    return {
        "message": f"Deleted {deleted_count} simulation result(s)",
        "deleted_count": deleted_count,
        "requested_count": len(result_ids),
    }


@router.get("/simulation/compare", response_model=SimulationComparisonResponse)
def compare_simulations(
    result_ids: List[str] = Query(..., description="List of result IDs to compare"),
    db: Session = Depends(get_db),
):
    """
    Compare multiple simulation results side by side.
    """
    if len(result_ids) < 2:
        raise HTTPException(status_code=400, detail="At least 2 result IDs required for comparison")

    results = []
    for result_id in result_ids:
        query = select(SimulationResultModel).where(SimulationResultModel.result_id == result_id)
        result = db.execute(query).scalar_one_or_none()
        if result:
            results.append(result)

    if len(results) < 2:
        raise HTTPException(status_code=404, detail="Not enough valid results found for comparison")

    # Calculate comparison metrics
    comparison_metrics = {
        "worst_uptime": min(r.simulated_metrics.get("uptime_percent", 100) for r in results),
        "highest_revenue_loss": max(r.projected_revenue_loss for r in results),
        "highest_sla_risk": max(r.risk_score for r in results),
        "most_affected_nodes": max(r.affected_node_count for r in results),
    }

    return SimulationComparisonResponse(
        results=results,
        comparison_metrics=comparison_metrics,
    )


@router.get("/simulation/historical-context", response_model=SimulationHistoricalContext)
def get_simulation_historical_context(
    scenario_type: str = Query("failure", description="Scenario type: failure, capacity, maintenance, disaster"),
    affected_nodes: int = Query(10, ge=1, le=1000, description="Number of nodes to be affected"),
    period_hours: int = Query(168, ge=24, le=720, description="Historical period to analyze (default: 7 days)"),
    db: Session = Depends(get_db),
):
    """
    Get historical context to inform Digital Twin simulations.

    Returns historical baselines, similar past incidents, and alert patterns
    to improve simulation accuracy and provide comparison data.

    The confidence score indicates how reliable the historical data is:
    - High (>0.8): Sufficient historical data for accurate baselines
    - Medium (0.5-0.8): Limited data, estimates may be less accurate
    - Low (<0.5): Minimal historical data, using defaults

    This endpoint is used by the Digital Twin to:
    1. Set realistic baseline metrics from historical averages
    2. Compare simulation results with similar past incidents
    3. Calibrate failure probabilities from historical patterns
    """
    try:
        # Get historical baselines
        baselines_data = get_historical_baselines(db, period_hours)
        baselines = HistoricalBaselines(
            kpi_baselines=baselines_data.get("kpi_baselines", {}),
            incident_baselines=baselines_data.get("incident_baselines", {}),
            network_baselines=baselines_data.get("network_baselines", {}),
            period_hours=period_hours,
            calculated_at=baselines_data.get("calculated_at", datetime.now().isoformat()),
        )

        # Get similar historical incidents
        similar_data = get_similar_historical_incidents(db, scenario_type, affected_nodes, limit=5)
        similar_incidents = [SimilarHistoricalIncident(**inc) for inc in similar_data]

        # Get historical alert patterns
        alert_patterns = get_historical_alert_patterns(db, period_hours)

        # Check data availability in aggregated tables
        from ..models import KPIMetrics1MinModel, KPIMetrics5MinModel, KPIMetricsHourlyModel, KPIMetricsDailyModel

        data_availability = {}
        for model, name in [
            (KPIMetrics1MinModel, "1min"),
            (KPIMetrics5MinModel, "5min"),
            (KPIMetricsHourlyModel, "hourly"),
            (KPIMetricsDailyModel, "daily"),
        ]:
            count = db.execute(select(func.count(model.id))).scalar() or 0
            data_availability[name] = {
                "records": count,
                "has_data": count > 0,
            }

        # Calculate confidence score based on data availability
        total_samples = baselines_data.get("kpi_baselines", {}).get("total_samples", 0)
        similar_count = len(similar_incidents)

        if total_samples > 1000 and similar_count >= 3:
            confidence_score = 0.9
        elif total_samples > 100 and similar_count >= 1:
            confidence_score = 0.7
        elif total_samples > 10:
            confidence_score = 0.5
        else:
            confidence_score = 0.3

        return SimulationHistoricalContext(
            baselines=baselines,
            similar_incidents=similar_incidents,
            alert_patterns=alert_patterns,
            data_availability=data_availability,
            confidence_score=confidence_score,
        )

    except Exception as e:
        logger.error(f"Failed to get simulation historical context: {e}")
        # Return minimal context on error
        return SimulationHistoricalContext(
            baselines=HistoricalBaselines(
                kpi_baselines={},
                incident_baselines={},
                network_baselines={},
                period_hours=period_hours,
                calculated_at=datetime.now().isoformat(),
            ),
            similar_incidents=[],
            alert_patterns={},
            data_availability={},
            confidence_score=0.1,
        )
