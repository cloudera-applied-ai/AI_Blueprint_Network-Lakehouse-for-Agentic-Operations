"""
AI Analyzer Module - LLM-powered alert analysis for autonomous cable network healing.

This module provides LLM-based analysis of individual alerts to determine:
- Root cause of issues
- Recommended actions
- Whether to execute autonomously
- Urgency scoring

Ported from src/services/aiAgentService.ts analyzeAlert()
"""

import json
import re
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field

from sqlalchemy.orm import Session
from sqlalchemy import select, func

from .models import FiberNodeModel, KPIMetricsModel, AlertModel, SelfHealingActionModel, LLMConfigModel
from .sensor_generator import (
    generate_equipment_sensor_data,
    generate_rf_plant_sensor_data,
    generate_environmental_sensor,
    generate_all_sensor_data,
)
from .llm_queue import llm_queue


@dataclass
class AgentAnalysis:
    """Result of AI analysis of an alert"""
    alert_id: str
    node_id: str
    summary: str
    root_cause: str
    recommendations: List[str]
    confidence: float
    reasoning: str
    should_execute_autonomously: bool
    urgency_score: int  # 1-10
    sensor_data_used: Dict[str, Any]
    raw_response: Optional[str] = None
    analysis_time_ms: int = 0


# Action type mapping for autonomous execution decisions
AUTONOMOUS_ACTION_TYPES = {
    "MODEM_REMOTE_REBOOT": {"autonomous": True, "risk": "low"},
    "FIRMWARE_PUSH": {"autonomous": True, "risk": "medium"},
    "PROVISIONING_REFRESH": {"autonomous": True, "risk": "low"},
    "CMTS_PORT_RESET": {"autonomous": True, "risk": "medium"},
    "SIGNAL_LEVEL_ADJUSTMENT": {"autonomous": True, "risk": "low"},
    "TRAFFIC_REROUTE": {"autonomous": True, "risk": "low"},
    "NODE_CAPACITY_REBALANCE": {"autonomous": True, "risk": "low"},
    "TICKET_CREATION": {"autonomous": True, "risk": "low"},
    "EQUIPMENT_REPLACEMENT": {"autonomous": False, "risk": "high"},  # Field work required
    "CREW_DISPATCH": {"autonomous": False, "risk": "medium"},
}

# Alert severity to urgency mapping
SEVERITY_URGENCY = {
    "critical": 9,
    "warning": 6,
    "info": 3,
}


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


def build_analysis_context(
    db: Session,
    alert: AlertModel,
    node: FiberNodeModel,
) -> Dict[str, Any]:
    """
    Build comprehensive context for LLM analysis.

    Includes:
    - Alert details
    - Fiber node configuration
    - Recent KPIs (last hour)
    - Recent alerts on same node
    - Recent actions on same node
    - Sensor data
    """
    now = datetime.utcnow()
    one_hour_ago = now - timedelta(hours=1)
    one_day_ago = now - timedelta(days=1)

    # Get recent KPIs
    kpi_query = select(KPIMetricsModel).where(
        KPIMetricsModel.node_id == node.node_id,
        KPIMetricsModel.timestamp >= one_hour_ago
    ).order_by(KPIMetricsModel.timestamp.desc()).limit(12)
    kpis = db.execute(kpi_query).scalars().all()

    # Calculate KPI trends (cable RF metrics)
    kpi_summary = {}
    if kpis:
        kpi_summary = {
            "avg_ds_snr_db": sum(getattr(k, 'ds_snr_db', 38) or 38 for k in kpis) / len(kpis),
            "avg_us_snr_db": sum(getattr(k, 'us_snr_db', 25) or 25 for k in kpis) / len(kpis),
            "avg_ds_power_level_dbmv": sum(getattr(k, 'ds_power_level_dbmv', 0) or 0 for k in kpis) / len(kpis),
            "avg_us_power_level_dbmv": sum(getattr(k, 'us_power_level_dbmv', 40) or 40 for k in kpis) / len(kpis),
            "avg_latency_ms": sum(getattr(k, 'latency_ms', 15) or 15 for k in kpis) / len(kpis),
            "avg_packet_loss_percent": sum(getattr(k, 'packet_loss_percent', 0) or 0 for k in kpis) / len(kpis),
            "avg_downstream_throughput_mbps": sum(getattr(k, 'downstream_throughput_mbps', 800) or 800 for k in kpis) / len(kpis),
            "avg_upstream_throughput_mbps": sum(getattr(k, 'upstream_throughput_mbps', 35) or 35 for k in kpis) / len(kpis),
            "avg_fec_uncorrected": sum(getattr(k, 'fec_uncorrected_codewords', 0) or 0 for k in kpis) / len(kpis),
            "avg_t3_timeouts": sum(getattr(k, 't3_timeouts', 0) or 0 for k in kpis) / len(kpis),
            "avg_node_temperature": sum(getattr(k, 'node_temperature', 35) or 35 for k in kpis) / len(kpis),
            "avg_node_cpu": sum(getattr(k, 'node_cpu_utilization', 40) or 40 for k in kpis) / len(kpis),
            "sample_count": len(kpis),
        }

    # Get recent alerts on this node
    recent_alerts_query = select(AlertModel).where(
        AlertModel.node_id == node.node_id,
        AlertModel.timestamp >= one_day_ago,
        AlertModel.alert_id != alert.alert_id
    ).order_by(AlertModel.timestamp.desc()).limit(5)
    recent_alerts = db.execute(recent_alerts_query).scalars().all()

    # Get recent actions on this node
    recent_actions_query = select(SelfHealingActionModel).where(
        SelfHealingActionModel.node_id == node.node_id,
        SelfHealingActionModel.start_time >= one_day_ago
    ).order_by(SelfHealingActionModel.start_time.desc()).limit(5)
    recent_actions = db.execute(recent_actions_query).scalars().all()

    # Generate sensor data - convert node model to dict for sensor generator
    node_dict = {
        "node_id": node.node_id,
        "status": node.status,
        "latitude": node.latitude,
        "longitude": node.longitude,
        "region": node.region,
        "service_area": getattr(node, 'service_area', None),
        "manufacturer": node.manufacturer,
        "hardware_model": node.hardware_model,
        "node_type": getattr(node, 'node_type', 'N+0'),
        "docsis_version": getattr(node, 'docsis_version', '3.1'),
    }
    sensor_data = generate_all_sensor_data(node_dict)

    return {
        "alert": {
            "id": alert.alert_id,
            "type": alert.type,
            "severity": alert.severity,
            "title": alert.title,
            "description": alert.description,
            "timestamp": alert.timestamp.isoformat() if alert.timestamp else now.isoformat(),
            "affected_customers": getattr(alert, 'affected_customers', None),
            "affected_modems": getattr(alert, 'affected_modems', None),
        },
        "node": {
            "id": node.node_id,
            "headend_id": getattr(node, 'headend_id', None),
            "hub_id": getattr(node, 'hub_id', None),
            "city": node.city,
            "region": node.region,
            "service_area": getattr(node, 'service_area', None),
            "status": node.status,
            "sla_tier": "Critical" if (getattr(node, 'homes_active', 0) or 0) > 2000 else "Standard",
            "node_type": getattr(node, 'node_type', 'N+0'),
            "docsis_version": getattr(node, 'docsis_version', '3.1'),
            "manufacturer": node.manufacturer,
            "hardware_model": node.hardware_model,
            "firmware_version": node.firmware_version,
            "homes_passed": getattr(node, 'homes_passed', None),
            "homes_active": getattr(node, 'homes_active', None),
            "amplifier_cascade": getattr(node, 'amplifier_cascade', None),
            "coax_plant_miles": getattr(node, 'coax_plant_miles', None),
            "last_maintenance": getattr(node, 'last_maintenance', None),
            "commissioned_date": getattr(node, 'commissioned_date', None),
        },
        "kpi_summary": kpi_summary,
        "recent_alerts": [
            {
                "type": a.type,
                "severity": a.severity,
                "description": a.description[:100],
                "status": a.status,
                "timestamp": a.timestamp.isoformat() if a.timestamp else None,
            }
            for a in recent_alerts
        ],
        "recent_actions": [
            {
                "type": a.action_type,
                "status": a.status,
                "effectiveness": a.effectiveness_score,
                "description": a.description[:100] if a.description else None,
            }
            for a in recent_actions
        ],
        "sensor_data": {
            "equipment": sensor_data.get("equipment", {}),
            "rf_plant": sensor_data.get("rf_plant", {}),
            "environmental": sensor_data.get("environmental", {}),
        },
    }


def build_analysis_prompt(context: Dict[str, Any]) -> List[Dict[str, str]]:
    """Build the LLM prompt for alert analysis"""
    alert = context["alert"]
    node = context["node"]
    kpi_summary = context.get("kpi_summary", {})
    recent_alerts = context.get("recent_alerts", [])
    recent_actions = context.get("recent_actions", [])
    sensor_data = context.get("sensor_data", {})

    system_prompt = """You are an expert cable network (HFC plant) engineer AI assistant specialized in self-healing DOCSIS networks. Your role is to analyze network alerts and provide actionable recommendations for a cable ISP (like Charter/Spectrum).

You must respond with a valid JSON object containing:
{
    "summary": "Brief 1-2 sentence summary of the issue",
    "root_cause": "Detailed explanation of the probable root cause",
    "recommendations": ["Array of specific action recommendations"],
    "confidence": 0.0-1.0,
    "reasoning": "Your reasoning process",
    "should_execute_autonomously": true/false,
    "urgency_score": 1-10,
    "recommended_action_type": "MODEM_REMOTE_REBOOT|FIRMWARE_PUSH|PROVISIONING_REFRESH|CMTS_PORT_RESET|SIGNAL_LEVEL_ADJUSTMENT|TRAFFIC_REROUTE|NODE_CAPACITY_REBALANCE|TICKET_CREATION"
}

Guidelines for autonomous execution:
- ONLY recommend autonomous=true for low-risk, reversible actions
- NEVER recommend autonomous for actions requiring physical plant access
- Consider SLA tier - Critical SLA needs more careful consideration
- Consider customer impact count and time of day

Action types and risk levels:
- MODEM_REMOTE_REBOOT: Low risk, can be automated
- FIRMWARE_PUSH: Medium risk, may cause brief service interruption
- PROVISIONING_REFRESH: Low risk, can be automated
- CMTS_PORT_RESET: Medium risk, affects multiple modems - automate only for critical issues
- SIGNAL_LEVEL_ADJUSTMENT: Low risk, can be automated
- TRAFFIC_REROUTE: Low risk, can be automated
- NODE_CAPACITY_REBALANCE: Low risk, can be automated
- TICKET_CREATION: Low risk, always safe to automate"""

    # Build detailed alert context
    alert_context = f"""
ALERT INFORMATION:
- Type: {alert['type']}
- Severity: {alert['severity']}
- Title: {alert['title']}
- Description: {alert['description']}
- Affected Customers: {alert.get('affected_customers', 'N/A')}
- Affected Modems: {alert.get('affected_modems', 'N/A')}
- Timestamp: {alert['timestamp']}

FIBER NODE INFORMATION:
- Node ID: {node['id']}
- Headend: {node.get('headend_id', 'N/A')}
- Hub: {node.get('hub_id', 'N/A')}
- Location: {node['city']}, {node['region']}
- Service Area: {node.get('service_area', 'N/A')}
- Status: {node['status']}
- SLA Tier: {node['sla_tier']}
- Node Type: {node.get('node_type', 'N/A')} (amplifier cascade depth)
- DOCSIS Version: {node.get('docsis_version', 'N/A')}
- Manufacturer: {node['manufacturer']} - {node['hardware_model']}
- Firmware: {node['firmware_version']}
- Homes Passed: {node.get('homes_passed', 'N/A')}
- Homes Active: {node.get('homes_active', 'N/A')}
- Amplifier Cascade: {node.get('amplifier_cascade', 'N/A')}
- Coax Plant Miles: {node.get('coax_plant_miles', 'N/A')}
- Last Maintenance: {node.get('last_maintenance') or 'Unknown'}
"""

    if kpi_summary:
        alert_context += f"""
RECENT RF METRICS (Last Hour Average):
IMPORTANT - Cable RF Metric interpretation:
  - DS SNR: Higher is better (>35 dB good, <30 dB problem)
  - US SNR: Higher is better (>25 dB good, <20 dB problem)
  - DS Power: Should be -7 to +7 dBmV (out of range = problem)
  - US Power: Should be 35-51 dBmV (out of range = problem)
  - FEC Uncorrected: LOWER is better (0 ideal, >100 serious)
  - T3 Timeouts: LOWER is better (0 ideal, >50 serious)
  - Latency: LOWER is better
  - Packet Loss: LOWER is better

- DS SNR: {kpi_summary.get('avg_ds_snr_db', 'N/A'):.1f} dB
- US SNR: {kpi_summary.get('avg_us_snr_db', 'N/A'):.1f} dB
- DS Power Level: {kpi_summary.get('avg_ds_power_level_dbmv', 'N/A'):.1f} dBmV
- US Power Level: {kpi_summary.get('avg_us_power_level_dbmv', 'N/A'):.1f} dBmV
- Downstream Throughput: {kpi_summary.get('avg_downstream_throughput_mbps', 'N/A'):.1f} Mbps
- Upstream Throughput: {kpi_summary.get('avg_upstream_throughput_mbps', 'N/A'):.1f} Mbps
- Latency: {kpi_summary.get('avg_latency_ms', 'N/A'):.1f} ms
- Packet Loss: {kpi_summary.get('avg_packet_loss_percent', 'N/A'):.2f}%
- FEC Uncorrected Codewords: {kpi_summary.get('avg_fec_uncorrected', 'N/A'):.0f}
- T3 Timeouts: {kpi_summary.get('avg_t3_timeouts', 'N/A'):.0f}
- Node Temperature: {kpi_summary.get('avg_node_temperature', 'N/A'):.1f}C
- Node CPU: {kpi_summary.get('avg_node_cpu', 'N/A'):.1f}%
"""

    if recent_alerts:
        alert_context += "\nRECENT ALERTS ON THIS NODE (Last 24h):\n"
        for i, a in enumerate(recent_alerts, 1):
            alert_context += f"  {i}. {a['type']} ({a['severity']}): {a['description']} - Status: {a['status']}\n"

    if recent_actions:
        alert_context += "\nRECENT AUTO-RESOLUTION ACTIONS:\n"
        for i, a in enumerate(recent_actions, 1):
            eff = f"{a['effectiveness']:.0f}%" if a['effectiveness'] else "N/A"
            alert_context += f"  {i}. {a['type']} - {a['status']} (Effectiveness: {eff})\n"

    # Add sensor data summary
    if sensor_data:
        equipment = sensor_data.get("equipment", {})
        rf_plant = sensor_data.get("rf_plant", {})
        environmental = sensor_data.get("environmental", {})

        if equipment:
            components = equipment.get("component_health", [])
            degraded = [c for c in components if c.get("status") in ("degraded", "critical", "failed")]
            if degraded:
                alert_context += "\nEQUIPMENT HEALTH ISSUES:\n"
                for c in degraded[:5]:
                    alert_context += f"  - {c.get('component_name')}: {c.get('status')} ({c.get('health_score', 0):.0f}% health)\n"

        if rf_plant:
            ds_snr = rf_plant.get("ds_snr_db", 0)
            us_snr = rf_plant.get("us_snr_db", 0)
            if ds_snr < 33 or us_snr < 22:
                alert_context += f"\nRF PLANT ISSUE: DS SNR {ds_snr:.1f} dB, US SNR {us_snr:.1f} dB (degraded signal quality)\n"
            fec_uncorrected = rf_plant.get("fec_uncorrected_codewords", 0)
            if fec_uncorrected > 50:
                alert_context += f"FEC ERRORS: {fec_uncorrected} uncorrected codewords (noise ingress likely)\n"

        if environmental:
            if environmental.get("cabinet_temperature", 0) > 45:
                alert_context += f"\nENVIRONMENTAL ALERT: Node temperature {environmental.get('cabinet_temperature', 0):.1f}C (elevated)\n"
            if environmental.get("rf_ingress_detected", False):
                alert_context += f"RF INGRESS: Ingress detected at node ({environmental.get('ingress_level_dbmv', 'N/A')} dBmV)\n"

    alert_context += "\nPlease analyze this alert and provide your recommendations in the specified JSON format."

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": alert_context},
    ]


def parse_analysis_response(response_content: str, alert_id: str, node_id: str) -> AgentAnalysis:
    """Parse the LLM response into an AgentAnalysis object"""

    # Try to extract JSON from the response
    try:
        # Try direct JSON parse first
        data = json.loads(response_content)
    except json.JSONDecodeError:
        # Try to find JSON block in response
        json_match = re.search(r'\{[\s\S]*\}', response_content)
        if json_match:
            try:
                data = json.loads(json_match.group())
            except json.JSONDecodeError:
                # Fall back to default analysis
                data = None
        else:
            data = None

    if not data:
        # Return fallback analysis
        return AgentAnalysis(
            alert_id=alert_id,
            node_id=node_id,
            summary="Unable to parse LLM response. Manual review recommended.",
            root_cause="Analysis parsing failed. The alert requires manual investigation.",
            recommendations=["Review alert manually", "Check fiber node status", "Investigate RF sensor data"],
            confidence=0.3,
            reasoning="LLM response could not be parsed as valid JSON.",
            should_execute_autonomously=False,
            urgency_score=5,
            sensor_data_used={},
            raw_response=response_content,
        )

    # Extract fields with defaults
    return AgentAnalysis(
        alert_id=alert_id,
        node_id=node_id,
        summary=data.get("summary", "No summary provided"),
        root_cause=data.get("root_cause", "Root cause not determined"),
        recommendations=data.get("recommendations", ["Manual review required"]),
        confidence=float(data.get("confidence", 0.5)),
        reasoning=data.get("reasoning", "No reasoning provided"),
        should_execute_autonomously=bool(data.get("should_execute_autonomously", False)),
        urgency_score=int(data.get("urgency_score", 5)),
        sensor_data_used={},
        raw_response=response_content,
    )


async def analyze_alert_with_llm(
    db: Session,
    alert_id: str,
    timeout_seconds: float = 90.0,
) -> Optional[AgentAnalysis]:
    """
    Analyze an alert using the configured LLM.

    This is the main entry point for LLM-based alert analysis.
    Called automatically by the background task when new alerts are generated.

    Args:
        db: Database session
        alert_id: ID of the alert to analyze
        timeout_seconds: Maximum time to wait for LLM response

    Returns:
        AgentAnalysis object or None if analysis failed
    """
    import time
    start_time = time.time()

    # Get LLM config
    llm_config = get_llm_config(db)
    if not llm_config:
        print(f"❌ LLM not configured or disabled - skipping analysis for alert {alert_id[:8]}")
        return None

    # Get the alert
    alert_query = select(AlertModel).where(AlertModel.alert_id == alert_id)
    alert = db.execute(alert_query).scalar_one_or_none()
    if not alert:
        print(f"❌ Alert {alert_id} not found")
        return None

    # Get the fiber node
    node_query = select(FiberNodeModel).where(FiberNodeModel.node_id == alert.node_id)
    node = db.execute(node_query).scalar_one_or_none()
    if not node:
        print(f"❌ Fiber node {alert.node_id} not found for alert {alert_id}")
        return None

    print(f"🔍 Analyzing alert {alert_id[:8]} on node {node.node_id}")

    # Build context and prompt
    context = build_analysis_context(db, alert, node)
    messages = build_analysis_prompt(context)

    # Build API request
    provider = llm_config["provider"]
    api_url = llm_config["endpoint_url"]

    # Add /v1/chat/completions suffix for OpenAI-compatible endpoints
    if provider in ['ollama', 'cloudera', 'custom']:
        if not api_url.endswith('/chat/completions'):
            if api_url.endswith('/v1'):
                api_url = f"{api_url}/chat/completions"
            elif '/v1' not in api_url:
                api_url = f"{api_url}/v1/chat/completions"
            else:
                api_url = f"{api_url}/chat/completions"

    headers = {"Content-Type": "application/json"}

    # Add authentication
    if llm_config.get("api_key"):
        headers["Authorization"] = f"Bearer {llm_config['api_key']}"
    elif llm_config.get("jwt_token"):
        headers["Authorization"] = f"Bearer {llm_config['jwt_token']}"

    # Build payload based on provider
    payload = {
        "messages": messages,
        "temperature": llm_config.get("temperature", 0.7),
        "max_tokens": llm_config.get("max_tokens", 2000),
    }

    if llm_config.get("model_name"):
        payload["model"] = llm_config["model_name"]

    # Submit job to LLM queue with priority 5 (automated analysis)
    try:
        job_id = llm_queue.submit_and_process_parallel(
            messages=messages,
            provider=provider,
            api_url=api_url,
            headers=headers,
            payload=payload,
            priority=5,  # Automated analysis priority
        )

        # Wait for result
        result = llm_queue.wait_for_job(job_id, timeout=timeout_seconds)

        if result is None:
            print(f"❌ LLM analysis timeout for alert {alert_id[:8]}")
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
            response_content = result["content"]

        if not response_content:
            print(f"❌ Empty LLM response for alert {alert_id[:8]}")
            return None

        # Parse response
        analysis = parse_analysis_response(response_content, alert_id, node.node_id)
        analysis.sensor_data_used = {
            "equipment": bool(context["sensor_data"].get("equipment")),
            "rf_plant": bool(context["sensor_data"].get("rf_plant")),
            "environmental": bool(context["sensor_data"].get("environmental")),
        }
        analysis.analysis_time_ms = int((time.time() - start_time) * 1000)

        print(f"✅ Analysis complete for {alert_id[:8]}: confidence={analysis.confidence:.2f}, autonomous={analysis.should_execute_autonomously}, urgency={analysis.urgency_score}")

        return analysis

    except Exception as e:
        print(f"❌ LLM analysis error for alert {alert_id[:8]}: {e}")
        import traceback
        traceback.print_exc()
        return None


def analyze_alert_rule_based(
    db: Session,
    alert_id: str,
) -> AgentAnalysis:
    """
    Fallback rule-based analysis when LLM is not available.

    Uses simple heuristics based on alert type and severity for cable network alerts.
    """
    # Get the alert
    alert_query = select(AlertModel).where(AlertModel.alert_id == alert_id)
    alert = db.execute(alert_query).scalar_one_or_none()
    if not alert:
        return None

    # Get the fiber node
    node_query = select(FiberNodeModel).where(FiberNodeModel.node_id == alert.node_id)
    node = db.execute(node_query).scalar_one_or_none()
    if not node:
        return None

    # Rule-based analysis for cable network alerts
    alert_type = alert.type.upper()
    severity = alert.severity.lower()

    # Default recommendations based on cable alert type
    action_map = {
        "NODE_OUTAGE": ("TICKET_CREATION", ["Dispatch field crew to node", "Check power supply status", "Verify fiber uplink connectivity"], "Fiber node is completely non-functional"),
        "CMTS_CARD_FAILURE": ("TICKET_CREATION", ["Check CMTS card status", "Failover to redundant card if available", "Dispatch headend technician"], "CMTS line card failure detected"),
        "HIGH_NOISE_INGRESS": ("SIGNAL_LEVEL_ADJUSTMENT", ["Identify ingress source location", "Check tap faceplate and connectors", "Adjust upstream levels if needed"], "Noise ingress detected on upstream path"),
        "POWER_SUPPLY_FAILURE": ("TICKET_CREATION", ["Check battery backup status", "Dispatch field crew for power supply replacement", "Verify utility power"], "Node power supply failure"),
        "AMPLIFIER_FAILURE": ("TICKET_CREATION", ["Identify failed amplifier in cascade", "Dispatch line technician", "Check for power supply issues"], "Amplifier failure in coax plant"),
        "UPSTREAM_CONGESTION": ("NODE_CAPACITY_REBALANCE", ["Rebalance upstream traffic across CMTS ports", "Consider node split", "Monitor utilization trends"], "Upstream channel utilization exceeded threshold"),
        "DOWNSTREAM_CONGESTION": ("TRAFFIC_REROUTE", ["Redistribute downstream load", "Enable OFDM channels if available", "Plan capacity upgrade"], "Downstream capacity threshold exceeded"),
        "PLANT_DAMAGE": ("TICKET_CREATION", ["Dispatch emergency repair crew", "Assess extent of damage", "Notify affected customers"], "Physical plant damage detected"),
        "CPE_MASS_OFFLINE": ("MODEM_REMOTE_REBOOT", ["Attempt mass modem reboot", "Check node upstream for issues", "Verify CMTS connectivity"], "Multiple customer modems went offline simultaneously"),
        "SIGNAL_DEGRADATION": ("SIGNAL_LEVEL_ADJUSTMENT", ["Check connector tightness", "Verify amplifier output levels", "Test for water ingress in plant"], "RF signal quality degradation"),
        "TEMPERATURE_ALARM": ("TICKET_CREATION", ["Check cooling systems", "Reduce power output if safe", "Dispatch field crew"], "Equipment overheating detected"),
        "CAPACITY_THRESHOLD": ("NODE_CAPACITY_REBALANCE", ["Rebalance subscriber load", "Plan node split", "Upgrade DOCSIS version"], "Node approaching capacity limits"),
        "FIRMWARE_ISSUE": ("FIRMWARE_PUSH", ["Push updated firmware", "Verify compatibility", "Monitor after update"], "Firmware issue detected on equipment"),
        "RANGING_FAILURE": ("PROVISIONING_REFRESH", ["Refresh modem provisioning", "Check signal levels", "Verify CMTS port assignment"], "Modem ranging failures detected"),
        "MAINTENANCE_OVERRUN": ("TICKET_CREATION", ["Escalate to maintenance supervisor", "Assess remaining work", "Update customer notifications"], "Maintenance window exceeded scheduled time"),
        "GATING_FAILURE": ("TICKET_CREATION", ["Review failed gating signal", "Re-evaluate maintenance window", "Check gate threshold settings"], "Maintenance gating check failed"),
    }

    action_type, recommendations, root_cause = action_map.get(
        alert_type,
        ("TICKET_CREATION", ["Investigate manually", "Check related systems", "Monitor for recurrence"], "Unknown issue type")
    )

    # Determine autonomous execution
    action_info = AUTONOMOUS_ACTION_TYPES.get(action_type, {"autonomous": False, "risk": "high"})
    should_auto = action_info["autonomous"]

    # Derive SLA criticality from homes_active (high subscriber nodes are critical)
    homes_active = getattr(node, 'homes_active', 0) or 0
    is_critical = homes_active > 2000

    # Don't auto-execute for critical nodes unless low risk
    if is_critical and action_info["risk"] != "low":
        should_auto = False

    # Calculate urgency
    urgency = SEVERITY_URGENCY.get(severity, 5)
    if is_critical:
        urgency = min(10, urgency + 2)
    affected_customers = getattr(alert, 'affected_customers', None)
    if affected_customers and affected_customers > 500:
        urgency = min(10, urgency + 1)

    sla_label = "Critical" if is_critical else "Standard"

    return AgentAnalysis(
        alert_id=alert_id,
        node_id=node.node_id,
        summary=f"{alert_type.replace('_', ' ').title()} detected on fiber node {node.node_id}",
        root_cause=root_cause,
        recommendations=recommendations,
        confidence=0.7,  # Rule-based analysis has moderate confidence
        reasoning=f"Rule-based analysis for {alert_type} alert with {severity} severity on {sla_label} SLA fiber node.",
        should_execute_autonomously=should_auto,
        urgency_score=urgency,
        sensor_data_used={},
    )


async def analyze_new_alert(db: Session, alert_id: str) -> Optional[AgentAnalysis]:
    """
    Main entry point for analyzing a newly generated alert.

    Attempts LLM analysis first, falls back to rule-based if LLM unavailable.
    """
    # Try LLM analysis first
    llm_config = get_llm_config(db)

    if llm_config:
        analysis = await analyze_alert_with_llm(db, alert_id)
        if analysis:
            return analysis
        # Fall through to rule-based if LLM failed

    # Fall back to rule-based analysis
    print(f"📋 Using rule-based analysis for alert {alert_id[:8]}")
    return analyze_alert_rule_based(db, alert_id)
