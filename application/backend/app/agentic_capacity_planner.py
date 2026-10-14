"""
Agentic Capacity Planning Module - Multi-agent orchestration for connection upgrade analysis.

Provides a pipeline of specialized agents:
1. Data Collector Agent - Gathers node/DC data by backhaul type
2. Upgrade Analyzer Agent - Calculates bandwidth impact of upgrades
3. Hardware Checker Agent - Checks equipment compatibility
4. Capacity Forecaster Agent - LLM-powered forecasting with upgrade context
"""

import asyncio
import json
import re
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum

from sqlalchemy.orm import Session
from sqlalchemy import select, func

from .models import (
    FiberNodeModel, HeadendModel, CMTSModel, HubModel, NetworkDeviceModel,
    KPIMetricsModel, LLMConfigModel,
    ComponentMetricsHistoryModel, CapacityPlanningExecutionModel
)
from .historical_analytics import get_kpi_trends, get_historical_kpi_averages, calculate_period_comparison
from .llm_queue import llm_queue


# ===== BACKHAUL SPECIFICATIONS =====

BACKHAUL_SPECS = {
    "Fiber": {
        "capacity_mbps": (1000, 10000),
        "avg_capacity_mbps": 5000,
        "latency_ms": 5,
        "reliability_percent": 99.99,
        "cost_per_node": 15000,
        "installation_days": 45,
    },
    "Starlink": {
        "capacity_mbps": (100, 500),
        "avg_capacity_mbps": 250,
        "latency_ms": 40,
        "reliability_percent": 99.5,
        "cost_per_node": 2500,
        "installation_days": 3,
    },
    "Microwave": {
        "capacity_mbps": (100, 1000),
        "avg_capacity_mbps": 500,
        "latency_ms": 15,
        "reliability_percent": 99.9,
        "cost_per_node": 8000,
        "installation_days": 14,
    },
    "Satellite": {
        "capacity_mbps": (10, 100),
        "avg_capacity_mbps": 50,
        "latency_ms": 500,
        "reliability_percent": 99.0,
        "cost_per_node": 5000,
        "installation_days": 7,
    },
    "Copper": {
        "capacity_mbps": (10, 100),
        "avg_capacity_mbps": 50,
        "latency_ms": 20,
        "reliability_percent": 98.5,
        "cost_per_node": 3000,
        "installation_days": 21,
    },
}

# Manufacturer compatibility matrix for upgrades
MANUFACTURER_COMPATIBILITY = {
    "Cisco": {
        "Fiber": "compatible",
        "Starlink": "compatible",
        "Microwave": "compatible",
    },
    "CommScope/Arris": {
        "Fiber": "compatible",
        "Starlink": "partial_upgrade",
        "Microwave": "compatible",
    },
    "Casa Systems": {
        "Fiber": "partial_upgrade",
        "Starlink": "partial_upgrade",
        "Microwave": "compatible",
    },
    "Harmonic": {
        "Fiber": "compatible",
        "Starlink": "compatible",
        "Microwave": "partial_upgrade",
    },
    "Vecima Networks": {
        "Fiber": "partial_upgrade",
        "Starlink": "replacement",
        "Microwave": "compatible",
    },
}

# Cost estimates for compatibility scenarios
COMPATIBILITY_COSTS = {
    "compatible": 0,  # No extra cost
    "partial_upgrade": 2500,  # Card/module upgrade
    "replacement": 12000,  # Full equipment replacement
}


class AgentType(str, Enum):
    DATA_COLLECTOR = "data-collector"
    UPGRADE_ANALYZER = "upgrade-analyzer"
    HARDWARE_CHECKER = "hardware-checker"
    HEADEND_COMPONENT_ANALYZER = "headend-component-analyzer"
    CAPACITY_FORECASTER = "capacity-forecaster"


class ExecutionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ThoughtType(str, Enum):
    THOUGHT = "thought"
    ACTION = "action"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    DATA = "data"
    ANALYSIS = "analysis"
    ERROR = "error"


@dataclass
class AgentThought:
    """A single thought/action from an agent"""
    id: str
    timestamp: str
    agent_id: str
    agent_name: str
    type: str
    content: str
    progress_percent: Optional[float] = None
    data_summary: Optional[Dict[str, Any]] = None


@dataclass
class UpgradeImpactAnalysis:
    """Results from the Upgrade Analyzer Agent"""
    nodes_analyzed: int
    current_total_bandwidth_gbps: float
    projected_total_bandwidth_gbps: float
    bandwidth_improvement_percent: float
    current_avg_latency_ms: float
    projected_avg_latency_ms: float
    latency_improvement_percent: float
    nodes_by_current_backhaul: Dict[str, int]
    upgrade_target: str
    users_to_benefit: int


@dataclass
class HardwareCompatibilityReport:
    """Results from the Hardware Checker Agent"""
    total_nodes_checked: int
    compatible_count: int
    partial_upgrade_count: int
    replacement_count: int
    compatibility_by_manufacturer: Dict[str, Dict[str, int]]
    estimated_total_cost: float
    estimated_upgrade_cost: float
    estimated_replacement_cost: float
    cost_breakdown_by_manufacturer: Dict[str, float]
    installation_timeline_days: int


@dataclass
class ComponentStatus:
    """Status of a single datacenter component"""
    component_id: str
    component_type: str  # CMTS, Hub, NetworkDevice
    name: str
    status: str
    utilization_percent: float
    capacity_current: float
    capacity_max: float
    performance_score: float  # 0-100
    issues: List[str]
    upgrade_priority: str  # low, medium, high, critical
    recommended_action: str
    estimated_cost: float
    # Location info for regional grouping
    location: str = ""
    region: str = ""
    # Historical trend data
    trend_direction: str = "unknown"  # increasing, decreasing, stable, unknown
    growth_rate_per_week: float = 0.0
    growth_rate_per_month: float = 0.0
    avg_utilization_7d: float = 0.0
    avg_utilization_30d: float = 0.0
    peak_utilization_7d: float = 0.0
    projected_days_to_threshold: Optional[int] = None
    performance_trend: str = "stable"  # degrading, stable, improving


@dataclass
class SiteAnalysis:
    """Analysis for a single site/datacenter"""
    dc_id: str
    name: str
    city: str
    status: str
    total_components: int
    components_by_type: Dict[str, int]
    health_score: float
    critical_count: int
    high_count: int
    issues: List[str]
    power_utilization_percent: float
    rack_utilization_percent: float
    avg_growth_per_week: float
    avg_growth_per_month: float
    recommendations: List[str]


@dataclass
class DatacenterComponentAnalysis:
    """Results from the Datacenter Component Analyzer Agent"""
    datacenter_id: str
    datacenter_name: str
    total_components: int
    components_by_type: Dict[str, int]
    components: List[ComponentStatus]
    overall_health_score: float  # 0-100
    critical_issues: List[str]
    upgrade_recommendations: List[Dict[str, Any]]
    estimated_total_upgrade_cost: float
    priority_upgrades: List[str]
    # Site-level breakdown
    sites: List[Dict[str, Any]] = field(default_factory=list)
    # Regional breakdown
    issues_by_location: Dict[str, List[str]] = field(default_factory=dict)
    components_by_location: Dict[str, int] = field(default_factory=dict)
    health_by_location: Dict[str, float] = field(default_factory=dict)
    growth_by_location: Dict[str, Dict[str, Any]] = field(default_factory=dict)


@dataclass
class AgenticCapacityPlanningExecution:
    """State of an agentic capacity planning execution"""
    execution_id: str
    status: str
    started_at: str
    completed_at: Optional[str] = None
    current_agent: Optional[str] = None
    current_agent_name: Optional[str] = None
    progress_percent: float = 0.0
    thoughts: List[AgentThought] = field(default_factory=list)

    # Request parameters
    analysis_mode: str = "current_state"
    target_backhaul_type: Optional[str] = None
    current_backhaul_filter: List[str] = field(default_factory=list)
    region: Optional[str] = None
    city: Optional[str] = None
    datacenter_ids: List[str] = field(default_factory=list)
    node_ids: List[str] = field(default_factory=list)
    include_nodes: bool = True
    include_datacenters: bool = True
    include_cost_estimate: bool = True
    forecast_periods: List[int] = field(default_factory=lambda: [30, 60, 90])

    # Agent outputs
    data_collector_output: Optional[Dict[str, Any]] = None
    upgrade_analysis: Optional[UpgradeImpactAnalysis] = None
    hardware_compatibility: Optional[HardwareCompatibilityReport] = None
    datacenter_analysis: Optional[DatacenterComponentAnalysis] = None

    # Final result
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# In-memory cache for active executions (also persisted to DB for multi-worker support)
_executions: Dict[str, AgenticCapacityPlanningExecution] = {}


def save_execution_to_db(db: Session, execution: AgenticCapacityPlanningExecution):
    """Persist execution state to database for multi-worker access."""
    try:
        # Check if record exists
        db_record = db.execute(
            select(CapacityPlanningExecutionModel).where(
                CapacityPlanningExecutionModel.execution_id == execution.execution_id
            )
        ).scalars().first()

        if db_record:
            # Update existing
            db_record.status = execution.status
            db_record.current_agent = execution.current_agent
            db_record.current_agent_name = execution.current_agent_name
            db_record.progress_percent = execution.progress_percent
            db_record.thoughts = [asdict(t) for t in execution.thoughts]
            db_record.data_collector_output = execution.data_collector_output
            db_record.upgrade_analysis = asdict(execution.upgrade_analysis) if execution.upgrade_analysis else None
            db_record.hardware_compatibility = asdict(execution.hardware_compatibility) if execution.hardware_compatibility else None
            db_record.datacenter_analysis = asdict(execution.datacenter_analysis) if execution.datacenter_analysis else None
            db_record.result = execution.result
            db_record.error = execution.error
            if execution.completed_at:
                db_record.completed_at = datetime.fromisoformat(execution.completed_at)
        else:
            # Create new
            db_record = CapacityPlanningExecutionModel(
                execution_id=execution.execution_id,
                status=execution.status,
                started_at=datetime.fromisoformat(execution.started_at) if execution.started_at else datetime.utcnow(),
                current_agent=execution.current_agent,
                current_agent_name=execution.current_agent_name,
                progress_percent=execution.progress_percent,
                analysis_mode=execution.analysis_mode,
                target_backhaul_type=execution.target_backhaul_type,
                current_backhaul_filter=execution.current_backhaul_filter,
                region=execution.region,
                city=execution.city,
                datacenter_ids=execution.datacenter_ids,
                node_ids=execution.node_ids,
                include_nodes=execution.include_nodes,
                include_datacenters=execution.include_datacenters,
                include_cost_estimate=execution.include_cost_estimate,
                thoughts=[asdict(t) for t in execution.thoughts],
            )
            db.add(db_record)

        db.commit()
    except Exception as e:
        # Safe rollback - only if session is still active and not in invalid state
        try:
            if db.is_active:
                db.rollback()
        except Exception:
            pass  # Session already closed or in invalid state
        print(f"Error saving execution to DB: {e}")


def load_execution_from_db(db: Session, execution_id: str) -> Optional[Dict[str, Any]]:
    """Load execution state from database."""
    db_record = db.execute(
        select(CapacityPlanningExecutionModel).where(
            CapacityPlanningExecutionModel.execution_id == execution_id
        )
    ).scalars().first()

    if not db_record:
        return None

    return {
        "execution_id": db_record.execution_id,
        "status": db_record.status,
        "started_at": db_record.started_at.isoformat() if db_record.started_at else None,
        "completed_at": db_record.completed_at.isoformat() if db_record.completed_at else None,
        "current_agent": db_record.current_agent,
        "current_agent_name": db_record.current_agent_name,
        "progress_percent": db_record.progress_percent or 0,
        "thoughts": db_record.thoughts or [],
        "analysis_mode": db_record.analysis_mode,
        "target_backhaul_type": db_record.target_backhaul_type,
        "upgrade_analysis": db_record.upgrade_analysis,
        "hardware_compatibility": db_record.hardware_compatibility,
        "datacenter_analysis": db_record.datacenter_analysis,
        "result": db_record.result,
        "error": db_record.error,
    }


def get_execution(execution_id: str) -> Optional[AgenticCapacityPlanningExecution]:
    """Get an execution by ID from in-memory cache"""
    return _executions.get(execution_id)


def create_execution(
    db: Session,
    analysis_mode: str,
    target_backhaul_type: Optional[str],
    current_backhaul_filter: List[str],
    region: Optional[str],
    city: Optional[str],
    datacenter_ids: List[str],
    node_ids: List[str],
    include_nodes: bool,
    include_datacenters: bool,
    include_cost_estimate: bool,
    forecast_periods: Optional[List[int]] = None,
) -> AgenticCapacityPlanningExecution:
    """Create a new execution and persist to database"""
    execution_id = f"cap-{uuid.uuid4().hex[:8]}"
    execution = AgenticCapacityPlanningExecution(
        execution_id=execution_id,
        status=ExecutionStatus.PENDING.value,
        started_at=datetime.utcnow().isoformat(),
        analysis_mode=analysis_mode,
        target_backhaul_type=target_backhaul_type,
        current_backhaul_filter=current_backhaul_filter,
        region=region,
        city=city,
        datacenter_ids=datacenter_ids,
        node_ids=node_ids,
        include_nodes=include_nodes,
        include_datacenters=include_datacenters,
        include_cost_estimate=include_cost_estimate,
        forecast_periods=forecast_periods or [30, 60, 90],
    )
    _executions[execution_id] = execution

    # Persist to database for multi-worker access
    save_execution_to_db(db, execution)

    return execution


def add_thought(
    execution: AgenticCapacityPlanningExecution,
    agent_id: str,
    agent_name: str,
    thought_type: str,
    content: str,
    progress_percent: Optional[float] = None,
    data_summary: Optional[Dict[str, Any]] = None,
):
    """Add a thought to the execution"""
    thought = AgentThought(
        id=f"thought-{uuid.uuid4().hex[:6]}",
        timestamp=datetime.utcnow().isoformat(),
        agent_id=agent_id,
        agent_name=agent_name,
        type=thought_type,
        content=content,
        progress_percent=progress_percent,
        data_summary=data_summary,
    )
    execution.thoughts.append(thought)
    if progress_percent is not None:
        execution.progress_percent = progress_percent


# ===== AGENT IMPLEMENTATIONS =====

async def run_data_collector_agent(
    db: Session,
    execution: AgenticCapacityPlanningExecution,
) -> Dict[str, Any]:
    """
    Data Collector Agent - Gathers node and DC data by backhaul type.

    Outputs:
    - Node counts by backhaul type
    - Current bandwidth by region
    - Utilization metrics
    """
    agent_id = AgentType.DATA_COLLECTOR.value
    agent_name = "Data Collector"

    execution.current_agent = agent_id
    execution.current_agent_name = agent_name

    # Build scope description
    scope_parts = []
    if execution.city:
        scope_parts.append(f"city: {execution.city}")
    if execution.region:
        scope_parts.append(f"region: {execution.region}")
    if execution.datacenter_ids:
        scope_parts.append(f"{len(execution.datacenter_ids)} datacenters")
    if execution.node_ids:
        scope_parts.append(f"{len(execution.node_ids)} specific nodes")
    scope_desc = ", ".join(scope_parts) if scope_parts else "all assets"

    add_thought(execution, agent_id, agent_name, ThoughtType.THOUGHT.value,
                f"Starting data collection for scope: {scope_desc}...", 5)

    await asyncio.sleep(0.3)  # Simulate processing

    nodes = []
    datacenters = []

    # Collect node data if included
    if execution.include_nodes:
        add_thought(execution, agent_id, agent_name, ThoughtType.TOOL_CALL.value,
                    "Querying fiber_nodes table with filters", 8)

        node_query = select(FiberNodeModel)

        # Apply filters
        if execution.region:
            node_query = node_query.where(FiberNodeModel.region == execution.region)
        if execution.city:
            node_query = node_query.where(FiberNodeModel.city == execution.city)
        if execution.node_ids:
            node_query = node_query.where(FiberNodeModel.node_id.in_(execution.node_ids))

        nodes = db.execute(node_query).scalars().all()

    # Collect datacenter data if included
    if execution.include_datacenters:
        add_thought(execution, agent_id, agent_name, ThoughtType.TOOL_CALL.value,
                    "Querying data_centers table", 10)

        dc_query = select(HeadendModel)

        if execution.datacenter_ids:
            dc_query = dc_query.where(HeadendModel.headend_id.in_(execution.datacenter_ids))
        if execution.city:
            dc_query = dc_query.where(HeadendModel.city == execution.city)
        if execution.region:
            dc_query = dc_query.where(HeadendModel.region == execution.region)

        datacenters = db.execute(dc_query).scalars().all()

    await asyncio.sleep(0.2)

    # Categorize nodes by backhaul type
    nodes_by_backhaul: Dict[str, List[Any]] = {}
    for node in nodes:
        backhaul = getattr(node, 'backhaul_type', 'Unknown')
        if backhaul not in nodes_by_backhaul:
            nodes_by_backhaul[backhaul] = []
        nodes_by_backhaul[backhaul].append(node)

    add_thought(execution, agent_id, agent_name, ThoughtType.TOOL_RESULT.value,
                f"Found {len(nodes)} total nodes across {len(nodes_by_backhaul)} backhaul types",
                12, {"total_nodes": len(nodes), "backhaul_types": list(nodes_by_backhaul.keys())})

    # Filter nodes if current_backhaul_filter is specified
    filtered_nodes = []
    if execution.current_backhaul_filter:
        add_thought(execution, agent_id, agent_name, ThoughtType.THOUGHT.value,
                    f"Filtering to nodes with backhaul types: {execution.current_backhaul_filter}", 15)
        for backhaul_type in execution.current_backhaul_filter:
            filtered_nodes.extend(nodes_by_backhaul.get(backhaul_type, []))
        add_thought(execution, agent_id, agent_name, ThoughtType.DATA.value,
                    f"Found {len(filtered_nodes)} nodes matching filter criteria", 18)
    else:
        filtered_nodes = nodes

    await asyncio.sleep(0.2)

    # Calculate bandwidth and utilization
    add_thought(execution, agent_id, agent_name, ThoughtType.THOUGHT.value,
                "Calculating current bandwidth and utilization metrics...", 20)

    total_bandwidth_mbps = 0
    nodes_by_type_count = {}
    manufacturers = {}

    for node in filtered_nodes:
        backhaul = getattr(node, 'backhaul_type', 'Unknown')
        bandwidth = getattr(node, 'backhaul_capacity_mbps', 100)
        manufacturer = getattr(node, 'manufacturer', 'Unknown')

        total_bandwidth_mbps += bandwidth
        nodes_by_type_count[backhaul] = nodes_by_type_count.get(backhaul, 0) + 1
        manufacturers[manufacturer] = manufacturers.get(manufacturer, 0) + 1

    # Get KPI averages for utilization data
    try:
        kpi_averages = get_historical_kpi_averages(db, period_hours=24)
    except Exception:
        kpi_averages = {}

    await asyncio.sleep(0.3)

    add_thought(execution, agent_id, agent_name, ThoughtType.ANALYSIS.value,
                f"Current total bandwidth: {total_bandwidth_mbps / 1000:.2f} Gbps across {len(filtered_nodes)} nodes",
                25, {
                    "total_bandwidth_gbps": round(total_bandwidth_mbps / 1000, 2),
                    "nodes_by_backhaul": nodes_by_type_count,
                    "avg_utilization": kpi_averages.get("cpu_utilization", 50),
                })

    # Process datacenter data
    dc_info = []
    total_dc_power_mw = 0
    total_dc_capacity_mw = 0
    for dc in datacenters:
        dc_data = {
            "dc_id": dc.headend_id or 'Unknown',
            "name": dc.name or 'Unknown',
            "city": dc.city or 'Unknown',
            "status": dc.status or 'Unknown',
            "power_capacity_mw": dc.power_capacity_mw or 0,
            "current_power_mw": (dc.power_capacity_mw or 0) * 0.65,  # Estimate from capacity
            "total_rack_units": dc.total_rack_units or 0,
            "used_rack_units": int((dc.total_rack_units or 0) * 0.7),  # Estimate 70% usage
        }
        dc_info.append(dc_data)
        total_dc_power_mw += dc_data["current_power_mw"] or 0
        total_dc_capacity_mw += dc_data["power_capacity_mw"] or 0

    if datacenters:
        add_thought(execution, agent_id, agent_name, ThoughtType.DATA.value,
                    f"Found {len(datacenters)} datacenters with {total_dc_capacity_mw:.1f} MW total capacity",
                    27, {"datacenter_count": len(datacenters), "total_capacity_mw": total_dc_capacity_mw})

    # Build output
    output = {
        "total_nodes": len(nodes),
        "filtered_nodes": len(filtered_nodes),
        "nodes_by_backhaul": nodes_by_type_count,
        "nodes_by_manufacturer": manufacturers,
        "total_bandwidth_mbps": total_bandwidth_mbps,
        "total_bandwidth_gbps": round(total_bandwidth_mbps / 1000, 2),
        "avg_throughput_mbps": kpi_averages.get("throughput_mbps", 150),
        "avg_latency_ms": kpi_averages.get("avg_latency", 25),
        "avg_active_modems": kpi_averages.get("active_modems", 500),
        "avg_cpu_utilization": kpi_averages.get("cpu_utilization", 50),
        "region": execution.region,
        "city": execution.city,
        "filter_applied": execution.current_backhaul_filter,
        # Datacenter data
        "datacenters": dc_info,
        "total_datacenters": len(datacenters),
        "total_dc_power_mw": round(total_dc_power_mw, 2),
        "total_dc_capacity_mw": round(total_dc_capacity_mw, 2),
    }

    execution.data_collector_output = output

    add_thought(execution, agent_id, agent_name, ThoughtType.DATA.value,
                "Data collection complete. Passing to Upgrade Analyzer.", 25, output)

    return output


async def run_upgrade_analyzer_agent(
    db: Session,
    execution: AgenticCapacityPlanningExecution,
) -> Optional[UpgradeImpactAnalysis]:
    """
    Upgrade Analyzer Agent - Calculates the impact of upgrading to target backhaul.

    Only runs if analysis_mode is 'upgrade_scenario' or 'add_redundancy'.
    """
    agent_id = AgentType.UPGRADE_ANALYZER.value
    agent_name = "Upgrade Impact Analyzer"

    execution.current_agent = agent_id
    execution.current_agent_name = agent_name

    if execution.analysis_mode == "current_state":
        add_thought(execution, agent_id, agent_name, ThoughtType.THOUGHT.value,
                    "Analysis mode is 'current_state' - skipping upgrade analysis", 30)
        return None

    add_thought(execution, agent_id, agent_name, ThoughtType.THOUGHT.value,
                f"Analyzing upgrade impact for target: {execution.target_backhaul_type}", 30)

    await asyncio.sleep(0.3)

    data = execution.data_collector_output
    if not data:
        add_thought(execution, agent_id, agent_name, ThoughtType.ERROR.value,
                    "No data from Data Collector - cannot perform upgrade analysis", 35)
        return None

    target_backhaul = execution.target_backhaul_type or "Fiber"
    target_specs = BACKHAUL_SPECS.get(target_backhaul, BACKHAUL_SPECS["Fiber"])

    add_thought(execution, agent_id, agent_name, ThoughtType.TOOL_CALL.value,
                f"Looking up specifications for {target_backhaul}: "
                f"{target_specs['avg_capacity_mbps']} Mbps avg, {target_specs['latency_ms']}ms latency",
                35)

    await asyncio.sleep(0.2)

    # Calculate current bandwidth from filtered nodes
    current_bandwidth_mbps = data.get("total_bandwidth_mbps", 0)
    filtered_count = data.get("filtered_nodes", 0)
    nodes_by_backhaul = data.get("nodes_by_backhaul", {})

    # Calculate projected bandwidth after upgrade
    projected_bandwidth_mbps = filtered_count * target_specs["avg_capacity_mbps"]

    add_thought(execution, agent_id, agent_name, ThoughtType.ANALYSIS.value,
                f"Calculating bandwidth improvement: {current_bandwidth_mbps/1000:.2f} Gbps -> {projected_bandwidth_mbps/1000:.2f} Gbps",
                42)

    await asyncio.sleep(0.3)

    # Calculate weighted average current latency
    current_latency = 0
    total_nodes_for_latency = 0
    for backhaul_type, count in nodes_by_backhaul.items():
        specs = BACKHAUL_SPECS.get(backhaul_type, {"latency_ms": 50})
        current_latency += specs["latency_ms"] * count
        total_nodes_for_latency += count

    if total_nodes_for_latency > 0:
        current_avg_latency = current_latency / total_nodes_for_latency
    else:
        current_avg_latency = data.get("avg_latency_ms", 50)

    projected_latency = target_specs["latency_ms"]

    # Calculate improvements
    if current_bandwidth_mbps > 0:
        bandwidth_improvement = ((projected_bandwidth_mbps - current_bandwidth_mbps) / current_bandwidth_mbps) * 100
    else:
        bandwidth_improvement = 0

    if current_avg_latency > 0:
        latency_improvement = ((current_avg_latency - projected_latency) / current_avg_latency) * 100
    else:
        latency_improvement = 0

    add_thought(execution, agent_id, agent_name, ThoughtType.ANALYSIS.value,
                f"Bandwidth improvement: +{bandwidth_improvement:.1f}% | Latency reduction: -{latency_improvement:.1f}%",
                48)

    await asyncio.sleep(0.2)

    # Estimate users to benefit
    users_per_node = data.get("avg_active_modems", 500)
    users_to_benefit = int(filtered_count * users_per_node)

    analysis = UpgradeImpactAnalysis(
        nodes_analyzed=filtered_count,
        current_total_bandwidth_gbps=round(current_bandwidth_mbps / 1000, 2),
        projected_total_bandwidth_gbps=round(projected_bandwidth_mbps / 1000, 2),
        bandwidth_improvement_percent=round(bandwidth_improvement, 1),
        current_avg_latency_ms=round(current_avg_latency, 1),
        projected_avg_latency_ms=projected_latency,
        latency_improvement_percent=round(latency_improvement, 1),
        nodes_by_current_backhaul=nodes_by_backhaul,
        upgrade_target=target_backhaul,
        users_to_benefit=users_to_benefit,
    )

    execution.upgrade_analysis = analysis

    add_thought(execution, agent_id, agent_name, ThoughtType.DATA.value,
                f"Upgrade analysis complete. {users_to_benefit:,} users will benefit from improved connectivity.",
                50, asdict(analysis))

    return analysis


async def run_hardware_checker_agent(
    db: Session,
    execution: AgenticCapacityPlanningExecution,
) -> Optional[HardwareCompatibilityReport]:
    """
    Hardware Checker Agent - Checks equipment compatibility with target backhaul.

    Runs in all modes to provide upgrade readiness insights for capacity planning.
    In 'current_state' mode: assesses hardware upgrade potential and constraints.
    In 'upgrade_scenario' mode: validates compatibility with target backhaul type.
    """
    agent_id = AgentType.HARDWARE_CHECKER.value
    agent_name = "Hardware Compatibility Checker"

    execution.current_agent = agent_id
    execution.current_agent_name = agent_name

    await asyncio.sleep(0.3)

    data = execution.data_collector_output
    if not data:
        add_thought(execution, agent_id, agent_name, ThoughtType.ERROR.value,
                    "No data from Data Collector", 58)
        return None

    manufacturers = data.get("nodes_by_manufacturer", {})
    nodes_by_backhaul = data.get("nodes_by_backhaul", {})

    # In current_state mode, assess compatibility with current backhaul types
    # In upgrade_scenario mode, assess compatibility with target backhaul
    if execution.analysis_mode == "current_state":
        # Use the most common current backhaul type for assessment
        if nodes_by_backhaul:
            current_backhaul = max(nodes_by_backhaul.keys(), key=lambda k: nodes_by_backhaul[k])
        else:
            current_backhaul = "Microwave"  # Default fallback
        target_backhaul = current_backhaul
        add_thought(execution, agent_id, agent_name, ThoughtType.THOUGHT.value,
                    f"Assessing hardware compatibility with current {current_backhaul} connections...", 55)
    else:
        target_backhaul = execution.target_backhaul_type or "Fiber"
        add_thought(execution, agent_id, agent_name, ThoughtType.THOUGHT.value,
                    f"Checking hardware compatibility for upgrade to {target_backhaul}...", 55)

    add_thought(execution, agent_id, agent_name, ThoughtType.TOOL_CALL.value,
                f"Checking compatibility matrix for {len(manufacturers)} manufacturers with {target_backhaul}",
                60)

    await asyncio.sleep(0.3)

    compatible_count = 0
    partial_upgrade_count = 0
    replacement_count = 0

    compatibility_by_manufacturer: Dict[str, Dict[str, int]] = {}
    cost_by_manufacturer: Dict[str, float] = {}

    for manufacturer, count in manufacturers.items():
        compat_matrix = MANUFACTURER_COMPATIBILITY.get(manufacturer, {})
        compat_status = compat_matrix.get(target_backhaul, "partial_upgrade")

        if manufacturer not in compatibility_by_manufacturer:
            compatibility_by_manufacturer[manufacturer] = {
                "compatible": 0,
                "partial_upgrade": 0,
                "replacement": 0,
            }

        compatibility_by_manufacturer[manufacturer][compat_status] = count

        if compat_status == "compatible":
            compatible_count += count
        elif compat_status == "partial_upgrade":
            partial_upgrade_count += count
        else:
            replacement_count += count

        # Calculate costs
        node_cost = BACKHAUL_SPECS.get(target_backhaul, {}).get("cost_per_node", 10000)
        compat_cost = COMPATIBILITY_COSTS.get(compat_status, 0)
        total_cost_for_mfr = count * (node_cost + compat_cost)
        cost_by_manufacturer[manufacturer] = total_cost_for_mfr

        add_thought(execution, agent_id, agent_name, ThoughtType.DATA.value,
                    f"{manufacturer}: {count} nodes - {compat_status.replace('_', ' ')}",
                    60 + (5 * list(manufacturers.keys()).index(manufacturer) / len(manufacturers)))

    await asyncio.sleep(0.2)

    # Calculate total costs
    target_specs = BACKHAUL_SPECS.get(target_backhaul, BACKHAUL_SPECS["Fiber"])
    base_cost_per_node = target_specs["cost_per_node"]

    estimated_total_cost = sum(cost_by_manufacturer.values())
    estimated_upgrade_cost = partial_upgrade_count * COMPATIBILITY_COSTS["partial_upgrade"]
    estimated_replacement_cost = replacement_count * COMPATIBILITY_COSTS["replacement"]

    # Calculate installation timeline (parallel installation with some overhead)
    base_installation_days = target_specs["installation_days"]
    total_nodes = compatible_count + partial_upgrade_count + replacement_count
    # Assume 10 nodes can be upgraded in parallel
    batches = max(1, total_nodes // 10)
    installation_timeline = base_installation_days * batches

    add_thought(execution, agent_id, agent_name, ThoughtType.ANALYSIS.value,
                f"Compatibility breakdown: {compatible_count} compatible, "
                f"{partial_upgrade_count} need partial upgrade, {replacement_count} need replacement",
                70)

    await asyncio.sleep(0.2)

    add_thought(execution, agent_id, agent_name, ThoughtType.ANALYSIS.value,
                f"Estimated total cost: ${estimated_total_cost:,.0f} | Timeline: {installation_timeline} days",
                73)

    report = HardwareCompatibilityReport(
        total_nodes_checked=total_nodes,
        compatible_count=compatible_count,
        partial_upgrade_count=partial_upgrade_count,
        replacement_count=replacement_count,
        compatibility_by_manufacturer=compatibility_by_manufacturer,
        estimated_total_cost=estimated_total_cost,
        estimated_upgrade_cost=estimated_upgrade_cost,
        estimated_replacement_cost=estimated_replacement_cost,
        cost_breakdown_by_manufacturer=cost_by_manufacturer,
        installation_timeline_days=installation_timeline,
    )

    execution.hardware_compatibility = report

    add_thought(execution, agent_id, agent_name, ThoughtType.DATA.value,
                "Hardware compatibility analysis complete. Passing to Headend Component Analyzer.",
                75, asdict(report))

    return report


# ===== COMPONENT UPGRADE SPECIFICATIONS =====
COMPONENT_UPGRADE_SPECS = {
    "CMTS": {
        "upgrade_threshold_utilization": 70,
        "critical_threshold_utilization": 85,
        "base_upgrade_cost": 150000,
        "capacity_upgrade_cost": 50000,
        "full_replacement_cost": 500000,
        "upgrade_types": ["port_expansion", "line_card_upgrade", "software_upgrade", "full_replacement"],
    },
    "Hub": {
        "upgrade_threshold_utilization": 65,
        "critical_threshold_utilization": 80,
        "base_upgrade_cost": 80000,
        "capacity_upgrade_cost": 30000,
        "full_replacement_cost": 250000,
        "upgrade_types": ["fiber_capacity_expansion", "power_upgrade", "equipment_refresh", "full_replacement"],
    },
    "NetworkDevice": {
        "upgrade_threshold_utilization": 70,
        "critical_threshold_utilization": 85,
        "base_upgrade_cost": 40000,
        "capacity_upgrade_cost": 15000,
        "full_replacement_cost": 120000,
        "upgrade_types": ["throughput_upgrade", "firmware_upgrade", "port_expansion", "full_replacement"],
    },
}


# ===== HISTORICAL COMPONENT ANALYSIS FUNCTIONS =====

def get_component_history(
    db: Session,
    component_type: str,
    component_id: str,
    period_hours: int = 168,  # 7 days default
) -> List[Dict[str, Any]]:
    """Get historical metrics for a component over the specified period."""
    cutoff = datetime.utcnow() - timedelta(hours=period_hours)

    records = db.execute(
        select(ComponentMetricsHistoryModel)
        .where(ComponentMetricsHistoryModel.component_type == component_type)
        .where(ComponentMetricsHistoryModel.component_id == component_id)
        .where(ComponentMetricsHistoryModel.recorded_at >= cutoff)
        .order_by(ComponentMetricsHistoryModel.recorded_at)
    ).scalars().all()

    return [
        {
            "timestamp": r.recorded_at.isoformat() if r.recorded_at else None,
            "utilization_percent": r.utilization_percent,
            "cpu_utilization": r.cpu_utilization,
            "memory_utilization": r.memory_utilization,
            "capacity_current": r.capacity_current,
            "capacity_max": r.capacity_max,
            "performance_score": r.performance_score,
            "status": r.status,
        }
        for r in records
    ]


def analyze_component_trends(
    history: List[Dict[str, Any]],
    current_utilization: float,
) -> Dict[str, Any]:
    """Analyze trends from historical data."""
    if not history or len(history) < 2:
        return {
            "trend_direction": "unknown",
            "growth_rate_per_week": 0,
            "growth_rate_per_month": 0,
            "avg_utilization_7d": current_utilization,
            "avg_utilization_30d": current_utilization,
            "peak_utilization_7d": current_utilization,
            "peak_utilization_30d": current_utilization,
            "utilization_variance": 0,
            "performance_trend": "stable",
            "projected_days_to_threshold": None,
            "data_points": 0,
        }

    utilizations = [h["utilization_percent"] for h in history if h.get("utilization_percent") is not None]
    performances = [h["performance_score"] for h in history if h.get("performance_score") is not None]

    if not utilizations:
        utilizations = [current_utilization]

    # Calculate averages
    avg_util = sum(utilizations) / len(utilizations)
    peak_util = max(utilizations)

    # Calculate 7-day and 30-day averages (approximate based on data density)
    recent_count = min(len(utilizations), len(utilizations) // 4 + 1)  # ~25% = 7 days of 30
    avg_util_7d = sum(utilizations[-recent_count:]) / recent_count if recent_count > 0 else avg_util
    avg_util_30d = avg_util

    # Calculate growth rate
    if len(utilizations) >= 2:
        first_quarter = utilizations[:max(1, len(utilizations)//4)]
        last_quarter = utilizations[-max(1, len(utilizations)//4):]
        first_avg = sum(first_quarter) / len(first_quarter)
        last_avg = sum(last_quarter) / len(last_quarter)

        if first_avg > 0:
            total_change = ((last_avg - first_avg) / first_avg) * 100
            # Assume data spans period_hours, convert to weekly/monthly
            growth_per_week = total_change / 4 if len(utilizations) > 10 else total_change
            growth_per_month = growth_per_week * 4
        else:
            growth_per_week = 0
            growth_per_month = 0
    else:
        growth_per_week = 0
        growth_per_month = 0

    # Determine trend direction
    if growth_per_week > 2:
        trend_direction = "increasing"
    elif growth_per_week < -2:
        trend_direction = "decreasing"
    else:
        trend_direction = "stable"

    # Calculate variance (standard deviation proxy)
    if len(utilizations) > 1:
        mean = sum(utilizations) / len(utilizations)
        variance = sum((x - mean) ** 2 for x in utilizations) / len(utilizations)
        std_dev = variance ** 0.5
    else:
        std_dev = 0

    # Performance trend
    if performances and len(performances) >= 2:
        perf_first = sum(performances[:len(performances)//2]) / max(1, len(performances)//2)
        perf_last = sum(performances[len(performances)//2:]) / max(1, len(performances) - len(performances)//2)
        if perf_last < perf_first - 2:
            performance_trend = "degrading"
        elif perf_last > perf_first + 2:
            performance_trend = "improving"
        else:
            performance_trend = "stable"
    else:
        performance_trend = "stable"

    # Project days to threshold (80% utilization)
    threshold = 80
    if current_utilization < threshold and growth_per_week > 0:
        remaining = threshold - current_utilization
        weeks_to_threshold = remaining / growth_per_week if growth_per_week > 0 else None
        days_to_threshold = int(weeks_to_threshold * 7) if weeks_to_threshold else None
    else:
        days_to_threshold = 0 if current_utilization >= threshold else None

    return {
        "trend_direction": trend_direction,
        "growth_rate_per_week": round(growth_per_week, 2),
        "growth_rate_per_month": round(growth_per_month, 2),
        "avg_utilization_7d": round(avg_util_7d, 1),
        "avg_utilization_30d": round(avg_util_30d, 1),
        "peak_utilization_7d": round(peak_util, 1),
        "peak_utilization_30d": round(peak_util, 1),
        "utilization_variance": round(std_dev, 2),
        "performance_trend": performance_trend,
        "projected_days_to_threshold": days_to_threshold,
        "data_points": len(utilizations),
    }


def collect_component_metrics(db: Session) -> int:
    """
    Collect current metrics from all cable network components and store in history table.
    Call this periodically (e.g., hourly) to build historical data.
    Returns the number of records created.
    """
    records_created = 0
    now = datetime.utcnow()

    # CMTS devices
    for comp in db.execute(select(CMTSModel)).scalars().all():
        if not comp.cmts_id:
            continue
        active = comp.active_modems or 0
        max_cap = comp.max_modems_capacity or 1
        utilization = (active / max_cap) * 100
        performance_score = comp.ranging_success_rate or 100
        db.add(ComponentMetricsHistoryModel(
            component_type="CMTS", component_id=comp.cmts_id,
            utilization_percent=utilization,
            cpu_utilization=comp.cpu_utilization,
            memory_utilization=comp.memory_utilization,
            capacity_current=active, capacity_max=max_cap,
            performance_score=performance_score,
            status=comp.status or 'unknown', recorded_at=now,
        ))
        records_created += 1

    # Hubs
    for comp in db.execute(select(HubModel)).scalars().all():
        if not comp.hub_id:
            continue
        current_tp = comp.current_throughput_gbps or 0
        fiber_cap = comp.fiber_capacity_gbps or 1
        utilization = (current_tp / fiber_cap) * 100
        performance_score = 100 if comp.status == 'operational' else (70 if comp.status == 'degraded' else 30)
        db.add(ComponentMetricsHistoryModel(
            component_type="Hub", component_id=comp.hub_id,
            utilization_percent=utilization,
            cpu_utilization=None, memory_utilization=None,
            capacity_current=current_tp, capacity_max=fiber_cap,
            performance_score=performance_score,
            status=comp.status or 'unknown', recorded_at=now,
        ))
        records_created += 1

    # Network devices (firewalls, switches, routers)
    for comp in db.execute(select(NetworkDeviceModel)).scalars().all():
        if not comp.device_id:
            continue
        utilization = comp.cpu_utilization or 0
        performance_score = 100 if comp.status == 'operational' else (70 if comp.status == 'degraded' else 30)
        db.add(ComponentMetricsHistoryModel(
            component_type="NetworkDevice", component_id=comp.device_id,
            utilization_percent=utilization,
            cpu_utilization=comp.cpu_utilization,
            memory_utilization=comp.memory_utilization,
            capacity_current=comp.uplink_speed_gbps or 0,
            capacity_max=comp.uplink_speed_gbps or 1,
            performance_score=performance_score,
            status=comp.status or 'unknown', recorded_at=now,
        ))
        records_created += 1

    db.commit()
    return records_created


def analyze_component(component, component_type: str, historical_trends: Optional[Dict[str, Any]] = None) -> ComponentStatus:
    """Analyze a single cable network component and return its status with recommendations."""
    specs = COMPONENT_UPGRADE_SPECS.get(component_type, COMPONENT_UPGRADE_SPECS["CMTS"])

    # Get utilization and capacity based on component type
    if component_type == "CMTS":
        active = getattr(component, 'active_modems', 0) or 0
        max_cap = getattr(component, 'max_modems_capacity', 1) or 1
        utilization = (active / max_cap) * 100
        capacity_current = active
        capacity_max = max_cap
        performance_metrics = [
            getattr(component, 'ranging_success_rate', 100) or 100,
        ]
    elif component_type == "Hub":
        current_tp = getattr(component, 'current_throughput_gbps', 0) or 0
        fiber_cap = getattr(component, 'fiber_capacity_gbps', 1) or 1
        utilization = (current_tp / fiber_cap) * 100
        capacity_current = current_tp
        capacity_max = fiber_cap
        status_val = getattr(component, 'status', 'operational')
        performance_metrics = [100 if status_val == 'operational' else 70]
    elif component_type == "NetworkDevice":
        utilization = getattr(component, 'cpu_utilization', 0) or 0
        capacity_current = getattr(component, 'uplink_speed_gbps', 0) or 0
        capacity_max = getattr(component, 'uplink_speed_gbps', 1) or 1
        status_val = getattr(component, 'status', 'operational')
        performance_metrics = [100 if status_val == 'operational' else 70]
    else:
        utilization = 50
        capacity_current = 0
        capacity_max = 1
        performance_metrics = [100]

    # Calculate performance score (average of metrics)
    performance_score = sum(performance_metrics) / len(performance_metrics) if performance_metrics else 100

    # Identify issues
    issues = []
    status = getattr(component, 'status', 'operational')

    if status != 'operational':
        issues.append(f"Status is {status}")
    if utilization >= specs["critical_threshold_utilization"]:
        issues.append(f"Critical utilization: {utilization:.1f}%")
    elif utilization >= specs["upgrade_threshold_utilization"]:
        issues.append(f"High utilization: {utilization:.1f}%")
    if performance_score < 95:
        issues.append(f"Performance degradation: {performance_score:.1f}%")

    # CPU/memory checks
    cpu_util = getattr(component, 'cpu_utilization', 0) or 0
    mem_util = getattr(component, 'memory_utilization', 0) or 0
    if cpu_util > 80:
        issues.append(f"High CPU: {cpu_util:.1f}%")
    if mem_util > 85:
        issues.append(f"High memory: {mem_util:.1f}%")

    # Extract historical trend data
    trends = historical_trends or {}
    trend_direction = trends.get("trend_direction", "unknown")
    growth_rate_per_week = trends.get("growth_rate_per_week", 0)
    growth_rate_per_month = trends.get("growth_rate_per_month", 0)
    avg_util_7d = trends.get("avg_utilization_7d", utilization)
    avg_util_30d = trends.get("avg_utilization_30d", utilization)
    peak_util_7d = trends.get("peak_utilization_7d", utilization)
    projected_days = trends.get("projected_days_to_threshold")
    perf_trend = trends.get("performance_trend", "stable")

    # Add trend-based issues
    if trend_direction == "increasing" and growth_rate_per_week > 3:
        issues.append(f"Rapid growth: {growth_rate_per_week:.1f}%/week")
    if projected_days is not None and projected_days < 30 and projected_days > 0:
        issues.append(f"Will reach threshold in {projected_days} days")
    if perf_trend == "degrading":
        issues.append("Performance degrading over time")

    # Determine upgrade priority (enhanced with trend data)
    if utilization >= specs["critical_threshold_utilization"] or status == 'failed':
        upgrade_priority = "critical"
    elif utilization >= specs["upgrade_threshold_utilization"] or status == 'degraded':
        upgrade_priority = "high"
    elif (utilization >= specs["upgrade_threshold_utilization"] - 15 or
          performance_score < 95 or
          (projected_days is not None and projected_days < 60)):
        upgrade_priority = "medium" if not (trend_direction == "increasing" and growth_rate_per_week > 5) else "high"
    elif trend_direction == "increasing" and growth_rate_per_week > 3:
        upgrade_priority = "medium"
    else:
        upgrade_priority = "low"

    # Determine recommended action and cost (enhanced with trend context)
    if upgrade_priority == "critical":
        if status == 'failed':
            recommended_action = "Immediate replacement required"
            estimated_cost = specs["full_replacement_cost"]
        else:
            recommended_action = "Urgent capacity expansion needed"
            estimated_cost = specs["base_upgrade_cost"] + specs["capacity_upgrade_cost"]
    elif upgrade_priority == "high":
        if projected_days is not None and projected_days < 30:
            recommended_action = f"Schedule capacity upgrade immediately - threshold breach projected in {projected_days} days"
        else:
            recommended_action = "Schedule capacity upgrade within 30 days"
        estimated_cost = specs["capacity_upgrade_cost"]
    elif upgrade_priority == "medium":
        if trend_direction == "increasing":
            recommended_action = f"Plan capacity upgrade within 60 days - growing at {growth_rate_per_month:.1f}%/month"
        else:
            recommended_action = "Plan capacity upgrade within 90 days"
        estimated_cost = specs["capacity_upgrade_cost"] * 0.7
    else:
        if trend_direction == "increasing" and growth_rate_per_week > 1:
            recommended_action = f"Monitor closely - growth rate {growth_rate_per_week:.1f}%/week"
        else:
            recommended_action = "No immediate action required - continue monitoring"
        estimated_cost = 0

    # Get the component's ID field
    if component_type == "CMTS":
        comp_id = getattr(component, 'cmts_id', 'unknown')
    elif component_type == "Hub":
        comp_id = getattr(component, 'hub_id', 'unknown')
    elif component_type == "NetworkDevice":
        comp_id = getattr(component, 'device_id', 'unknown')
    else:
        comp_id = 'unknown'

    return ComponentStatus(
        component_id=comp_id,
        component_type=component_type,
        name=getattr(component, 'name', None) or getattr(component, 'hostname', 'Unknown'),
        status=status,
        utilization_percent=utilization,
        capacity_current=capacity_current,
        capacity_max=capacity_max,
        performance_score=performance_score,
        issues=issues,
        upgrade_priority=upgrade_priority,
        recommended_action=recommended_action,
        estimated_cost=estimated_cost,
        location=getattr(component, 'city', '') or '',
        region=getattr(component, 'region', '') or '',
        trend_direction=trend_direction,
        growth_rate_per_week=growth_rate_per_week,
        growth_rate_per_month=growth_rate_per_month,
        avg_utilization_7d=avg_util_7d,
        avg_utilization_30d=avg_util_30d,
        peak_utilization_7d=peak_util_7d,
        projected_days_to_threshold=projected_days,
        performance_trend=perf_trend,
    )


async def run_datacenter_component_analyzer_agent(
    db: Session,
    execution: AgenticCapacityPlanningExecution,
) -> Optional[DatacenterComponentAnalysis]:
    """
    Headend Component Analyzer Agent - Analyzes all components in selected headends.

    For each headend, fetches and analyzes:
    - CMTS devices (Cable Modem Termination Systems)
    - Hubs (Distribution hubs)
    - Network Devices (Firewalls, switches, routers)

    Provides upgrade recommendations based on utilization and performance.
    """
    agent_id = AgentType.HEADEND_COMPONENT_ANALYZER.value
    agent_name = "Headend Component Analyzer"

    execution.current_agent = agent_id
    execution.current_agent_name = agent_name

    # Skip if no headends to analyze
    data = execution.data_collector_output
    if not data or not data.get("datacenters"):
        add_thought(execution, agent_id, agent_name, ThoughtType.THOUGHT.value,
                    "No headends in scope - skipping component analysis", 76)
        return None

    datacenters = data.get("datacenters", [])
    add_thought(execution, agent_id, agent_name, ThoughtType.THOUGHT.value,
                f"Analyzing components for {len(datacenters)} headend(s) with 7-day and 30-day trends...", 76)

    await asyncio.sleep(0.3)

    all_components: List[ComponentStatus] = []
    components_by_type: Dict[str, int] = {}
    critical_issues: List[str] = []
    upgrade_recommendations: List[Dict[str, Any]] = []
    total_upgrade_cost = 0.0
    priority_upgrades: List[str] = []
    trend_warnings: List[str] = []
    sites: List[Dict[str, Any]] = []

    for dc_data in datacenters:
        dc_id = dc_data.get("dc_id", "unknown")
        dc_name = dc_data.get("name", "Unknown")
        dc_city = dc_data.get("city", "Unknown")
        dc_status = dc_data.get("status", "Unknown")
        power_capacity = dc_data.get("power_capacity_mw", 0) or 0
        current_power = dc_data.get("current_power_mw", 0) or 0
        total_racks = dc_data.get("total_rack_units", 0) or 0
        used_racks = dc_data.get("used_rack_units", 0) or 0

        # Track site-level data
        site_components: List[ComponentStatus] = []
        site_components_by_type: Dict[str, int] = {}
        site_issues: List[str] = []
        site_critical_count = 0
        site_high_count = 0
        site_growth_rates: List[float] = []

        add_thought(execution, agent_id, agent_name, ThoughtType.TOOL_CALL.value,
                    f"Fetching components and historical data for {dc_name} ({dc_id})...", 78)

        # Query cable network components linked to this headend
        component_queries = [
            ("CMTS", CMTSModel, "cmts_id",
             db.execute(select(CMTSModel).where(CMTSModel.headend_id == dc_id)).scalars().all()),
            ("Hub", HubModel, "hub_id",
             db.execute(select(HubModel).where(HubModel.headend_id == dc_id)).scalars().all()),
            ("NetworkDevice", NetworkDeviceModel, "device_id",
             db.execute(select(NetworkDeviceModel).where(NetworkDeviceModel.headend_id == dc_id)).scalars().all()),
        ]

        for comp_type, model_class, id_field, components in component_queries:
            if not components:
                continue

            components_by_type[comp_type] = components_by_type.get(comp_type, 0) + len(components)

            for component in components:
                comp_id = getattr(component, id_field, 'unknown')

                # Fetch 30-day historical data for trend analysis
                history_30d = get_component_history(db, comp_type, comp_id, period_hours=720)  # 30 days

                # Get current utilization for trend analysis
                if comp_type == "CMTS":
                    active = getattr(component, 'active_modems', 0) or 0
                    max_cap = getattr(component, 'max_modems_capacity', 1) or 1
                    current_util = (active / max_cap) * 100
                elif comp_type == "Hub":
                    current_tp = getattr(component, 'current_throughput_gbps', 0) or 0
                    fiber_cap = getattr(component, 'fiber_capacity_gbps', 1) or 1
                    current_util = (current_tp / fiber_cap) * 100
                elif comp_type == "NetworkDevice":
                    current_util = getattr(component, 'cpu_utilization', 0) or 0
                else:
                    current_util = 50

                # Analyze trends
                trends = analyze_component_trends(history_30d, current_util)

                # Analyze component with historical context
                status = analyze_component(component, comp_type, historical_trends=trends)
                all_components.append(status)
                site_components.append(status)
                site_components_by_type[comp_type] = site_components_by_type.get(comp_type, 0) + 1

                # Track site-level issues and priority counts
                if status.issues:
                    for issue in status.issues:
                        site_issues.append(f"{comp_type} {status.name}: {issue}")
                if status.upgrade_priority == "critical":
                    site_critical_count += 1
                elif status.upgrade_priority == "high":
                    site_high_count += 1
                if status.growth_rate_per_week > 0:
                    site_growth_rates.append(status.growth_rate_per_week)

                # Track trend-based warnings
                if status.trend_direction == "increasing" and status.growth_rate_per_week > 5:
                    trend_warnings.append(f"{comp_type} {status.name}: Rapid growth ({status.growth_rate_per_week:.1f}%/week)")
                if status.projected_days_to_threshold is not None and 0 < status.projected_days_to_threshold < 60:
                    trend_warnings.append(f"{comp_type} {status.name}: Threshold breach in {status.projected_days_to_threshold} days")

                # Track critical issues - add each issue separately for better formatting
                if status.upgrade_priority == "critical":
                    for issue in status.issues:
                        critical_issues.append(f"{dc_name} › {comp_type} {status.name}: {issue}")
                    priority_upgrades.append(f"{comp_type}: {status.name}")

                # Build upgrade recommendations
                if status.upgrade_priority in ["critical", "high"]:
                    upgrade_recommendations.append({
                        "component_id": status.component_id,
                        "component_type": comp_type,
                        "name": status.name,
                        "site_id": dc_id,
                        "site_name": dc_name,
                        "current_utilization": status.utilization_percent,
                        "avg_utilization_7d": status.avg_utilization_7d,
                        "avg_utilization_30d": status.avg_utilization_30d,
                        "trend_direction": status.trend_direction,
                        "growth_rate_per_week": status.growth_rate_per_week,
                        "growth_rate_per_month": status.growth_rate_per_month,
                        "projected_days_to_threshold": status.projected_days_to_threshold,
                        "priority": status.upgrade_priority,
                        "action": status.recommended_action,
                        "estimated_cost": status.estimated_cost,
                        "issues": status.issues,
                    })

                total_upgrade_cost += status.estimated_cost

        # Build site summary after processing all components for this datacenter
        if site_components:
            site_health_scores = []
            for comp in site_components:
                status_score = 100 if comp.status == 'operational' else (70 if comp.status == 'degraded' else 30)
                util_score = max(0, 100 - max(0, comp.utilization_percent - 50))
                score = (status_score * 0.3 + util_score * 0.3 + comp.performance_score * 0.4)
                site_health_scores.append(score)

            site_health = sum(site_health_scores) / len(site_health_scores) if site_health_scores else 100.0
            power_util = (current_power / power_capacity * 100) if power_capacity > 0 else 0
            rack_util = (used_racks / total_racks * 100) if total_racks > 0 else 0
            avg_growth = sum(site_growth_rates) / len(site_growth_rates) if site_growth_rates else 0

            # Generate site-specific recommendations
            site_recommendations = []
            if site_critical_count > 0:
                site_recommendations.append(f"Immediate attention needed for {site_critical_count} critical component(s)")
            if site_high_count > 0:
                site_recommendations.append(f"Plan upgrades for {site_high_count} high-priority component(s)")
            if power_util > 80:
                site_recommendations.append(f"Power utilization at {power_util:.1f}% - consider capacity expansion")
            if rack_util > 85:
                site_recommendations.append(f"Rack space at {rack_util:.1f}% - plan for additional racks")
            if avg_growth > 3:
                site_recommendations.append(f"High growth rate ({avg_growth:.1f}%/week) - accelerate capacity planning")

            sites.append({
                "dc_id": dc_id,
                "name": dc_name,
                "city": dc_city,
                "status": dc_status,
                "total_components": len(site_components),
                "components_by_type": site_components_by_type,
                "health_score": round(site_health, 1),
                "critical_count": site_critical_count,
                "high_count": site_high_count,
                "issues": site_issues[:10],  # Limit to top 10 issues
                "power_capacity_mw": power_capacity,
                "current_power_mw": current_power,
                "power_utilization_percent": round(power_util, 1),
                "total_rack_units": total_racks,
                "used_rack_units": used_racks,
                "rack_utilization_percent": round(rack_util, 1),
                "avg_growth_per_week": round(avg_growth, 2),
                "recommendations": site_recommendations,
            })

        await asyncio.sleep(0.2)

    # Calculate overall health score and regional breakdowns
    issues_by_location: Dict[str, List[str]] = {}
    components_by_location: Dict[str, int] = {}
    health_by_location: Dict[str, List[float]] = {}
    growth_by_location: Dict[str, Dict[str, Any]] = {}

    if all_components:
        health_scores = []
        for comp in all_components:
            # Health based on status, utilization, and performance
            status_score = 100 if comp.status == 'operational' else (70 if comp.status == 'degraded' else 30)
            util_score = max(0, 100 - max(0, comp.utilization_percent - 50))
            score = (status_score * 0.3 + util_score * 0.3 + comp.performance_score * 0.4)
            health_scores.append(score)

            # Group by location
            location = comp.location or comp.region or "Unknown"
            if location not in components_by_location:
                components_by_location[location] = 0
                health_by_location[location] = []
                issues_by_location[location] = []
                growth_by_location[location] = {
                    "avg_growth_per_week": [],
                    "avg_growth_per_month": [],
                    "critical_count": 0,
                    "high_count": 0,
                }

            components_by_location[location] += 1
            health_by_location[location].append(score)

            # Track issues by location
            if comp.issues:
                for issue in comp.issues:
                    issues_by_location[location].append(f"{comp.component_type} {comp.name}: {issue}")

            # Track growth by location
            if comp.growth_rate_per_week > 0:
                growth_by_location[location]["avg_growth_per_week"].append(comp.growth_rate_per_week)
            if comp.growth_rate_per_month > 0:
                growth_by_location[location]["avg_growth_per_month"].append(comp.growth_rate_per_month)
            if comp.upgrade_priority == "critical":
                growth_by_location[location]["critical_count"] += 1
            elif comp.upgrade_priority == "high":
                growth_by_location[location]["high_count"] += 1

        overall_health = sum(health_scores) / len(health_scores)

        # Convert health lists to averages
        health_by_location_avg: Dict[str, float] = {}
        for loc, scores in health_by_location.items():
            health_by_location_avg[loc] = round(sum(scores) / len(scores), 1) if scores else 100.0
            # Finalize growth averages
            if growth_by_location[loc]["avg_growth_per_week"]:
                growth_by_location[loc]["avg_growth_per_week"] = round(
                    sum(growth_by_location[loc]["avg_growth_per_week"]) / len(growth_by_location[loc]["avg_growth_per_week"]), 2
                )
            else:
                growth_by_location[loc]["avg_growth_per_week"] = 0
            if growth_by_location[loc]["avg_growth_per_month"]:
                growth_by_location[loc]["avg_growth_per_month"] = round(
                    sum(growth_by_location[loc]["avg_growth_per_month"]) / len(growth_by_location[loc]["avg_growth_per_month"]), 2
                )
            else:
                growth_by_location[loc]["avg_growth_per_month"] = 0
    else:
        overall_health = 100.0
        health_by_location_avg = {}

    # Sort recommendations by priority
    priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    upgrade_recommendations.sort(key=lambda x: priority_order.get(x["priority"], 4))

    add_thought(execution, agent_id, agent_name, ThoughtType.ANALYSIS.value,
                f"Analyzed {len(all_components)} components. Health score: {overall_health:.1f}%",
                82, {
                    "total_components": len(all_components),
                    "components_by_type": components_by_type,
                    "critical_issues_count": len(critical_issues),
                    "health_score": round(overall_health, 1),
                })

    if critical_issues:
        add_thought(execution, agent_id, agent_name, ThoughtType.ERROR.value,
                    f"Found {len(critical_issues)} critical issues requiring immediate attention",
                    83, {"critical_issues": critical_issues[:5]})

    if trend_warnings:
        add_thought(execution, agent_id, agent_name, ThoughtType.ANALYSIS.value,
                    f"Trend analysis: {len(trend_warnings)} components showing concerning growth patterns",
                    84, {"trend_warnings": trend_warnings[:5]})

    if upgrade_recommendations:
        add_thought(execution, agent_id, agent_name, ThoughtType.DATA.value,
                    f"Generated {len(upgrade_recommendations)} upgrade recommendations based on current state and 30-day trends. "
                    f"Estimated total cost: ${total_upgrade_cost:,.0f}",
                    85, {"top_recommendations": upgrade_recommendations[:3]})

    # Sort sites by critical count (descending), then by health score (ascending)
    sites.sort(key=lambda s: (-s["critical_count"], s["health_score"]))

    # Build the analysis result
    analysis = DatacenterComponentAnalysis(
        datacenter_id=datacenters[0].get("dc_id", "multiple") if len(datacenters) == 1 else "multiple",
        datacenter_name=datacenters[0].get("name", "Multiple") if len(datacenters) == 1 else f"{len(datacenters)} Datacenters",
        total_components=len(all_components),
        components_by_type=components_by_type,
        components=[asdict(c) for c in all_components],  # Convert to dicts for JSON
        overall_health_score=round(overall_health, 1),
        critical_issues=critical_issues,
        upgrade_recommendations=upgrade_recommendations,
        estimated_total_upgrade_cost=total_upgrade_cost,
        priority_upgrades=priority_upgrades,
        sites=sites,
        issues_by_location=issues_by_location,
        components_by_location=components_by_location,
        health_by_location=health_by_location_avg,
        growth_by_location=growth_by_location,
    )

    execution.datacenter_analysis = analysis

    add_thought(execution, agent_id, agent_name, ThoughtType.DATA.value,
                "Headend component analysis complete. Passing to Capacity Forecaster.",
                88)

    return analysis


async def run_capacity_forecaster_agent(
    db: Session,
    execution: AgenticCapacityPlanningExecution,
    timeout_seconds: float = 60.0,
) -> Dict[str, Any]:
    """
    Capacity Forecaster Agent - Uses LLM to generate forecasts with upgrade context.

    This agent combines all previous data and generates:
    - 30/60/90 day capacity forecasts
    - Recommendations
    - Risk assessments
    """
    agent_id = AgentType.CAPACITY_FORECASTER.value
    agent_name = "Capacity Forecaster"

    execution.current_agent = agent_id
    execution.current_agent_name = agent_name

    add_thought(execution, agent_id, agent_name, ThoughtType.THOUGHT.value,
                "Building comprehensive capacity forecast...", 78)

    await asyncio.sleep(0.3)

    data = execution.data_collector_output or {}
    upgrade_analysis = execution.upgrade_analysis
    hardware_report = execution.hardware_compatibility

    # Get trend data
    add_thought(execution, agent_id, agent_name, ThoughtType.TOOL_CALL.value,
                "Fetching 7-day KPI trends for growth analysis...", 80)

    try:
        trend_data = get_kpi_trends(db, period_hours=168, max_points=50)
    except Exception:
        trend_data = []

    await asyncio.sleep(0.2)

    # Get period comparisons
    try:
        comparisons = calculate_period_comparison(db, period_hours=168)
    except Exception:
        comparisons = []

    add_thought(execution, agent_id, agent_name, ThoughtType.ANALYSIS.value,
                f"Analyzing {len(trend_data)} trend data points...", 82)

    await asyncio.sleep(0.3)

    # Check for LLM config
    llm_config = _get_llm_config(db)

    if not llm_config:
        add_thought(execution, agent_id, agent_name, ThoughtType.THOUGHT.value,
                    "LLM not configured - using rule-based forecasting", 85)
        result = _generate_rule_based_forecast(execution, data, trend_data)
    else:
        add_thought(execution, agent_id, agent_name, ThoughtType.TOOL_CALL.value,
                    f"Calling LLM ({llm_config['provider']}) for advanced forecasting...", 85)

        try:
            result = await _call_llm_for_forecast(
                execution, data, trend_data, comparisons, llm_config, timeout_seconds
            )
            add_thought(execution, agent_id, agent_name, ThoughtType.TOOL_RESULT.value,
                        "LLM analysis complete", 92)
        except Exception as e:
            add_thought(execution, agent_id, agent_name, ThoughtType.ERROR.value,
                        f"LLM call failed: {str(e)}, falling back to rule-based", 88)
            result = _generate_rule_based_forecast(execution, data, trend_data)

    await asyncio.sleep(0.2)

    # Add upgrade-specific recommendations if applicable
    if upgrade_analysis:
        add_thought(execution, agent_id, agent_name, ThoughtType.ANALYSIS.value,
                    "Incorporating upgrade impact into recommendations...", 95)

        upgrade_rec = (
            f"Upgrading {upgrade_analysis.nodes_analyzed} nodes to {upgrade_analysis.upgrade_target} "
            f"will increase bandwidth by {upgrade_analysis.bandwidth_improvement_percent:.1f}% "
            f"and reduce latency by {upgrade_analysis.latency_improvement_percent:.1f}%"
        )
        result["recommendations"] = [upgrade_rec] + result.get("recommendations", [])

        # Add upgrade context to forecasts
        result["upgrade_impact"] = asdict(upgrade_analysis)

    if hardware_report:
        cost_rec = (
            f"Estimated upgrade cost: ${hardware_report.estimated_total_cost:,.0f} "
            f"({hardware_report.compatible_count} compatible, "
            f"{hardware_report.partial_upgrade_count} partial upgrades, "
            f"{hardware_report.replacement_count} replacements)"
        )
        result["recommendations"] = result.get("recommendations", []) + [cost_rec]
        result["hardware_compatibility"] = asdict(hardware_report)

    execution.result = result

    add_thought(execution, agent_id, agent_name, ThoughtType.DATA.value,
                "Capacity forecast complete. Analysis ready for review.", 100)

    return result


def _get_llm_config(db: Session) -> Optional[Dict[str, Any]]:
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


def _generate_rule_based_forecast(
    execution: AgenticCapacityPlanningExecution,
    data: Dict[str, Any],
    trend_data: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Generate a rule-based forecast when LLM is unavailable"""

    # Estimate growth from trend data
    growth_rate = 2.5  # Default 2.5% per month
    trend_direction = "stable"

    if trend_data and len(trend_data) >= 2:
        first_throughput = trend_data[0].get('throughput_mbps', 100)
        last_throughput = trend_data[-1].get('throughput_mbps', 100)
        if first_throughput > 0:
            weekly_change = ((last_throughput - first_throughput) / first_throughput) * 100
            growth_rate = weekly_change * 4
            if weekly_change > 2:
                trend_direction = "growing"
            elif weekly_change < -2:
                trend_direction = "declining"

    current_utilization = data.get("avg_cpu_utilization", 50)
    current_bandwidth_gbps = data.get("total_bandwidth_gbps", 100)

    # Generate forecasts using custom periods from execution
    periods = execution.forecast_periods if execution.forecast_periods else [30, 60, 90]
    forecasts = []
    for days in periods:
        months = days / 30
        projected_growth = 1 + (growth_rate / 100) * months

        proj_util = min(95, current_utilization * projected_growth)
        proj_bw = current_bandwidth_gbps * projected_growth

        # Determine risk level
        if proj_util > 85:
            risk = "critical"
        elif proj_util > 75:
            risk = "high"
        elif proj_util > 60:
            risk = "medium"
        else:
            risk = "low"

        forecasts.append({
            "period_days": days,
            "projected_node_utilization": round(proj_util, 1),
            "projected_dc_utilization": round(proj_util * 0.9, 1),
            "projected_bandwidth_usage_gbps": round(proj_bw, 2),
            "confidence": round(0.7 - (days / 300), 2),
            "risk_level": risk,
        })

    # Generate recommendations
    recommendations = []
    if trend_direction == "growing" and growth_rate > 3:
        recommendations.append("High growth rate detected - plan capacity expansion within 60 days")
    if current_utilization > 70:
        recommendations.append(f"Current utilization at {current_utilization:.1f}% - consider load balancing")
    if not recommendations:
        recommendations.append("Current capacity is adequate - continue monitoring trends")

    # Generate per-datacenter forecasts from site data
    datacenter_forecasts = []
    dc_list = data.get("datacenters", [])
    site_data = execution.datacenter_analysis.sites if execution.datacenter_analysis else []

    for dc in dc_list:
        dc_id = dc.get("dc_id", "unknown")
        dc_name = dc.get("name", "Unknown")
        dc_city = dc.get("city", "Unknown")
        power_cap = dc.get("power_capacity_mw", 0) or 0
        current_power = dc.get("current_power_mw", 0) or 0
        total_racks = dc.get("total_rack_units", 0) or 0
        used_racks = dc.get("used_rack_units", 0) or 0

        current_power_util = (current_power / power_cap * 100) if power_cap > 0 else 0
        current_rack_util = (used_racks / total_racks * 100) if total_racks > 0 else 0

        # Find matching site for growth rate
        site_growth = 0.0
        site_health = 100.0
        for site in site_data:
            if site.get("dc_id") == dc_id:
                site_growth = site.get("avg_growth_per_week", 0) or 0
                site_health = site.get("health_score", 100)
                break

        # Monthly growth rate from weekly (or use the global growth rate)
        monthly_growth = (site_growth * 4) if site_growth > 0 else growth_rate

        dc_forecasts = []
        for days in periods:
            months = days / 30
            growth_factor = 1 + (monthly_growth / 100) * months
            proj_power = min(100, current_power_util * growth_factor)
            proj_rack = min(100, current_rack_util * growth_factor)

            if proj_power > 90 or proj_rack > 90:
                risk = "critical"
            elif proj_power > 80 or proj_rack > 80:
                risk = "high"
            elif proj_power > 65 or proj_rack > 65:
                risk = "medium"
            else:
                risk = "low"

            dc_forecasts.append({
                "period_days": days,
                "projected_power_util": round(proj_power, 1),
                "projected_rack_util": round(proj_rack, 1),
                "risk_level": risk,
            })

        datacenter_forecasts.append({
            "dc_id": dc_id,
            "dc_name": dc_name,
            "city": dc_city,
            "current_power_util": round(current_power_util, 1),
            "current_rack_util": round(current_rack_util, 1),
            "health_score": round(site_health, 1),
            "growth_rate_per_month": round(monthly_growth, 1),
            "forecasts": dc_forecasts,
        })

    # Extract bandwidth bottlenecks from datacenter analysis
    bandwidth_bottlenecks = []
    capacity_constraints = []
    analysis_parts = []

    if execution.datacenter_analysis:
        dc_analysis = execution.datacenter_analysis

        # Extract bottlenecks from sites with high utilization
        if dc_analysis.sites:
            for site in dc_analysis.sites:
                # Power bottleneck
                power_util = site.get("power_utilization_percent", 0)
                if power_util >= 75:
                    bandwidth_bottlenecks.append({
                        "location": f"{site.get('name', 'Unknown')} (Power)",
                        "current_utilization": power_util,
                        "projected_breach_days": max(7, int((100 - power_util) / (site.get("avg_growth_per_week", 1) or 1) * 7)) if power_util < 100 else 0,
                    })

                # Rack space bottleneck
                rack_util = site.get("rack_utilization_percent", 0)
                if rack_util >= 80:
                    bandwidth_bottlenecks.append({
                        "location": f"{site.get('name', 'Unknown')} (Rack Space)",
                        "current_utilization": rack_util,
                        "projected_breach_days": max(7, int((100 - rack_util) / (site.get("avg_growth_per_week", 1) or 1) * 7)) if rack_util < 100 else 0,
                    })

        # Extract capacity constraints from components
        if dc_analysis.upgrade_recommendations:
            cpu_issues = []
            memory_issues = []
            bandwidth_issues = []

            for rec in dc_analysis.upgrade_recommendations:
                issues = rec.get("issues", [])
                comp_name = f"{rec.get('component_type', '')} {rec.get('name', '')}"
                for issue in issues:
                    issue_lower = issue.lower()
                    if "cpu" in issue_lower:
                        cpu_issues.append(comp_name)
                    elif "memory" in issue_lower:
                        memory_issues.append(comp_name)
                    elif "bandwidth" in issue_lower or "utilization" in issue_lower:
                        bandwidth_issues.append(comp_name)

            if cpu_issues:
                capacity_constraints.append({
                    "resource": "CPU",
                    "severity": "high" if len(cpu_issues) > 3 else "medium",
                    "affected_components": cpu_issues[:5],
                })
            if memory_issues:
                capacity_constraints.append({
                    "resource": "Memory",
                    "severity": "high" if len(memory_issues) > 3 else "medium",
                    "affected_components": memory_issues[:5],
                })
            if bandwidth_issues:
                capacity_constraints.append({
                    "resource": "Bandwidth",
                    "severity": "high" if len(bandwidth_issues) > 3 else "medium",
                    "affected_components": bandwidth_issues[:5],
                })

        # Build analysis summary
        critical_count = len(dc_analysis.critical_issues) if dc_analysis.critical_issues else 0
        if critical_count > 0:
            analysis_parts.append(f"{critical_count} critical issues require immediate attention")
        if bandwidth_bottlenecks:
            analysis_parts.append(f"{len(bandwidth_bottlenecks)} infrastructure bottlenecks identified")
        if capacity_constraints:
            analysis_parts.append(f"{len(capacity_constraints)} resource constraints detected")

    # Build final analysis summary
    if analysis_parts:
        analysis_summary = f"{trend_direction.title()} trend with {growth_rate:.1f}%/month growth. " + ". ".join(analysis_parts) + "."
    else:
        analysis_summary = f"Rule-based analysis: {trend_direction.title()} trend with {growth_rate:.1f}%/month growth."

    return {
        "trend_direction": trend_direction,
        "growth_rate_percent_per_month": round(growth_rate, 1),
        "current_node_utilization": current_utilization,
        "current_dc_utilization": current_utilization * 0.9,
        "total_throughput_gbps": current_bandwidth_gbps,
        "forecasts": forecasts,
        "datacenter_forecasts": datacenter_forecasts,
        "bandwidth_bottlenecks": bandwidth_bottlenecks,
        "capacity_constraints": capacity_constraints,
        "analysis_summary": analysis_summary,
        "recommendations": recommendations,
    }


async def _call_llm_for_forecast(
    execution: AgenticCapacityPlanningExecution,
    data: Dict[str, Any],
    trend_data: List[Dict[str, Any]],
    comparisons: List[Dict[str, Any]],
    llm_config: Dict[str, Any],
    timeout_seconds: float,
) -> Dict[str, Any]:
    """Call LLM for advanced capacity forecasting"""

    # Build prompt
    messages = _build_forecast_prompt(execution, data, trend_data, comparisons)

    # Build API request
    provider = llm_config["provider"]
    api_url = llm_config["endpoint_url"]

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
    job_id = llm_queue.submit_and_process_parallel(
        messages=messages,
        provider=provider,
        api_url=api_url,
        headers=headers,
        payload=payload,
        priority=3,
    )

    result = llm_queue.wait_for_job(job_id, timeout=timeout_seconds)

    if not result:
        raise Exception("LLM returned empty response")

    # Extract content
    response_content = ""
    if isinstance(result, dict):
        if "choices" in result and result["choices"]:
            response_content = result["choices"][0].get("message", {}).get("content", "")
        elif "content" in result:
            response_content = result["content"]
    elif isinstance(result, str):
        response_content = result

    if not response_content:
        raise Exception("Empty response content from LLM")

    # Parse response
    analysis = _parse_llm_response(response_content)
    if not analysis:
        raise Exception("Failed to parse LLM response")

    return analysis


def _build_forecast_prompt(
    execution: AgenticCapacityPlanningExecution,
    data: Dict[str, Any],
    trend_data: List[Dict[str, Any]],
    comparisons: List[Dict[str, Any]],
) -> List[Dict[str, str]]:
    """Build the LLM prompt for capacity forecasting"""

    # Use custom forecast periods from execution
    periods = execution.forecast_periods if execution.forecast_periods else [30, 60, 90]
    forecast_examples = ",\n        ".join(
        f'{{"period_days": {d}, "projected_node_utilization": <percent>, "projected_dc_utilization": <percent>, "projected_bandwidth_usage_gbps": <number>, "confidence": <0-1>, "risk_level": "low|medium|high|critical"}}'
        for d in periods
    )

    system_prompt = f"""You are an expert cable/ISP network capacity planner. Analyze the provided network data and generate capacity forecasts.

You must respond with ONLY a valid JSON object containing:
{{
    "trend_direction": "growing|stable|declining",
    "growth_rate_percent_per_month": <number>,
    "current_node_utilization": <percent>,
    "current_dc_utilization": <percent>,
    "total_throughput_gbps": <number>,
    "forecasts": [
        {forecast_examples}
    ],
    "datacenter_forecasts": [
        {{"dc_id": "<id>", "dc_name": "<name>", "city": "<city>", "current_power_util": <percent>, "current_rack_util": <percent>, "forecasts": [
            {{"period_days": <days>, "projected_power_util": <percent>, "projected_rack_util": <percent>, "risk_level": "low|medium|high|critical"}}
        ]}}
    ],
    "bandwidth_bottlenecks": [{{"location": "<name>", "current_utilization": <percent>, "projected_breach_days": <number or null>}}],
    "capacity_constraints": [{{"resource": "cpu|memory|bandwidth", "affected_components": ["list"], "severity": "low|medium|high"}}],
    "analysis_summary": "2-3 sentence analysis",
    "recommendations": ["Recommendation 1", "Recommendation 2", "Recommendation 3"]
}}

IMPORTANT: Generate forecasts for exactly these periods (in days): {periods}. Include per-datacenter forecasts for each datacenter in the data."""

    # Build context
    context = f"""
=== CURRENT NETWORK STATE ===
- Total Nodes: {data.get('total_nodes', 0):,}
- Filtered Nodes: {data.get('filtered_nodes', 0):,}
- Total Bandwidth: {data.get('total_bandwidth_gbps', 0):.2f} Gbps
- Avg Throughput per Node: {data.get('avg_throughput_mbps', 0):.1f} Mbps
- Avg Latency: {data.get('avg_latency_ms', 0):.1f} ms
- Avg CPU Utilization: {data.get('avg_cpu_utilization', 0):.1f}%
- Region Filter: {data.get('region', 'All')}
- City Filter: {data.get('city', 'All')}
- Forecast Periods: {periods} days

Nodes by Backhaul Type:
"""
    for bt, count in data.get('nodes_by_backhaul', {}).items():
        context += f"  - {bt}: {count} nodes\n"

    # Include datacenter/site data for per-location analysis
    dc_list = data.get('datacenters', [])
    if dc_list:
        context += f"\n=== DATACENTERS ({len(dc_list)} sites) ===\n"
        for dc in dc_list:
            power_cap = dc.get('power_capacity_mw', 0) or 0
            current_power = dc.get('current_power_mw', 0) or 0
            power_util = (current_power / power_cap * 100) if power_cap > 0 else 0
            total_racks = dc.get('total_rack_units', 0) or 0
            used_racks = dc.get('used_rack_units', 0) or 0
            rack_util = (used_racks / total_racks * 100) if total_racks > 0 else 0
            context += (
                f"  - {dc.get('name', 'Unknown')} ({dc.get('dc_id', '?')}) in {dc.get('city', '?')}: "
                f"Power {power_util:.1f}% ({current_power:.1f}/{power_cap:.1f} MW), "
                f"Rack {rack_util:.1f}% ({used_racks}/{total_racks} RU), "
                f"Status: {dc.get('status', '?')}\n"
            )

    # Include DC component analysis if available
    if execution.datacenter_analysis and execution.datacenter_analysis.sites:
        context += "\n=== DATACENTER COMPONENT HEALTH ===\n"
        for site in execution.datacenter_analysis.sites:
            context += (
                f"  - {site.get('name', '?')} ({site.get('dc_id', '?')}): "
                f"Health {site.get('health_score', 0):.1f}%, "
                f"{site.get('critical_count', 0)} critical, {site.get('high_count', 0)} high priority, "
                f"Growth {site.get('avg_growth_per_week', 0):.1f}%/week\n"
            )

    if execution.upgrade_analysis:
        ua = execution.upgrade_analysis
        context += f"""
=== UPGRADE SCENARIO ===
- Target Backhaul: {ua.upgrade_target}
- Nodes to Upgrade: {ua.nodes_analyzed}
- Current Bandwidth: {ua.current_total_bandwidth_gbps} Gbps
- Projected Bandwidth: {ua.projected_total_bandwidth_gbps} Gbps (+{ua.bandwidth_improvement_percent}%)
- Current Latency: {ua.current_avg_latency_ms} ms
- Projected Latency: {ua.projected_avg_latency_ms} ms (-{ua.latency_improvement_percent}%)
"""

    if trend_data and len(trend_data) >= 2:
        first = trend_data[0]
        last = trend_data[-1]
        context += f"""
=== 7-DAY TRENDS ===
Throughput: {first.get('throughput_mbps', 0):.1f} -> {last.get('throughput_mbps', 0):.1f} Mbps
Active Modems: {first.get('active_modems', 0):.0f} -> {last.get('active_modems', 0):.0f}
CPU: {first.get('cpu_utilization', 0):.1f}% -> {last.get('cpu_utilization', 0):.1f}%
"""

    context += "\nProvide capacity forecasts in the specified JSON format. Include per-datacenter forecasts for each datacenter listed above."

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": context},
    ]


def _parse_llm_response(response_content: str) -> Dict[str, Any]:
    """Parse LLM response JSON"""
    try:
        return json.loads(response_content)
    except json.JSONDecodeError:
        pass

    # Try markdown code block
    json_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', response_content)
    if json_match:
        try:
            return json.loads(json_match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # Try to find JSON object
    json_match = re.search(r'\{[\s\S]*\}', response_content)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass

    return {}


# ===== MAIN ORCHESTRATION =====

async def run_agentic_capacity_planning(
    db: Session,
    execution: AgenticCapacityPlanningExecution,
) -> AgenticCapacityPlanningExecution:
    """
    Run the full agentic capacity planning pipeline.

    Pipeline:
    1. Data Collector Agent - Gather node/DC data
    2. Upgrade Analyzer Agent - Calculate upgrade impact (if applicable)
    3. Hardware Checker Agent - Check compatibility (if applicable)
    4. Headend Component Analyzer Agent - Analyze headend components and recommend upgrades
    5. Capacity Forecaster Agent - Generate forecasts
    """
    try:
        execution.status = ExecutionStatus.RUNNING.value
        save_execution_to_db(db, execution)

        # Agent 1: Data Collector
        await run_data_collector_agent(db, execution)
        save_execution_to_db(db, execution)

        # Agent 2: Upgrade Analyzer
        await run_upgrade_analyzer_agent(db, execution)
        save_execution_to_db(db, execution)

        # Agent 3: Hardware Checker
        await run_hardware_checker_agent(db, execution)
        save_execution_to_db(db, execution)

        # Agent 4: Datacenter Component Analyzer
        await run_datacenter_component_analyzer_agent(db, execution)
        save_execution_to_db(db, execution)

        # Agent 5: Capacity Forecaster
        await run_capacity_forecaster_agent(db, execution)

        execution.status = ExecutionStatus.COMPLETED.value
        execution.completed_at = datetime.utcnow().isoformat()
        save_execution_to_db(db, execution)

    except Exception as e:
        execution.status = ExecutionStatus.FAILED.value
        execution.error = str(e)
        execution.completed_at = datetime.utcnow().isoformat()
        add_thought(execution, "system", "System", ThoughtType.ERROR.value,
                    f"Execution failed: {str(e)}", execution.progress_percent)
        save_execution_to_db(db, execution)

    return execution


def start_agentic_capacity_planning(
    db: Session,
    analysis_mode: str = "current_state",
    target_backhaul_type: Optional[str] = None,
    current_backhaul_filter: Optional[List[str]] = None,
    region: Optional[str] = None,
    city: Optional[str] = None,
    datacenter_ids: Optional[List[str]] = None,
    node_ids: Optional[List[str]] = None,
    include_nodes: bool = True,
    include_datacenters: bool = True,
    include_cost_estimate: bool = True,
    forecast_periods: Optional[List[int]] = None,
) -> str:
    """
    Start an agentic capacity planning execution.

    Args:
        analysis_mode: "current_state" or "upgrade_scenario"
        target_backhaul_type: Target backhaul for upgrade analysis (e.g., "Fiber", "5G")
        current_backhaul_filter: Filter nodes by current backhaul types
        region: Filter by geographic region (e.g., "USA", "APAC")
        city: Filter by city (e.g., "New York", "Los Angeles")
        datacenter_ids: List of specific datacenter IDs to analyze
        node_ids: List of specific node IDs to analyze
        include_nodes: Include nodes in analysis (default True)
        include_datacenters: Include datacenters in analysis (default True)
        include_cost_estimate: Include cost estimates in results
        forecast_periods: Custom forecast periods in days (default [30, 60, 90])

    Returns the execution_id which can be used to poll for status.
    """
    execution = create_execution(
        db=db,
        analysis_mode=analysis_mode,
        target_backhaul_type=target_backhaul_type,
        current_backhaul_filter=current_backhaul_filter or [],
        region=region,
        city=city,
        datacenter_ids=datacenter_ids or [],
        node_ids=node_ids or [],
        include_nodes=include_nodes,
        include_datacenters=include_datacenters,
        include_cost_estimate=include_cost_estimate,
        forecast_periods=forecast_periods,
    )

    # Start the async execution in a background task
    import asyncio

    def run_in_background():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(run_agentic_capacity_planning(db, execution))
        finally:
            loop.close()

    import threading
    thread = threading.Thread(target=run_in_background, daemon=True)
    thread.start()

    return execution.execution_id


def get_execution_status(execution_id: str, db: Optional[Session] = None) -> Optional[Dict[str, Any]]:
    """Get the current status of an execution.

    First checks in-memory cache, then falls back to database for multi-worker support.
    """
    # First check in-memory cache
    execution = get_execution(execution_id)

    if execution:
        # Found in memory, return from execution object
        return {
            "execution_id": execution.execution_id,
            "status": execution.status,
            "started_at": execution.started_at,
            "completed_at": execution.completed_at,
            "current_agent": execution.current_agent,
            "current_agent_name": execution.current_agent_name,
            "progress_percent": execution.progress_percent,
            "thoughts": [asdict(t) for t in execution.thoughts],
            "analysis_mode": execution.analysis_mode,
            "target_backhaul_type": execution.target_backhaul_type,
            "upgrade_analysis": asdict(execution.upgrade_analysis) if execution.upgrade_analysis else None,
            "hardware_compatibility": asdict(execution.hardware_compatibility) if execution.hardware_compatibility else None,
            "datacenter_analysis": asdict(execution.datacenter_analysis) if execution.datacenter_analysis else None,
            "result": execution.result,
            "error": execution.error,
        }

    # Not in memory - try loading from database (multi-worker scenario)
    if db:
        db_status = load_execution_from_db(db, execution_id)
        if db_status:
            return db_status

    return None
