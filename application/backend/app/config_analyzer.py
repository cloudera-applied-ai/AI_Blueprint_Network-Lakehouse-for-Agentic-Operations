"""
Config Analyzer Module - LLM-powered configuration change impact assessment.

Follows the ai_analyzer.py pattern: LLM analysis with rule-based fallback.
"""

import json
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

from sqlalchemy.orm import Session
from sqlalchemy import select, func

from .models import (
    NetworkDeviceModel, ConfigChangeLogModel, ConfigComplianceModel,
    ChangeRequestModel, AlertModel,
)
from .ai_analyzer import get_llm_config
from .llm_queue import llm_queue


@dataclass
class ConfigAnalysisResult:
    """Result of AI analysis of a configuration change request"""
    request_id: str
    risk_level: str  # low, medium, high, critical
    impact_score: float  # 0-10
    recommendation: str  # approve, review, reject
    summary: str
    potential_impacts: List[str]
    rollback_complexity: str  # simple, moderate, complex
    reasoning: str
    raw_response: Optional[str] = None


# Risk scoring by change type and device type
CHANGE_RISK_MATRIX = {
    ("firewall", "security"): 8,
    ("firewall", "maintenance"): 5,
    ("firewall", "optimization"): 6,
    ("firewall", "compliance"): 4,
    ("switch", "security"): 6,
    ("switch", "maintenance"): 3,
    ("switch", "optimization"): 4,
    ("switch", "compliance"): 3,
    ("router", "security"): 7,
    ("router", "maintenance"): 4,
    ("router", "optimization"): 5,
    ("router", "compliance"): 3,
    ("modem", "security"): 3,
    ("modem", "maintenance"): 2,
    ("modem", "optimization"): 3,
    ("modem", "compliance"): 2,
}


def build_config_analysis_context(
    db: Session,
    change_request: ChangeRequestModel,
) -> Dict[str, Any]:
    """Build context for LLM analysis of a config change."""
    device_ids = [t["device_id"] for t in (change_request.target_devices or [])]

    # Get devices
    devices = db.query(NetworkDeviceModel).filter(
        NetworkDeviceModel.device_id.in_(device_ids)
    ).all() if device_ids else []

    # Get recent changes for these devices (last 7 days)
    recent_changes = db.query(ConfigChangeLogModel).filter(
        ConfigChangeLogModel.device_id.in_(device_ids)
    ).order_by(ConfigChangeLogModel.change_timestamp.desc()).limit(10).all() if device_ids else []

    # Get active alerts in related regions
    regions = list({d.region for d in devices if d.region})
    active_alerts = 0
    if regions:
        active_alerts = db.query(func.count(AlertModel.id)).filter(
            AlertModel.status == "ACTIVE"
        ).scalar() or 0

    return {
        "change_request": {
            "request_id": change_request.request_id,
            "title": change_request.title,
            "description": change_request.description,
            "change_type": change_request.change_type,
            "device_count": change_request.device_count,
        },
        "devices": [
            {
                "device_id": d.device_id,
                "device_type": d.device_type,
                "device_role": d.device_role,
                "hostname": d.hostname,
                "manufacturer": d.manufacturer,
                "status": d.status,
                "compliance_status": d.compliance_status,
                "region": d.region,
            }
            for d in devices
        ],
        "recent_changes_count": len(recent_changes),
        "active_alerts_in_network": active_alerts,
        "affected_regions": regions,
    }


async def analyze_config_change(
    db: Session,
    change_request: ChangeRequestModel,
) -> ConfigAnalysisResult:
    """
    LLM-powered impact assessment of a configuration change.
    Falls back to rule-based analysis if LLM is unavailable.
    """
    context = build_config_analysis_context(db, change_request)
    llm_config = get_llm_config(db)

    if llm_config and llm_config.get("endpoint_url"):
        try:
            result = await _analyze_with_llm(llm_config, context, change_request)
            if result:
                return result
        except Exception as e:
            print(f"LLM config analysis failed, falling back to rules: {e}")

    return analyze_config_change_rule_based(context, change_request)


async def _analyze_with_llm(
    llm_config: Dict,
    context: Dict,
    change_request: ChangeRequestModel,
) -> Optional[ConfigAnalysisResult]:
    """Call LLM for config change analysis."""
    system_prompt = f"""You are a network configuration change analyst. Assess the risk and impact of the proposed change.

CHANGE REQUEST:
- Title: {context['change_request']['title']}
- Type: {context['change_request']['change_type']}
- Description: {context['change_request'].get('description', 'N/A')}
- Devices affected: {context['change_request']['device_count']}

AFFECTED DEVICES:
{json.dumps(context['devices'], indent=2)}

NETWORK CONTEXT:
- Recent changes to these devices: {context['recent_changes_count']}
- Active alerts in network: {context['active_alerts_in_network']}
- Affected regions: {context['affected_regions']}

Respond with a JSON object containing:
{{
    "risk_level": "low|medium|high|critical",
    "impact_score": 0-10,
    "recommendation": "approve|review|reject",
    "summary": "Brief summary",
    "potential_impacts": ["impact1", "impact2"],
    "rollback_complexity": "simple|moderate|complex",
    "reasoning": "Detailed reasoning"
}}"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Analyze this configuration change request: {change_request.title}"},
    ]

    provider = llm_config.get("provider", "cloudera")
    api_url = llm_config["endpoint_url"]

    headers = {"Content-Type": "application/json"}
    if llm_config.get("jwt_token"):
        headers["Authorization"] = f"Bearer {llm_config['jwt_token']}"
    elif llm_config.get("api_key"):
        if provider == "anthropic":
            headers["x-api-key"] = llm_config["api_key"]
            headers["anthropic-version"] = "2023-06-01"
        else:
            headers["Authorization"] = f"Bearer {llm_config['api_key']}"

    payload = {
        "messages": messages,
        "max_tokens": llm_config.get("max_tokens", 2000),
        "temperature": llm_config.get("temperature", 0.3),
    }
    if llm_config.get("model_name"):
        payload["model"] = llm_config["model_name"]

    try:
        job_id = llm_queue.submit_and_process_parallel(
            messages=messages, provider=provider, api_url=api_url,
            headers=headers, payload=payload, priority=5,
        )
        result = llm_queue.wait_for_job(job_id, timeout=60.0)
        if not result:
            return None

        # Extract response
        content = ""
        if "choices" in result and result["choices"]:
            choice = result["choices"][0]
            content = choice.get("message", {}).get("content", "") or choice.get("text", "")
        elif "content" in result:
            if isinstance(result["content"], list):
                content = "".join(b.get("text", "") for b in result["content"] if b.get("type") == "text")
            else:
                content = result["content"]

        if not content:
            return None

        # Parse JSON from response
        import re
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            parsed = json.loads(json_match.group())
            return ConfigAnalysisResult(
                request_id=change_request.request_id,
                risk_level=parsed.get("risk_level", "medium"),
                impact_score=float(parsed.get("impact_score", 5)),
                recommendation=parsed.get("recommendation", "review"),
                summary=parsed.get("summary", "LLM analysis completed"),
                potential_impacts=parsed.get("potential_impacts", []),
                rollback_complexity=parsed.get("rollback_complexity", "moderate"),
                reasoning=parsed.get("reasoning", content),
                raw_response=content,
            )
    except Exception as e:
        print(f"LLM config analysis error: {e}")

    return None


def analyze_config_change_rule_based(
    context: Dict,
    change_request: ChangeRequestModel,
) -> ConfigAnalysisResult:
    """Rule-based fallback when LLM is unavailable."""
    devices = context.get("devices", [])
    change_type = change_request.change_type or "maintenance"

    # Calculate base risk from device types and change type
    risk_scores = []
    for dev in devices:
        key = (dev.get("device_type", ""), change_type)
        score = CHANGE_RISK_MATRIX.get(key, 5)
        # Boost risk if device is degraded or has drift
        if dev.get("status") == "degraded":
            score += 2
        if dev.get("compliance_status") == "drifted":
            score += 1
        risk_scores.append(score)

    avg_score = sum(risk_scores) / len(risk_scores) if risk_scores else 5
    # Scale by number of devices
    if len(devices) > 5:
        avg_score = min(10, avg_score + 1)
    if len(devices) > 20:
        avg_score = min(10, avg_score + 1)

    # Boost risk if there are active alerts
    if context.get("active_alerts_in_network", 0) > 10:
        avg_score = min(10, avg_score + 1)

    # Map score to risk level
    if avg_score <= 3:
        risk_level = "low"
        recommendation = "approve"
    elif avg_score <= 5:
        risk_level = "medium"
        recommendation = "approve"
    elif avg_score <= 7:
        risk_level = "high"
        recommendation = "review"
    else:
        risk_level = "critical"
        recommendation = "review"

    device_types = list({d.get("device_type", "unknown") for d in devices})
    impacts = []
    if "firewall" in device_types:
        impacts.append("Potential connectivity disruption during firewall rule update")
    if "switch" in device_types:
        impacts.append("VLAN changes may cause brief network partition")
    if "router" in device_types:
        impacts.append("Routing protocol reconvergence expected")
    if "modem" in device_types:
        impacts.append("Customer-facing modems may experience brief reconnection")

    return ConfigAnalysisResult(
        request_id=change_request.request_id,
        risk_level=risk_level,
        impact_score=round(avg_score, 1),
        recommendation=recommendation,
        summary=f"Rule-based analysis: {risk_level} risk {change_type} change affecting {len(devices)} {', '.join(device_types)} device(s)",
        potential_impacts=impacts,
        rollback_complexity="simple" if len(devices) <= 3 else "moderate" if len(devices) <= 10 else "complex",
        reasoning=f"Risk score {round(avg_score, 1)}/10 based on device types ({', '.join(device_types)}), "
                  f"change type ({change_type}), {context.get('active_alerts_in_network', 0)} active alerts, "
                  f"and {context.get('recent_changes_count', 0)} recent changes.",
    )
