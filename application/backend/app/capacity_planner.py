"""
Capacity Planning Module - LLM-powered bandwidth and capacity forecasting for Digital Twin.

Analyzes current node and data center utilization, trend data, and provides
capacity forecasts for 30/60/90 days with bandwidth projections and bottleneck identification.
"""

import json
import re
import time
import random
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

from sqlalchemy.orm import Session
from sqlalchemy import select, func

from .models import FiberNodeModel, KPIMetricsModel, LLMConfigModel
from .historical_analytics import get_kpi_trends, get_historical_kpi_averages, calculate_period_comparison
from .llm_queue import llm_queue


@dataclass
class CapacityForecast:
    """Capacity forecast for a specific time period"""
    period_days: int
    projected_node_utilization: float
    projected_dc_utilization: float
    projected_bandwidth_usage_gbps: float
    confidence: float
    risk_level: str  # low, medium, high, critical


@dataclass
class CapacityPlanningResult:
    """Complete capacity planning analysis result"""
    analysis_timestamp: str

    # Current State
    current_node_capacity_utilization: float
    current_dc_capacity_utilization: float
    current_bandwidth_utilization_percent: float
    total_active_modems: int
    total_throughput_gbps: float

    # Trend Analysis
    trend_direction: str  # growing, stable, declining
    growth_rate_percent_per_month: float

    # Forecasts
    forecasts: List[Dict[str, Any]]

    # Bottlenecks
    bandwidth_bottlenecks: List[Dict[str, Any]]
    capacity_constraints: List[Dict[str, Any]]

    # LLM Analysis
    llm_analysis: str
    recommendations: List[str]

    # Metadata
    data_sources_used: List[str]
    analysis_time_ms: int


# Geographic regions (matching main.py)
GEOGRAPHIC_REGIONS = ["Northeast", "Southeast", "Midwest", "Southwest", "West", "Northwest"]


def get_llm_config(db: Session) -> Optional[Dict[str, Any]]:
    """Get the current LLM configuration from database"""
    query = select(LLMConfigModel).where(LLMConfigModel.id == 1)
    result = db.execute(query)
    config = result.scalar_one_or_none()

    if not config or not config.enabled:
        return None

    return {
        "provider": config.provider,
        "endpoint_url": config.endpoint_url,
        "api_key": config.api_key,
        "jwt_token": config.jwt_token,
        "model_name": config.model_name,
        "temperature": config.temperature,
        "max_tokens": config.max_tokens,
    }


def gather_node_capacity_data(db: Session, region: Optional[str] = None) -> Dict[str, Any]:
    """
    Gather capacity-related data from fiber nodes.

    Returns aggregated node metrics including capacity, backhaul, and utilization.
    """
    # Build node query
    node_query = select(FiberNodeModel)
    if region and region in GEOGRAPHIC_REGIONS:
        node_query = node_query.where(FiberNodeModel.region == region)

    nodes = db.execute(node_query).scalars().all()

    if not nodes:
        return {
            "total_nodes": 0,
            "total_capacity": 0,
            "total_backhaul_mbps": 0,
            "avg_throughput_mbps": 0,
            "avg_active_modems": 0,
            "avg_cpu_utilization": 0,
            "avg_memory_utilization": 0,
            "nodes_by_status": {},
            "nodes_by_technology": {},
        }

    # Calculate aggregates
    total_capacity = sum(getattr(t, 'capacity', 500) for t in nodes)
    total_backhaul = sum(getattr(t, 'backhaul_capacity_mbps', 1000) for t in nodes)

    # Count by status
    status_counts = {}
    for t in nodes:
        status = getattr(t, 'status', 'healthy')
        # Handle case where status might be a list
        if isinstance(status, list):
            status = status[0] if status else 'healthy'
        status_counts[status] = status_counts.get(status, 0) + 1

    # Count by technology
    tech_counts = {}
    for t in nodes:
        tech = getattr(t, 'technology', 'LTE')
        # Handle case where technology might be a list
        if isinstance(tech, list):
            tech = tech[0] if tech else 'LTE'
        tech_counts[tech] = tech_counts.get(tech, 0) + 1

    # Get recent KPIs for actual utilization (24 hours)
    try:
        kpi_averages = get_historical_kpi_averages(db, period_hours=24)
    except Exception:
        kpi_averages = {}

    return {
        "total_nodes": len(nodes),
        "total_capacity": total_capacity,
        "total_backhaul_mbps": total_backhaul,
        "avg_throughput_mbps": kpi_averages.get("downstream_throughput_mbps", 150.0),
        "avg_active_modems": kpi_averages.get("active_modems", 500.0),
        "avg_cpu_utilization": kpi_averages.get("node_cpu_utilization", 45.0),
        "avg_memory_utilization": kpi_averages.get("node_memory_utilization", 55.0),
        "avg_latency_ms": kpi_averages.get("latency_ms", 25.0),
        "nodes_by_status": status_counts,
        "nodes_by_technology": tech_counts,
    }


def gather_datacenter_capacity_data(db: Session, region: Optional[str] = None) -> Dict[str, Any]:
    """
    Gather capacity data from data centers.

    Generates data center metrics matching the /core-network/data-centers endpoint structure.
    """
    # Simulate DC data similar to the endpoint in main.py
    # In a real implementation, this would query actual DC data
    random.seed(42)  # Consistent results

    dc_count = 12 if not region else 2

    # Aggregate metrics across data centers
    total_uplinks_gbps = dc_count * random.choice([100, 200, 400])
    avg_network_utilization = random.uniform(45, 75)
    avg_cpu_utilization = random.uniform(40, 70)
    avg_memory_utilization = random.uniform(45, 75)
    avg_storage_utilization = random.uniform(50, 80)

    # Calculate used vs available capacity
    used_capacity_gbps = total_uplinks_gbps * (avg_network_utilization / 100)

    return {
        "total_data_centers": dc_count,
        "total_uplinks_gbps": total_uplinks_gbps,
        "used_capacity_gbps": round(used_capacity_gbps, 2),
        "avg_network_utilization_percent": round(avg_network_utilization, 1),
        "avg_cpu_utilization": round(avg_cpu_utilization, 1),
        "avg_memory_utilization": round(avg_memory_utilization, 1),
        "avg_storage_utilization": round(avg_storage_utilization, 1),
        "peak_hour_utilization": round(avg_network_utilization * 1.3, 1),  # 30% higher during peak
    }


def build_capacity_planning_prompt(
    node_data: Dict[str, Any],
    dc_data: Dict[str, Any],
    trend_data: List[Dict[str, Any]],
    comparisons: List[Dict[str, Any]],
) -> List[Dict[str, str]]:
    """Build the LLM prompt for capacity planning analysis."""

    system_prompt = """You are an expert telecommunications network capacity planner. Your role is to analyze current network utilization data from fiber nodes and data centers to provide accurate capacity forecasts.

You must respond with ONLY a valid JSON object (no markdown, no explanation outside JSON) containing:
{
    "trend_direction": "growing|stable|declining",
    "growth_rate_percent_per_month": <number>,
    "forecasts": [
        {
            "period_days": 30,
            "projected_node_utilization": <percent 0-100>,
            "projected_dc_utilization": <percent 0-100>,
            "projected_bandwidth_usage_gbps": <number>,
            "confidence": <0.0-1.0>,
            "risk_level": "low|medium|high|critical"
        },
        {
            "period_days": 60,
            "projected_node_utilization": <percent>,
            "projected_dc_utilization": <percent>,
            "projected_bandwidth_usage_gbps": <number>,
            "confidence": <0.0-1.0>,
            "risk_level": "low|medium|high|critical"
        },
        {
            "period_days": 90,
            "projected_node_utilization": <percent>,
            "projected_dc_utilization": <percent>,
            "projected_bandwidth_usage_gbps": <number>,
            "confidence": <0.0-1.0>,
            "risk_level": "low|medium|high|critical"
        }
    ],
    "bandwidth_bottlenecks": [
        {"location": "region or component name", "current_utilization": <percent>, "projected_breach_days": <number or null if no breach>}
    ],
    "capacity_constraints": [
        {"resource": "cpu|memory|bandwidth|storage", "affected_components": ["list of affected"], "severity": "low|medium|high"}
    ],
    "analysis_summary": "2-3 sentence detailed analysis of current state and projections",
    "recommendations": ["Specific actionable recommendation 1", "Recommendation 2", "Recommendation 3"]
}

Risk Level Guidelines:
- low: utilization < 60%, no constraints
- medium: utilization 60-75%, minor constraints
- high: utilization 75-85%, significant constraints
- critical: utilization > 85%, immediate action needed

Bottleneck Identification:
- Flag any component with utilization > 70% as a potential bottleneck
- Estimate days until breach based on growth rate

Note: "node" refers to fiber nodes in the cable/ISP network."""

    # Build context with actual data
    context = f"""
=== NODE CAPACITY DATA ===
- Total Fiber Nodes: {node_data.get('total_nodes', 0):,}
- Total Node Capacity: {node_data.get('total_capacity', 0):,} users
- Total Backhaul Capacity: {node_data.get('total_backhaul_mbps', 0):,.0f} Mbps
- Current Avg Throughput: {node_data.get('avg_throughput_mbps', 0):.1f} Mbps per node
- Current Avg Active Modems: {node_data.get('avg_active_modems', 0):.0f} per node
- Avg CPU Utilization: {node_data.get('avg_cpu_utilization', 0):.1f}%
- Avg Memory Utilization: {node_data.get('avg_memory_utilization', 0):.1f}%
- Avg Latency: {node_data.get('avg_latency_ms', 0):.1f} ms

Node Status Distribution:
"""
    for status, count in node_data.get('nodes_by_status', {}).items():
        context += f"  - {status}: {count} nodes\n"

    context += f"""
=== DATA CENTER CAPACITY DATA ===
- Total Data Centers: {dc_data.get('total_data_centers', 0)}
- Total Network Uplinks: {dc_data.get('total_uplinks_gbps', 0)} Gbps
- Current Used Capacity: {dc_data.get('used_capacity_gbps', 0):.1f} Gbps
- Avg Network Utilization: {dc_data.get('avg_network_utilization_percent', 0):.1f}%
- Peak Hour Utilization: {dc_data.get('peak_hour_utilization', 0):.1f}%
- Avg CPU Utilization: {dc_data.get('avg_cpu_utilization', 0):.1f}%
- Avg Memory Utilization: {dc_data.get('avg_memory_utilization', 0):.1f}%
- Avg Storage Utilization: {dc_data.get('avg_storage_utilization', 0):.1f}%
"""

    # Add trend data
    if trend_data and len(trend_data) >= 2:
        first = trend_data[0]
        last = trend_data[-1]
        context += f"""
=== 7-DAY TREND DATA ===
Throughput: {first.get('throughput_mbps', 0):.1f} -> {last.get('throughput_mbps', 0):.1f} Mbps
Active Modems: {first.get('active_modems', 0):.0f} -> {last.get('active_modems', 0):.0f}
CPU Utilization: {first.get('cpu_utilization', 0):.1f}% -> {last.get('cpu_utilization', 0):.1f}%
Memory Utilization: {first.get('memory_utilization', 0):.1f}% -> {last.get('memory_utilization', 0):.1f}%
Latency: {first.get('avg_latency', 0):.1f} -> {last.get('avg_latency', 0):.1f} ms
"""

    # Add period comparisons
    if comparisons:
        context += "\n=== WEEK-OVER-WEEK COMPARISON ===\n"
        for comp in comparisons[:6]:  # Top 6 metrics
            context += f"- {comp.get('metric_name', 'Unknown')}: {comp.get('change_percent', 0):.1f}% ({comp.get('trend', 'stable')})\n"

    context += "\nAnalyze this data and provide capacity forecasts in the specified JSON format."

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": context},
    ]


def parse_capacity_response(response_content: str) -> Dict[str, Any]:
    """Parse LLM response JSON, handling various formats."""
    try:
        # Try direct JSON parse
        return json.loads(response_content)
    except json.JSONDecodeError:
        pass

    # Try to extract JSON from markdown code block
    json_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', response_content)
    if json_match:
        try:
            return json.loads(json_match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # Try to find JSON object in response
    json_match = re.search(r'\{[\s\S]*\}', response_content)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass

    # Return empty dict if parsing fails
    return {}


def generate_rule_based_capacity_plan(
    node_data: Dict[str, Any],
    dc_data: Dict[str, Any],
    trend_data: List[Dict[str, Any]],
) -> CapacityPlanningResult:
    """
    Generate a rule-based capacity plan when LLM is unavailable.
    Uses heuristics based on current utilization and trends.
    """
    # Calculate current utilization
    node_cpu = node_data.get('avg_cpu_utilization', 50.0)
    node_mem = node_data.get('avg_memory_utilization', 55.0)
    dc_net = dc_data.get('avg_network_utilization_percent', 60.0)
    dc_cpu = dc_data.get('avg_cpu_utilization', 50.0)

    # Estimate growth from trend data
    growth_rate = 2.5  # Default 2.5% per month
    trend_direction = "stable"

    if trend_data and len(trend_data) >= 2:
        first_throughput = trend_data[0].get('throughput_mbps', 100)
        last_throughput = trend_data[-1].get('throughput_mbps', 100)
        if first_throughput > 0:
            weekly_change = ((last_throughput - first_throughput) / first_throughput) * 100
            growth_rate = weekly_change * 4  # Extrapolate to monthly
            if weekly_change > 2:
                trend_direction = "growing"
            elif weekly_change < -2:
                trend_direction = "declining"

    # Generate forecasts
    forecasts = []
    current_bandwidth = dc_data.get('used_capacity_gbps', 100.0)

    for days in [30, 60, 90]:
        months = days / 30
        projected_growth = 1 + (growth_rate / 100) * months

        proj_node = min(95, node_cpu * projected_growth)
        proj_dc = min(95, dc_net * projected_growth)
        proj_bw = current_bandwidth * projected_growth

        # Determine risk level
        max_util = max(proj_node, proj_dc)
        if max_util > 85:
            risk = "critical"
        elif max_util > 75:
            risk = "high"
        elif max_util > 60:
            risk = "medium"
        else:
            risk = "low"

        forecasts.append({
            "period_days": days,
            "projected_node_utilization": round(proj_node, 1),
            "projected_dc_utilization": round(proj_dc, 1),
            "projected_bandwidth_usage_gbps": round(proj_bw, 2),
            "confidence": 0.7 - (days / 300),  # Confidence decreases over time
            "risk_level": risk,
        })

    # Identify bottlenecks
    bottlenecks = []
    if dc_net > 70:
        bottlenecks.append({
            "location": "Data Center Network",
            "current_utilization": dc_net,
            "projected_breach_days": int((85 - dc_net) / (growth_rate / 30)) if growth_rate > 0 else None,
        })
    if node_cpu > 70:
        bottlenecks.append({
            "location": "Node CPU",
            "current_utilization": node_cpu,
            "projected_breach_days": int((85 - node_cpu) / (growth_rate / 30)) if growth_rate > 0 else None,
        })

    # Identify constraints
    constraints = []
    if dc_cpu > 65:
        constraints.append({
            "resource": "cpu",
            "affected_components": ["Data Centers"],
            "severity": "medium" if dc_cpu < 75 else "high",
        })
    if node_mem > 70:
        constraints.append({
            "resource": "memory",
            "affected_components": ["Fiber Nodes"],
            "severity": "medium" if node_mem < 80 else "high",
        })

    # Generate recommendations
    recommendations = []
    if trend_direction == "growing":
        recommendations.append("Plan for capacity expansion within 60 days based on current growth trends")
    if dc_net > 70:
        recommendations.append(f"Data center network utilization at {dc_net:.1f}% - consider adding uplink capacity")
    if node_cpu > 65:
        recommendations.append("Evaluate load balancing across nodes to distribute CPU load")
    if not recommendations:
        recommendations.append("Current capacity is adequate - continue monitoring trends")

    return CapacityPlanningResult(
        analysis_timestamp=datetime.utcnow().isoformat(),
        current_node_capacity_utilization=node_cpu,
        current_dc_capacity_utilization=dc_net,
        current_bandwidth_utilization_percent=dc_net,
        total_active_modems=int(node_data.get('avg_active_modems', 500) * node_data.get('total_nodes', 100)),
        total_throughput_gbps=round(node_data.get('avg_throughput_mbps', 150) * node_data.get('total_nodes', 100) / 1000, 2),
        trend_direction=trend_direction,
        growth_rate_percent_per_month=round(growth_rate, 1),
        forecasts=forecasts,
        bandwidth_bottlenecks=bottlenecks,
        capacity_constraints=constraints,
        llm_analysis=f"Rule-based analysis: {trend_direction.title()} trend detected with {growth_rate:.1f}% monthly growth rate.",
        recommendations=recommendations,
        data_sources_used=["kpi_metrics", "fiber_nodes", "rule_based_estimation"],
        analysis_time_ms=0,
    )


async def run_capacity_planning(
    db: Session,
    parameters: Dict[str, Any],
    timeout_seconds: float = 120.0,
) -> CapacityPlanningResult:
    """
    Execute capacity planning analysis with LLM.

    Gathers data from nodes and data centers, analyzes trends,
    and uses LLM to generate capacity forecasts.
    """
    start_time = time.time()

    region = parameters.get("region")

    # Gather data from all sources
    print(f"Gathering node capacity data...")
    node_data = gather_node_capacity_data(db, region)

    print(f"Gathering data center capacity data...")
    dc_data = gather_datacenter_capacity_data(db, region)

    print(f"Getting KPI trends (7 days)...")
    try:
        trend_data = get_kpi_trends(db, period_hours=168, max_points=50)
    except Exception as e:
        print(f"Warning: Could not get trend data: {e}")
        trend_data = []

    print(f"Calculating period comparisons...")
    try:
        comparisons = calculate_period_comparison(db, period_hours=168)
    except Exception as e:
        print(f"Warning: Could not calculate comparisons: {e}")
        comparisons = []

    # Check for LLM config
    llm_config = get_llm_config(db)
    if not llm_config:
        print("LLM not configured, using rule-based analysis")
        result = generate_rule_based_capacity_plan(node_data, dc_data, trend_data)
        result.analysis_time_ms = int((time.time() - start_time) * 1000)
        return result

    # Build prompt and call LLM
    print(f"Building LLM prompt for capacity planning...")
    messages = build_capacity_planning_prompt(node_data, dc_data, trend_data, comparisons)

    # Build API request
    provider = llm_config["provider"]
    api_url = llm_config["endpoint_url"]

    # Handle URL construction for different providers
    if provider in ['ollama', 'cloudera', 'custom']:
        if api_url and not api_url.endswith('/chat/completions'):
            if api_url.endswith('/v1'):
                api_url = f"{api_url}/chat/completions"
            elif '/v1' not in api_url:
                api_url = f"{api_url}/v1/chat/completions"

    headers = {"Content-Type": "application/json"}
    if llm_config.get("api_key"):
        headers["Authorization"] = f"Bearer {llm_config['api_key']}"
    elif llm_config.get("jwt_token"):
        headers["Authorization"] = f"Bearer {llm_config['jwt_token']}"

    payload = {
        "messages": messages,
        "temperature": llm_config.get("temperature", 0.7),
        "max_tokens": llm_config.get("max_tokens", 3000),
    }
    if llm_config.get("model_name"):
        payload["model"] = llm_config["model_name"]

    # Submit to LLM queue
    print(f"Submitting to LLM queue (provider: {provider})...")
    try:
        job_id = llm_queue.submit_and_process_parallel(
            messages=messages,
            provider=provider,
            api_url=api_url,
            headers=headers,
            payload=payload,
            priority=3,
        )

        result = llm_queue.wait_for_job(job_id, timeout=timeout_seconds)
    except Exception as e:
        print(f"LLM queue error: {e}, falling back to rule-based")
        result = None

    if not result:
        print("No LLM response, using rule-based analysis")
        fallback = generate_rule_based_capacity_plan(node_data, dc_data, trend_data)
        fallback.analysis_time_ms = int((time.time() - start_time) * 1000)
        return fallback

    # Extract content from LLM response
    response_content = ""
    if isinstance(result, dict):
        if "choices" in result and result["choices"]:
            response_content = result["choices"][0].get("message", {}).get("content", "")
        elif "content" in result:
            response_content = result["content"]
    elif isinstance(result, str):
        response_content = result

    if not response_content:
        print("Empty LLM response, using rule-based analysis")
        fallback = generate_rule_based_capacity_plan(node_data, dc_data, trend_data)
        fallback.analysis_time_ms = int((time.time() - start_time) * 1000)
        return fallback

    # Parse LLM response
    print(f"Parsing LLM response...")
    analysis = parse_capacity_response(response_content)

    if not analysis:
        print("Failed to parse LLM response, using rule-based analysis")
        fallback = generate_rule_based_capacity_plan(node_data, dc_data, trend_data)
        fallback.analysis_time_ms = int((time.time() - start_time) * 1000)
        return fallback

    # Build result from LLM analysis
    return CapacityPlanningResult(
        analysis_timestamp=datetime.utcnow().isoformat(),
        current_node_capacity_utilization=node_data.get("avg_cpu_utilization", 50.0),
        current_dc_capacity_utilization=dc_data.get("avg_network_utilization_percent", 60.0),
        current_bandwidth_utilization_percent=dc_data.get("avg_network_utilization_percent", 60.0),
        total_active_modems=int(node_data.get("avg_active_modems", 500) * node_data.get("total_nodes", 100)),
        total_throughput_gbps=round(node_data.get("avg_throughput_mbps", 150) * node_data.get("total_nodes", 100) / 1000, 2),
        trend_direction=analysis.get("trend_direction", "stable"),
        growth_rate_percent_per_month=analysis.get("growth_rate_percent_per_month", 0),
        forecasts=analysis.get("forecasts", []),
        bandwidth_bottlenecks=analysis.get("bandwidth_bottlenecks", []),
        capacity_constraints=analysis.get("capacity_constraints", []),
        llm_analysis=analysis.get("analysis_summary", ""),
        recommendations=analysis.get("recommendations", []),
        data_sources_used=["kpi_metrics", "fiber_nodes", "data_centers", "llm_analysis"],
        analysis_time_ms=int((time.time() - start_time) * 1000),
    )
