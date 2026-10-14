"""
Agent Studio Router - Complex Multi-Agent Workflow for Cable Network Operations

This module provides a LangChain-based multi-agent system that:
1. Understands natural language queries about network operations
2. Uses fuzzy matching for regions, manufacturers, and cable network terminology
3. Delegates to specialized agents for data retrieval, analysis, prediction, and visualization
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime
import uuid
import asyncio
import re
from difflib import SequenceMatcher

from sqlalchemy.orm import Session
from ..database import get_db
from ..models import FiberNodeModel, KPIMetricsModel, AlertModel, SelfHealingActionModel
from ..llm_queue import llm_queue
from ..ai_analyzer import get_llm_config

router = APIRouter(prefix="/api/v1/agent-studio", tags=["agent-studio"])


# ============================================
# Fuzzy Search & Terminology Mapping
# ============================================

# Region mappings - supports fuzzy matching
REGION_MAPPINGS = {
    # Europe variations
    "europe": "EUROPE",
    "european": "EUROPE",
    "eu": "EUROPE",
    "uk": "UK",
    "united kingdom": "UK",
    "britain": "UK",
    "british": "UK",
    "ireland": "IRELAND",
    "irish": "IRELAND",
    # North America
    "north america": "USA",
    "usa": "USA",
    "us": "USA",
    "united states": "USA",
    "america": "USA",
    "american": "USA",
    "canada": "CANADA",
    "canadian": "CANADA",
    # Asia Pacific
    "asia": "APAC",
    "asian": "APAC",
    "apac": "APAC",
    "asia pacific": "APAC",
    "pacific": "APAC",
    # Middle East
    "middle east": "MIDDLE_EAST",
    "middle eastern": "MIDDLE_EAST",
    "mideast": "MIDDLE_EAST",
    # Africa
    "africa": "AFRICA",
    "african": "AFRICA",
    # Australia/NZ
    "australia": "AUSTRALIA_NZ",
    "australian": "AUSTRALIA_NZ",
    "new zealand": "AUSTRALIA_NZ",
    "oceania": "AUSTRALIA_NZ",
    "anz": "AUSTRALIA_NZ",
}

# Geographic region groupings
GEOGRAPHIC_REGIONS = {
    "Europe": ["UK", "IRELAND", "EUROPE"],
    "North America": ["USA", "CANADA"],
    "Asia Pacific": ["APAC", "MIDDLE_EAST"],
    "Oceania": ["AUSTRALIA_NZ"],
    "Africa": ["AFRICA"],
}

# Cable network terminology mappings
CABLE_TERMINOLOGY = {
    # KPI-related terms
    "backhaul": ["latency_ms", "downstream_throughput_mbps", "packet_loss_percent"],
    "latency": ["latency_ms"],
    "delay": ["latency_ms"],
    "throughput": ["downstream_throughput_mbps"],
    "bandwidth": ["downstream_throughput_mbps"],
    "packet loss": ["packet_loss_percent"],
    "high packet loss": ["packet_loss_percent"],
    "signal issues": ["packet_loss_percent"],
    "signal quality": ["ds_snr_db", "packet_loss_percent"],
    "snr": ["ds_snr_db", "us_snr_db"],
    "channel bonding": ["ds_channel_utilization_percent", "us_channel_utilization_percent"],
    "cpu": ["node_cpu_utilization"],
    "memory": ["node_memory_utilization"],
    "temperature": ["node_temperature"],
    "overheating": ["node_temperature"],
    "congestion": ["node_cpu_utilization", "node_memory_utilization", "active_modems"],
    "capacity": ["active_modems", "downstream_throughput_mbps"],
    # Issue types
    "performance": ["ds_snr_db", "packet_loss_percent", "latency_ms", "downstream_throughput_mbps"],
    "degraded": ["ds_snr_db", "packet_loss_percent"],
    "outage": ["status"],
    "failure": ["status", "ds_snr_db"],
}

# Manufacturer mappings
MANUFACTURER_MAPPINGS = {
    "cisco": "Cisco",
    "commscope": "CommScope/Arris",
    "commscope/arris": "CommScope/Arris",
    "arris": "CommScope/Arris",
    "casa": "Casa Systems",
    "casa systems": "Casa Systems",
    "harmonic": "Harmonic",
    "vecima": "Vecima Networks",
    "vecima networks": "Vecima Networks",
    "calix": "Calix",
}


def fuzzy_match_region(query: str) -> List[str]:
    """Extract and match region from natural language query"""
    query_lower = query.lower()
    matched_regions = []

    # Direct mapping check
    for term, region in REGION_MAPPINGS.items():
        if term in query_lower:
            if region not in matched_regions:
                matched_regions.append(region)

    # Check geographic region groups
    for group_name, regions in GEOGRAPHIC_REGIONS.items():
        if group_name.lower() in query_lower:
            matched_regions.extend([r for r in regions if r not in matched_regions])

    # Fuzzy matching for misspellings
    if not matched_regions:
        words = re.findall(r'\b\w+\b', query_lower)
        for word in words:
            for term, region in REGION_MAPPINGS.items():
                if len(word) > 3 and SequenceMatcher(None, word, term).ratio() > 0.8:
                    if region not in matched_regions:
                        matched_regions.append(region)

    return matched_regions


def extract_cable_metrics(query: str) -> List[str]:
    """Extract relevant KPI metrics from natural language query"""
    query_lower = query.lower()
    metrics = []

    for term, metric_list in CABLE_TERMINOLOGY.items():
        if term in query_lower:
            metrics.extend([m for m in metric_list if m not in metrics])

    return metrics


def extract_manufacturer(query: str) -> Optional[str]:
    """Extract manufacturer from query"""
    query_lower = query.lower()
    for term, manufacturer in MANUFACTURER_MAPPINGS.items():
        if term in query_lower:
            return manufacturer
    return None


# ============================================
# Data Models
# ============================================

class AgentType(str, Enum):
    MANAGER = "manager"
    WORKER = "worker"


class AgentConfig(BaseModel):
    id: str
    name: str
    role: str
    goal: str
    backstory: str
    tools: List[str] = []
    type: AgentType = AgentType.WORKER
    allow_delegation: bool = False


class ToolConfig(BaseModel):
    id: str
    name: str
    description: str
    agent_id: str


class WorkflowConfig(BaseModel):
    id: str
    name: str
    description: str
    manager_agent_id: str
    is_conversational: bool = True
    agents: List[AgentConfig]
    tools: List[ToolConfig]


class ExecuteRequest(BaseModel):
    workflow_id: str
    user_input: str
    context: Dict[str, Any] = {}


class ThoughtMessage(BaseModel):
    id: str
    timestamp: str
    agent_id: str
    agent_name: str
    type: str  # thought, action, observation, tool_call, tool_result, final_answer
    content: str
    tool_name: Optional[str] = None
    tool_input: Optional[Dict] = None
    tool_output: Optional[Dict] = None


class ExecutionResponse(BaseModel):
    execution_id: str
    status: str  # pending, running, completed, failed
    workflow_id: str
    user_input: str
    thoughts: List[ThoughtMessage] = []
    final_output: Optional[str] = None
    visualization: Optional[Dict] = None
    started_at: str
    completed_at: Optional[str] = None


# ============================================
# Storage & Configuration
# ============================================

_executions: Dict[str, ExecutionResponse] = {}

# Full Cable Network Operations Workflow
DEFAULT_WORKFLOW = WorkflowConfig(
    id="cable-network-ops",
    name="Cable Network Operations Workflow",
    description="""Multi-agent workflow for network KPI analysis, failure prediction, and visualization.

Example queries:
- Analyze the backhaul issues affecting latency in our European nodes
- Retrieve KPI data for Cisco nodes and identify any anomalies
- Compare packet loss rates between manufacturers over the last 7 days
- Which nodes are likely to fail in the next 2 hours?
- Show me poorly performing regions
- What's causing the degraded service in APAC?""",
    manager_agent_id="noc-manager",
    is_conversational=True,
    agents=[
        AgentConfig(
            id="noc-manager",
            name="NOC Manager",
            role="Network Operations Center Manager",
            goal="Delegate tasks to specialized agents, coordinate analysis, and provide comprehensive responses",
            backstory="""You are an experienced NOC Manager who coordinates network operations analysis.
You understand cable network terminology and can interpret natural language queries about network issues.
When users mention regions like 'European', 'APAC', or 'American', you know how to map these to the correct database regions.
You delegate to specialists: Network Data Analyst for data retrieval, Predictive Analyst for failure prediction,
Network Researcher for industry standards, and Visualization Specialist for charts.""",
            tools=[],
            type=AgentType.MANAGER,
            allow_delegation=True,
        ),
        AgentConfig(
            id="network-data-analyst",
            name="Network Data Analyst",
            role="Network Data Analyst",
            goal="Retrieve and analyze network KPI data from fiber nodes",
            backstory="""You are a skilled network data analyst who retrieves and analyzes KPI data from fiber nodes.
You use the Network Data Retrieval Tool to fetch node, KPI, alert, and action data.

IMPORTANT: When filtering by region, use these exact values:
- USA, CANADA (North America)
- UK, IRELAND, EUROPE (European regions)
- APAC, MIDDLE_EAST (Asia)
- AUSTRALIA_NZ (Oceania)
- AFRICA

For 'European nodes', query for regions: UK, IRELAND, EUROPE
For backhaul issues, focus on: latency_ms, downstream_throughput_mbps, packet_loss_percent

Always include statistics in your analysis and format results in clear tables.""",
            tools=["network-data-retrieval", "network-analysis"],
            type=AgentType.WORKER,
        ),
        AgentConfig(
            id="predictive-analyst",
            name="Predictive Analyst",
            role="Predictive Failure Analyst",
            goal="Predict node failures and analyze geographic performance patterns",
            backstory="""You are a predictive analyst who forecasts node failures and identifies at-risk infrastructure.
You analyze KPI trends, environmental factors, and historical patterns to predict failures.

For geographic analysis, you understand that:
- 'European' means UK, IRELAND, EUROPE regions
- 'American' means USA, CANADA regions
- 'Asian' means APAC, MIDDLE_EAST regions

When analyzing latency/backhaul issues, focus on:
- latency_ms > 50ms indicates problems
- packet_loss_percent > 1% is concerning
- downstream_throughput_mbps < 50 suggests congestion

Format predictions with risk scores and recommended actions.""",
            tools=["predictive-failure", "geographic-performance"],
            type=AgentType.WORKER,
        ),
        AgentConfig(
            id="network-researcher",
            name="Network Researcher",
            role="Network Standards Researcher",
            goal="Research industry standards, best practices, and troubleshooting guides",
            backstory="""You research CableLabs/SCTE standards, vendor documentation, and industry best practices.
For backhaul issues, you can find relevant standards for latency thresholds and troubleshooting guides.
You provide context from industry standards to support analysis findings.""",
            tools=["internet-search"],
            type=AgentType.WORKER,
        ),
        AgentConfig(
            id="visualization-specialist",
            name="Visualization Specialist",
            role="Data Visualization Specialist",
            goal="Create informative visualizations from network data",
            backstory="""You create charts and visualizations to help understand network performance.
You can create bar charts comparing regions, line charts showing trends, pie charts for distribution,
and heatmaps for geographic analysis. Always choose the most appropriate chart type for the data.""",
            tools=["data-visualization"],
            type=AgentType.WORKER,
        ),
    ],
    tools=[
        ToolConfig(
            id="network-data-retrieval",
            name="Network Data Retrieval Tool",
            description="Retrieves nodes, KPIs, alerts, and actions from the network database. Supports filtering by region (USA, CANADA, UK, IRELAND, EUROPE, APAC, MIDDLE_EAST, AUSTRALIA_NZ, AFRICA), manufacturer, status, and time range.",
            agent_id="network-data-analyst"
        ),
        ToolConfig(
            id="network-analysis",
            name="Network Analysis Tool",
            description="Performs statistical analysis on retrieved network data, identifies anomalies, and calculates health scores.",
            agent_id="network-data-analyst"
        ),
        ToolConfig(
            id="predictive-failure",
            name="Predictive Failure Analysis Tool",
            description="Predicts node failures based on KPI trends, assigns risk scores, and identifies nodes likely to fail within specified time windows.",
            agent_id="predictive-analyst"
        ),
        ToolConfig(
            id="geographic-performance",
            name="Geographic Performance Analysis Tool",
            description="Analyzes network performance by geographic location, identifies poorly performing regions and cities.",
            agent_id="predictive-analyst"
        ),
        ToolConfig(
            id="internet-search",
            name="Internet Search Tool",
            description="Searches for CableLabs/SCTE standards, vendor documentation, and troubleshooting guides.",
            agent_id="network-researcher"
        ),
        ToolConfig(
            id="data-visualization",
            name="Data Visualization Tool",
            description="Creates charts (bar, line, pie, heatmap) from network data for visual analysis.",
            agent_id="visualization-specialist"
        ),
    ],
)

# Network Configuration Management Workflow
CONFIG_MANAGEMENT_WORKFLOW = WorkflowConfig(
    id="config-management-ops",
    name="Network Configuration Management Workflow",
    description="""Multi-agent workflow for network device configuration management, compliance, and change orchestration.

Example queries:
- Check compliance of all firewalls
- Review pending change requests
- Analyze drift on switches in the Northeast region
- Recommend VLAN optimization for distribution switches
- Scan all routers for security policy compliance
- What devices have configuration drift?""",
    manager_agent_id="config-orchestrator",
    is_conversational=True,
    agents=[
        AgentConfig(
            id="config-orchestrator",
            name="Config Orchestrator",
            role="Configuration Management Orchestrator",
            goal="Coordinate multi-device configuration changes, validate dependencies, and manage approval workflows",
            backstory="""You are a senior network configuration manager who orchestrates changes across firewalls,
switches, routers, and modems. You understand change management best practices, ITIL change processes,
and risk assessment. You delegate to specialized agents for device-specific analysis and coordinate
multi-device change plans. You ensure all changes follow the approval workflow.""",
            tools=[],
            type=AgentType.MANAGER,
            allow_delegation=True,
        ),
        AgentConfig(
            id="firewall-agent",
            name="Firewall Agent",
            role="Firewall Configuration Specialist",
            goal="Manage firewall ACL rules, security zones, IPS policies, and NAT configurations",
            backstory="""You specialize in firewall configuration management across Fortinet, Palo Alto, and Cisco platforms.
You analyze ACL rules for conflicts, optimize security zone policies, manage IPS signatures,
and ensure NAT configurations are consistent. You can detect overly permissive rules and recommend
hardening changes.""",
            tools=["firewall-config-tool", "acl-management-tool"],
            type=AgentType.WORKER,
        ),
        AgentConfig(
            id="switch-agent",
            name="Switch Agent",
            role="Switch Configuration Specialist",
            goal="Manage VLAN configurations, port security, and STP optimization",
            backstory="""You specialize in switch configuration across Cisco, Arista, and Juniper platforms.
You manage VLAN assignments, optimize spanning tree topology, enforce port security policies,
and ensure DHCP snooping and storm control are properly configured. You can detect VLAN sprawl
and recommend consolidation.""",
            tools=["switch-config-tool", "vlan-management-tool"],
            type=AgentType.WORKER,
        ),
        AgentConfig(
            id="router-agent",
            name="Router Agent",
            role="Router Configuration Specialist",
            goal="Manage BGP/OSPF routing, route tables, and QoS policies",
            backstory="""You specialize in router configuration across Cisco, Juniper, and Nokia platforms.
You optimize OSPF areas, manage BGP peering, tune QoS policies for voice/video/data traffic,
and ensure routing convergence is optimal. You can detect suboptimal routes and recommend
path improvements.""",
            tools=["router-config-tool", "routing-optimization-tool"],
            type=AgentType.WORKER,
        ),
        AgentConfig(
            id="modem-agent",
            name="Modem Agent",
            role="Modem Provisioning Specialist",
            goal="Manage DOCSIS modem provisioning, firmware, and signal optimization",
            backstory="""You specialize in cable modem provisioning and management. You handle DOCSIS 3.0/3.1/4.0
configuration files, firmware deployment, channel bonding optimization, and signal level tuning.
You can identify modems with poor signal quality and recommend provisioning changes.""",
            tools=["modem-provisioning-tool"],
            type=AgentType.WORKER,
        ),
        AgentConfig(
            id="compliance-agent",
            name="Compliance Agent",
            role="Configuration Compliance Specialist",
            goal="Detect configuration drift, enforce policy compliance, and recommend remediation",
            backstory="""You are a compliance specialist who detects configuration drift from baseline templates,
enforces security and operational policies, and recommends remediation actions. You scan devices
against golden configurations and identify non-compliant settings that need correction.""",
            tools=["compliance-scan-tool", "drift-detection-tool"],
            type=AgentType.WORKER,
        ),
    ],
    tools=[
        ToolConfig(
            id="firewall-config-tool",
            name="Firewall Configuration Tool",
            description="Retrieves and modifies firewall configurations including ACLs, security zones, IPS, and NAT rules.",
            agent_id="firewall-agent",
        ),
        ToolConfig(
            id="acl-management-tool",
            name="ACL Management Tool",
            description="Analyzes, optimizes, and validates access control lists for conflicts and security gaps.",
            agent_id="firewall-agent",
        ),
        ToolConfig(
            id="switch-config-tool",
            name="Switch Configuration Tool",
            description="Retrieves and modifies switch configurations including VLANs, STP, and port security.",
            agent_id="switch-agent",
        ),
        ToolConfig(
            id="vlan-management-tool",
            name="VLAN Management Tool",
            description="Manages VLAN assignments, detects VLAN sprawl, and optimizes VLAN topology.",
            agent_id="switch-agent",
        ),
        ToolConfig(
            id="router-config-tool",
            name="Router Configuration Tool",
            description="Retrieves and modifies router configurations including OSPF, BGP, and QoS policies.",
            agent_id="router-agent",
        ),
        ToolConfig(
            id="routing-optimization-tool",
            name="Routing Optimization Tool",
            description="Analyzes routing tables, detects suboptimal paths, and recommends routing improvements.",
            agent_id="router-agent",
        ),
        ToolConfig(
            id="modem-provisioning-tool",
            name="Modem Provisioning Tool",
            description="Manages DOCSIS modem configurations, firmware updates, and provisioning files.",
            agent_id="modem-agent",
        ),
        ToolConfig(
            id="compliance-scan-tool",
            name="Compliance Scan Tool",
            description="Scans device configurations against baseline templates and policies to detect non-compliance.",
            agent_id="compliance-agent",
        ),
        ToolConfig(
            id="drift-detection-tool",
            name="Drift Detection Tool",
            description="Detects configuration drift between running config and golden baseline, reports differences.",
            agent_id="compliance-agent",
        ),
    ],
)

# Config management terminology for fuzzy query matching
CONFIG_TERMINOLOGY = {
    "acl": ["acl_rules", "access_control"],
    "access control": ["acl_rules"],
    "firewall rules": ["acl_rules", "security_zones"],
    "security": ["acl_rules", "ips_enabled", "security_zones"],
    "vlan": ["vlans", "vlan_management"],
    "spanning tree": ["stp_mode", "stp_priority"],
    "stp": ["stp_mode", "stp_priority"],
    "port security": ["port_security_enabled"],
    "routing": ["routing_protocols", "static_routes"],
    "ospf": ["routing_protocols"],
    "bgp": ["routing_protocols"],
    "qos": ["qos_policies"],
    "compliance": ["compliance_status", "drift"],
    "drift": ["compliance_status", "config_drift"],
    "firmware": ["firmware_version"],
    "provisioning": ["provisioning_file", "docsis_version"],
    "modem": ["docsis_version", "downstream_channels"],
    "nat": ["nat_rules", "nat_enabled"],
    "vpn": ["vpn_tunnels"],
}

_workflows: Dict[str, WorkflowConfig] = {
    DEFAULT_WORKFLOW.id: DEFAULT_WORKFLOW,
    CONFIG_MANAGEMENT_WORKFLOW.id: CONFIG_MANAGEMENT_WORKFLOW,
}


# ============================================
# Database Query Functions
# ============================================

def get_network_summary(db: Session, regions: List[str] = None, metrics: List[str] = None) -> Dict:
    """Get comprehensive network data summary with optional region/metric filtering"""
    from sqlalchemy import func, and_

    summary = {
        "nodes": {"total": 0, "by_status": {}, "by_region": {}, "by_manufacturer": {}},
        "kpis": {"latest": [], "statistics": {}},
        "alerts": {"total": 0, "active": 0, "by_severity": {}, "by_type": {}},
        "actions": {"total": 0, "by_status": {}},
    }

    try:
        # Node query with optional region filter
        node_query = db.query(FiberNodeModel)
        if regions:
            node_query = node_query.filter(FiberNodeModel.region.in_(regions))

        nodes = node_query.all()
        summary["nodes"]["total"] = len(nodes)

        for node in nodes:
            # By status
            status = node.status or "unknown"
            summary["nodes"]["by_status"][status] = summary["nodes"]["by_status"].get(status, 0) + 1
            # By region
            region = node.region or "unknown"
            summary["nodes"]["by_region"][region] = summary["nodes"]["by_region"].get(region, 0) + 1
            # By manufacturer
            mfr = node.manufacturer or "unknown"
            summary["nodes"]["by_manufacturer"][mfr] = summary["nodes"]["by_manufacturer"].get(mfr, 0) + 1

        # Get node IDs for filtered regions
        node_ids = [t.node_id for t in nodes] if regions else None

        # KPI statistics with optional filtering
        kpi_query = db.query(KPIMetricsModel)
        if node_ids:
            kpi_query = kpi_query.filter(KPIMetricsModel.node_id.in_(node_ids))

        kpis = kpi_query.order_by(KPIMetricsModel.timestamp.desc()).limit(1000).all()

        if kpis:
            # Calculate statistics for requested metrics or all
            metric_fields = metrics or [
                "ds_snr_db", "packet_loss_percent", "latency_ms",
                "downstream_throughput_mbps", "us_snr_db",
                "node_cpu_utilization", "node_memory_utilization", "node_temperature"
            ]

            for field in metric_fields:
                values = [getattr(kpi, field) for kpi in kpis if getattr(kpi, field, None) is not None]
                if values:
                    summary["kpis"]["statistics"][field] = {
                        "avg": round(sum(values) / len(values), 2),
                        "min": round(min(values), 2),
                        "max": round(max(values), 2),
                        "count": len(values)
                    }

            # Sample of latest KPIs
            summary["kpis"]["latest"] = [
                {
                    "node_id": k.node_id,
                    "timestamp": k.timestamp.isoformat() if k.timestamp else None,
                    "latency_ms": k.latency_ms,
                    "downstream_throughput_mbps": k.downstream_throughput_mbps,
                    "packet_loss_percent": k.packet_loss_percent,
                    "ds_snr_db": k.ds_snr_db,
                }
                for k in kpis[:20]
            ]

        # Alerts with optional node filtering
        alert_query = db.query(AlertModel)
        if node_ids:
            alert_query = alert_query.filter(AlertModel.node_id.in_(node_ids))

        alerts = alert_query.all()
        summary["alerts"]["total"] = len(alerts)
        summary["alerts"]["active"] = len([a for a in alerts if a.status in ["ACTIVE", "active"]])

        for alert in alerts:
            sev = alert.severity or "unknown"
            summary["alerts"]["by_severity"][sev] = summary["alerts"]["by_severity"].get(sev, 0) + 1
            atype = alert.type or "unknown"
            summary["alerts"]["by_type"][atype] = summary["alerts"]["by_type"].get(atype, 0) + 1

        # Actions
        actions = db.query(SelfHealingActionModel).all()
        summary["actions"]["total"] = len(actions)
        for action in actions:
            status = action.status or "unknown"
            summary["actions"]["by_status"][status] = summary["actions"]["by_status"].get(status, 0) + 1

    except Exception as e:
        summary["error"] = str(e)

    return summary


def get_nodes_with_issues(db: Session, regions: List[str] = None, issue_type: str = "latency") -> List[Dict]:
    """Get nodes with specific issues (latency, packet loss, etc.)"""
    from sqlalchemy import and_

    results = []

    try:
        # Get nodes with optional region filter
        node_query = db.query(FiberNodeModel)
        if regions:
            node_query = node_query.filter(FiberNodeModel.region.in_(regions))
        nodes = {t.node_id: t for t in node_query.all()}

        if not nodes:
            return results

        # Get latest KPIs for these nodes
        kpis = db.query(KPIMetricsModel).filter(
            KPIMetricsModel.node_id.in_(nodes.keys())
        ).order_by(KPIMetricsModel.timestamp.desc()).all()

        # Group by node, keep latest
        latest_kpis = {}
        for kpi in kpis:
            if kpi.node_id not in latest_kpis:
                latest_kpis[kpi.node_id] = kpi

        # Filter by issue type
        thresholds = {
            "latency": ("latency_ms", 50, "gt"),  # > 50ms is bad
            "packet_loss": ("packet_loss_percent", 1, "gt"),  # > 1% is bad
            "throughput": ("downstream_throughput_mbps", 50, "lt"),  # < 50 Mbps is bad
            "snr": ("ds_snr_db", 30, "lt"),  # < 30 dB is bad
        }

        field, threshold, comparison = thresholds.get(issue_type, ("latency_ms", 50, "gt"))

        for node_id, kpi in latest_kpis.items():
            value = getattr(kpi, field, None)
            if value is None:
                continue

            is_issue = (comparison == "gt" and value > threshold) or (comparison == "lt" and value < threshold)

            if is_issue:
                node = nodes[node_id]
                results.append({
                    "node_id": node_id,
                    "region": node.region,
                    "city": node.city,
                    "manufacturer": node.manufacturer,
                    "status": node.status,
                    "issue_metric": field,
                    "issue_value": round(value, 2),
                    "threshold": threshold,
                    "latitude": node.latitude,
                    "longitude": node.longitude,
                })

        # Sort by severity (worst first)
        if comparison == "gt":
            results.sort(key=lambda x: x["issue_value"], reverse=True)
        else:
            results.sort(key=lambda x: x["issue_value"])

    except Exception as e:
        return [{"error": str(e)}]

    return results[:50]  # Return top 50


# ============================================
# LLM Integration
# ============================================

async def call_llm(db: Session, messages: List[Dict[str, str]], max_tokens: int = 4000) -> Optional[str]:
    """Call the configured LLM using the shared queue service"""
    config = get_llm_config(db)

    if not config or not config.get("endpoint_url"):
        return None

    provider = config.get("provider", "cloudera")
    api_url = config["endpoint_url"]

    # Build headers based on provider
    headers = {"Content-Type": "application/json"}
    if config.get("jwt_token"):
        headers["Authorization"] = f"Bearer {config['jwt_token']}"
    elif config.get("api_key"):
        if provider == "anthropic":
            headers["x-api-key"] = config["api_key"]
            headers["anthropic-version"] = "2023-06-01"
        else:
            headers["Authorization"] = f"Bearer {config['api_key']}"

    # Build payload
    payload = {
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": config.get("temperature", 0.3),
    }
    if config.get("model_name"):
        payload["model"] = config["model_name"]

    try:
        job_id = llm_queue.submit_and_process_parallel(
            messages=messages,
            provider=provider,
            api_url=api_url,
            headers=headers,
            payload=payload,
            priority=5,
        )

        # Wait for result
        result = llm_queue.wait_for_job(job_id, timeout=90.0)

        if result is None:
            print("LLM call timed out")
            return None

        # Extract response content
        response_content = ""
        if "choices" in result and len(result["choices"]) > 0:
            choice = result["choices"][0]
            if "message" in choice:
                response_content = choice["message"].get("content", "")
            elif "text" in choice:
                response_content = choice["text"]
        elif "content" in result:
            # Anthropic format
            if isinstance(result["content"], list):
                response_content = "".join(
                    block.get("text", "") for block in result["content"] if block.get("type") == "text"
                )
            else:
                response_content = result["content"]

        return response_content if response_content else None

    except Exception as e:
        print(f"LLM call failed: {e}")
        return None


async def run_agent_analysis(
    db: Session,
    user_input: str,
    execution: ExecutionResponse,
    update_callback
):
    """Run the multi-agent analysis workflow"""

    # Step 1: Parse the query to extract intent
    regions = fuzzy_match_region(user_input)
    metrics = extract_cable_metrics(user_input)
    manufacturer = extract_manufacturer(user_input)

    # Add parsing thought
    await update_callback(ThoughtMessage(
        id=str(uuid.uuid4()),
        timestamp=datetime.now().isoformat(),
        agent_id="noc-manager",
        agent_name="NOC Manager",
        type="thought",
        content=f"Analyzing query: '{user_input}'\n- Detected regions: {regions or 'all'}\n- Relevant metrics: {metrics or 'general'}\n- Manufacturer filter: {manufacturer or 'none'}"
    ))

    # Step 2: Get network data
    await update_callback(ThoughtMessage(
        id=str(uuid.uuid4()),
        timestamp=datetime.now().isoformat(),
        agent_id="noc-manager",
        agent_name="NOC Manager",
        type="action",
        content="Delegating to Network Data Analyst to retrieve relevant data..."
    ))

    # Simulate tool call
    await update_callback(ThoughtMessage(
        id=str(uuid.uuid4()),
        timestamp=datetime.now().isoformat(),
        agent_id="network-data-analyst",
        agent_name="Network Data Analyst",
        type="tool_call",
        content=f"Retrieving network data for regions: {regions or 'all'}",
        tool_name="Network Data Retrieval Tool",
        tool_input={"regions": regions, "metrics": metrics}
    ))

    # Get actual data from database
    network_summary = get_network_summary(db, regions, metrics)

    await update_callback(ThoughtMessage(
        id=str(uuid.uuid4()),
        timestamp=datetime.now().isoformat(),
        agent_id="network-data-analyst",
        agent_name="Network Data Analyst",
        type="tool_result",
        content=f"Retrieved data: {network_summary['nodes']['total']} nodes, {network_summary['alerts']['active']} active alerts",
        tool_name="Network Data Retrieval Tool",
    ))

    # Step 3: If looking for issues, get specific problem nodes
    issue_nodes = []
    if any(term in user_input.lower() for term in ["issue", "problem", "backhaul", "latency", "degraded", "poor"]):
        issue_type = "latency"
        if "packet" in user_input.lower():
            issue_type = "packet_loss"
        elif "throughput" in user_input.lower() or "bandwidth" in user_input.lower():
            issue_type = "throughput"
        elif "drop" in user_input.lower():
            issue_type = "packet_loss"

        await update_callback(ThoughtMessage(
            id=str(uuid.uuid4()),
            timestamp=datetime.now().isoformat(),
            agent_id="predictive-analyst",
            agent_name="Predictive Analyst",
            type="tool_call",
            content=f"Analyzing nodes with {issue_type} issues...",
            tool_name="Geographic Performance Analysis Tool",
        ))

        issue_nodes = get_nodes_with_issues(db, regions, issue_type)

        await update_callback(ThoughtMessage(
            id=str(uuid.uuid4()),
            timestamp=datetime.now().isoformat(),
            agent_id="predictive-analyst",
            agent_name="Predictive Analyst",
            type="tool_result",
            content=f"Found {len(issue_nodes)} nodes with {issue_type} issues",
            tool_name="Geographic Performance Analysis Tool",
        ))

    # Step 4: Build context and call LLM for final analysis
    await update_callback(ThoughtMessage(
        id=str(uuid.uuid4()),
        timestamp=datetime.now().isoformat(),
        agent_id="noc-manager",
        agent_name="NOC Manager",
        type="thought",
        content="Synthesizing findings and preparing comprehensive response..."
    ))

    # Build the system prompt with all context
    system_prompt = f"""You are a Network Operations Center (NOC) analyst providing detailed analysis.

USER QUERY: {user_input}

DETECTED FILTERS:
- Regions: {regions or 'All regions'}
- Metrics of interest: {metrics or 'General network health'}
- Manufacturer: {manufacturer or 'All manufacturers'}

NETWORK DATA SUMMARY:
- Total Nodes: {network_summary['nodes']['total']}
- Nodes by Region: {network_summary['nodes']['by_region']}
- Nodes by Status: {network_summary['nodes']['by_status']}
- Nodes by Manufacturer: {network_summary['nodes']['by_manufacturer']}

KPI STATISTICS:
{_format_kpi_stats(network_summary['kpis']['statistics'])}

ALERTS:
- Total Alerts: {network_summary['alerts']['total']}
- Active Alerts: {network_summary['alerts']['active']}
- By Severity: {network_summary['alerts']['by_severity']}
- By Type: {network_summary['alerts']['by_type']}

{"NODES WITH ISSUES:" if issue_nodes else ""}
{_format_issue_nodes(issue_nodes) if issue_nodes else ""}

Provide a comprehensive analysis that:
1. Directly addresses the user's question
2. Highlights key findings from the data
3. Identifies specific nodes/regions with issues
4. Provides actionable recommendations
5. Uses tables where appropriate for clarity

Format your response in markdown with clear sections."""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_input}
    ]

    response = await call_llm(db, messages)

    if response:
        final_output = response
    else:
        # Fallback response if LLM not available
        final_output = _generate_fallback_response(user_input, network_summary, issue_nodes, regions, metrics)

    # Add final answer
    await update_callback(ThoughtMessage(
        id=str(uuid.uuid4()),
        timestamp=datetime.now().isoformat(),
        agent_id="noc-manager",
        agent_name="NOC Manager",
        type="final_answer",
        content=final_output
    ))

    return final_output


def _format_kpi_stats(stats: Dict) -> str:
    """Format KPI statistics for the prompt"""
    if not stats:
        return "No KPI data available"

    lines = []
    for metric, values in stats.items():
        lines.append(f"- {metric}: avg={values['avg']}, min={values['min']}, max={values['max']}")
    return "\n".join(lines)


def _format_issue_nodes(nodes: List[Dict]) -> str:
    """Format issue nodes for the prompt"""
    if not nodes:
        return ""

    lines = ["| Node ID | Region | City | Issue | Value | Threshold |", "|---------|--------|------|-------|-------|-----------|"]
    for t in nodes[:15]:
        lines.append(f"| {t['node_id']} | {t['region']} | {t.get('city', 'N/A')} | {t['issue_metric']} | {t['issue_value']} | {t['threshold']} |")

    if len(nodes) > 15:
        lines.append(f"\n... and {len(nodes) - 15} more nodes with issues")

    return "\n".join(lines)


def _generate_fallback_response(user_input: str, summary: Dict, issue_nodes: List, regions: List, metrics: List) -> str:
    """Generate a response when LLM is not available"""
    response_parts = []

    region_str = ", ".join(regions) if regions else "all regions"
    response_parts.append(f"## Network Analysis for {region_str.upper()}\n")

    # Summary
    response_parts.append(f"### Overview")
    response_parts.append(f"- **Total Nodes Analyzed:** {summary['nodes']['total']}")
    response_parts.append(f"- **Active Alerts:** {summary['alerts']['active']}")

    # Status breakdown
    if summary['nodes']['by_status']:
        response_parts.append(f"\n### Node Status Distribution")
        for status, count in summary['nodes']['by_status'].items():
            response_parts.append(f"- {status}: {count} nodes")

    # KPI Statistics
    if summary['kpis']['statistics']:
        response_parts.append(f"\n### Key Performance Indicators")
        relevant_metrics = metrics or ["latency_ms", "downstream_throughput_mbps", "packet_loss_percent", "ds_snr_db"]
        for metric in relevant_metrics:
            if metric in summary['kpis']['statistics']:
                stats = summary['kpis']['statistics'][metric]
                response_parts.append(f"- **{metric}:** avg={stats['avg']}, range=[{stats['min']} - {stats['max']}]")

    # Issue nodes
    if issue_nodes:
        response_parts.append(f"\n### Nodes Requiring Attention")
        response_parts.append("| Node ID | Region | Issue | Value |")
        response_parts.append("|---------|--------|-------|-------|")
        for t in issue_nodes[:10]:
            response_parts.append(f"| {t['node_id']} | {t['region']} | {t['issue_metric']} | {t['issue_value']} |")

    # Recommendations
    response_parts.append(f"\n### Recommendations")
    if issue_nodes:
        response_parts.append("1. Investigate the nodes listed above with high latency/packet loss")
        response_parts.append("2. Check backhaul connectivity and capacity")
        response_parts.append("3. Review recent configuration changes in affected regions")
    else:
        response_parts.append("1. Continue monitoring KPIs for early warning signs")
        response_parts.append("2. Review capacity planning for peak usage periods")

    return "\n".join(response_parts)


# ============================================
# API Endpoints
# ============================================

@router.get("/workflows")
async def list_workflows():
    """List available workflows"""
    return {
        "workflows": [
            {
                "id": w.id,
                "name": w.name,
                "description": w.description,
                "agent_count": len(w.agents),
                "tool_count": len(w.tools),
            }
            for w in _workflows.values()
        ]
    }


@router.get("/workflows/{workflow_id}")
async def get_workflow(workflow_id: str):
    """Get workflow details"""
    if workflow_id not in _workflows:
        raise HTTPException(status_code=404, detail="Workflow not found")

    workflow = _workflows[workflow_id]
    return {
        "id": workflow.id,
        "name": workflow.name,
        "description": workflow.description,
        "is_conversational": workflow.is_conversational,
        "agents": [a.dict() for a in workflow.agents],
        "tools": [t.dict() for t in workflow.tools],
    }


@router.post("/execute")
async def execute_workflow(request: ExecuteRequest, db: Session = Depends(get_db)):
    """Execute a workflow with user input"""
    if request.workflow_id not in _workflows:
        raise HTTPException(status_code=404, detail="Workflow not found")

    execution_id = f"exec-{uuid.uuid4().hex[:12]}"

    execution = ExecutionResponse(
        execution_id=execution_id,
        status="running",
        workflow_id=request.workflow_id,
        user_input=request.user_input,
        thoughts=[],
        started_at=datetime.now().isoformat(),
    )

    _executions[execution_id] = execution

    # Run analysis in background
    async def update_execution(thought: ThoughtMessage):
        execution.thoughts.append(thought)
        if thought.type == "final_answer":
            execution.final_output = thought.content
            execution.status = "completed"
            execution.completed_at = datetime.now().isoformat()

    asyncio.create_task(run_agent_analysis(db, request.user_input, execution, update_execution))

    return {"execution_id": execution_id, "status": "running"}


@router.get("/executions/{execution_id}")
async def get_execution(execution_id: str):
    """Get execution status and results"""
    if execution_id not in _executions:
        raise HTTPException(status_code=404, detail="Execution not found")

    execution = _executions[execution_id]
    return {
        "execution_id": execution.execution_id,
        "status": execution.status,
        "workflow_id": execution.workflow_id,
        "user_input": execution.user_input,
        "thoughts": [t.dict() for t in execution.thoughts],
        "final_output": execution.final_output,
        "started_at": execution.started_at,
        "completed_at": execution.completed_at,
    }
