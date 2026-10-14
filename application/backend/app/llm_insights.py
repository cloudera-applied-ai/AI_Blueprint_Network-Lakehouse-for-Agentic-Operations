"""
LLM Insights Service - Configurable LLM-powered periodic deep analysis.

This module provides LLM-based analysis capabilities that work alongside the
rule-based ai_insights.py module. It supports multiple inference providers:
- Claude API (Anthropic)
- OpenAI API
- Ollama (local)
- Custom endpoints (Cloudera AI, etc.)

The LLM analysis is designed for periodic deep analysis (daily/weekly) rather
than real-time insights, to minimize latency and API costs.
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum

from sqlalchemy.orm import Session

from .models import LLMConfigModel
from .net import ssl_context
from .historical_analytics import (
    get_kpi_trends,
    get_historical_kpi_averages,
    calculate_period_comparison,
    get_historical_revenue_loss,
    get_incident_statistics,
    get_historical_alert_patterns,
)

logger = logging.getLogger(__name__)


class LLMProvider(str, Enum):
    """Supported LLM providers"""
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    OLLAMA = "ollama"
    CLOUDERA = "cloudera"
    CUSTOM = "custom"


@dataclass
class LLMInsight:
    """LLM-generated insight"""
    id: str
    timestamp: datetime
    insight_type: str
    severity: str
    title: str
    analysis: str
    recommendations: List[str]
    confidence: float
    data_sources: List[str]
    model_used: str


def get_llm_config(db: Session) -> Optional[Dict[str, Any]]:
    """Get LLM configuration from database."""
    config = db.query(LLMConfigModel).filter(LLMConfigModel.config_key == "default").first()
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


async def call_anthropic_api(
    prompt: str,
    api_key: str,
    model: str,
    max_tokens: int = 2000,
    temperature: float = 0.7
) -> str:
    """Call Anthropic Claude API."""
    import httpx

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=60.0,
        )
        response.raise_for_status()
        data = response.json()
        return data["content"][0]["text"]


async def call_openai_api(
    prompt: str,
    api_key: str,
    model: str,
    max_tokens: int = 2000,
    temperature: float = 0.7
) -> str:
    """Call OpenAI API."""
    import httpx

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=60.0,
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]


async def call_ollama_api(
    prompt: str,
    endpoint_url: str,
    model: str,
    max_tokens: int = 2000,
    temperature: float = 0.7
) -> str:
    """Call Ollama local API."""
    import httpx

    async with httpx.AsyncClient(verify=ssl_context()) as client:
        response = await client.post(
            f"{endpoint_url}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "num_predict": max_tokens,
                    "temperature": temperature,
                },
            },
            timeout=120.0,  # Local models can be slower
        )
        response.raise_for_status()
        data = response.json()
        return data["response"]


async def call_custom_api(
    prompt: str,
    endpoint_url: str,
    api_key: Optional[str] = None,
    jwt_token: Optional[str] = None,
    model: Optional[str] = None,
    max_tokens: int = 2000,
    temperature: float = 0.7
) -> str:
    """Call custom LLM endpoint (e.g., Cloudera AI)."""
    import httpx

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    elif jwt_token:
        headers["Authorization"] = f"Bearer {jwt_token}"

    payload = {
        "prompt": prompt,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    if model:
        payload["model"] = model

    async with httpx.AsyncClient(verify=ssl_context()) as client:
        response = await client.post(
            endpoint_url,
            headers=headers,
            json=payload,
            timeout=120.0,
        )
        response.raise_for_status()
        data = response.json()
        # Try common response formats
        if "content" in data:
            return data["content"]
        elif "text" in data:
            return data["text"]
        elif "response" in data:
            return data["response"]
        elif "choices" in data and data["choices"]:
            return data["choices"][0].get("text", data["choices"][0].get("message", {}).get("content", ""))
        return str(data)


def _require_model(config: Dict[str, Any]) -> str:
    """Model names are configured in Settings -> AI; never substitute a default."""
    model = (config.get("model_name") or "").strip()
    if not model:
        raise ValueError("No model name configured - set Model Name in Settings -> AI")
    return model


async def call_llm(
    prompt: str,
    config: Dict[str, Any]
) -> str:
    """
    Call the configured LLM provider.
    """
    provider = config.get("provider", "").lower()

    try:
        if provider == LLMProvider.ANTHROPIC.value:
            return await call_anthropic_api(
                prompt,
                api_key=config.get("api_key", ""),
                model=_require_model(config),
                max_tokens=config.get("max_tokens", 2000),
                temperature=config.get("temperature", 0.7),
            )
        elif provider == LLMProvider.OPENAI.value:
            return await call_openai_api(
                prompt,
                api_key=config.get("api_key", ""),
                model=_require_model(config),
                max_tokens=config.get("max_tokens", 2000),
                temperature=config.get("temperature", 0.7),
            )
        elif provider == LLMProvider.OLLAMA.value:
            return await call_ollama_api(
                prompt,
                endpoint_url=config.get("endpoint_url") or "",
                model=_require_model(config),
                max_tokens=config.get("max_tokens", 2000),
                temperature=config.get("temperature", 0.7),
            )
        elif provider in (LLMProvider.CLOUDERA.value, LLMProvider.CUSTOM.value):
            return await call_custom_api(
                prompt,
                endpoint_url=config.get("endpoint_url", ""),
                api_key=config.get("api_key"),
                jwt_token=config.get("jwt_token"),
                model=config.get("model_name"),
                max_tokens=config.get("max_tokens", 2000),
                temperature=config.get("temperature", 0.7),
            )
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")
    except Exception as e:
        logger.error(f"LLM API call failed: {e}")
        raise


def build_executive_summary_prompt(
    kpi_trends: List[Dict[str, Any]],
    kpi_averages: Dict[str, float],
    period_comparison: List[Dict[str, Any]],
    revenue_loss: Dict[str, float],
    incident_stats: Dict[str, Any],
    alert_patterns: Dict[str, Any],
    period_hours: int
) -> str:
    """Build a prompt for LLM-based executive summary generation."""

    period_desc = f"{period_hours} hours" if period_hours <= 24 else f"{period_hours // 24} days"

    prompt = f"""You are a cable network (HFC plant) operations analyst for a major ISP. Analyze the following network performance data from the past {period_desc} and provide an executive summary.

## Network KPI Averages (Cable RF Metrics)
{json.dumps(kpi_averages, indent=2)}

## Period-over-Period Comparison (vs Previous {period_desc})
{json.dumps(period_comparison, indent=2)}

## Financial Impact
{json.dumps(revenue_loss, indent=2)}

## Incident Statistics
{json.dumps(incident_stats, indent=2)}

## Alert Patterns
- Total Alerts: {alert_patterns.get('total_alerts', 0)}
- By Severity: {json.dumps(alert_patterns.get('by_severity', {}))}
- Peak Hours: {json.dumps(alert_patterns.get('peak_hours', []))}

---

Please provide:

1. **Executive Summary** (2-3 sentences): A high-level overview of cable plant health and key concerns.

2. **Key Findings** (3-5 bullet points): Most important observations from the data (RF signal quality, modem health, capacity utilization, customer impact).

3. **Trend Analysis**: Identify whether the network is improving, stable, or declining based on period comparison.

4. **Financial Impact Assessment**: Comment on revenue loss from outages and areas for improvement.

5. **Recommendations** (3-5 actionable items): Specific actions to improve network performance (node splits, plant maintenance, DOCSIS upgrades, etc.).

6. **Risk Assessment**: High, Medium, or Low risk level with brief justification.

Format your response as JSON with these fields:
{{
  "executive_summary": "...",
  "key_findings": ["...", "..."],
  "trend_analysis": {{
    "overall_trend": "improving|stable|declining",
    "details": "..."
  }},
  "financial_assessment": "...",
  "recommendations": ["...", "..."],
  "risk_level": "high|medium|low",
  "risk_justification": "..."
}}
"""
    return prompt


def build_anomaly_analysis_prompt(
    alert_data: Dict[str, Any],
    node_data: Dict[str, Any],
    recent_kpis: List[Dict[str, Any]],
    historical_patterns: Dict[str, Any]
) -> str:
    """Build a prompt for LLM-based anomaly analysis."""

    prompt = f"""You are a cable network analyst specializing in HFC plant anomaly detection and root cause analysis.

## Current Alert
{json.dumps(alert_data, indent=2)}

## Affected Fiber Node Information
{json.dumps(node_data, indent=2)}

## Recent KPIs (last hour)
{json.dumps(recent_kpis[-10:] if len(recent_kpis) > 10 else recent_kpis, indent=2)}

## Historical Alert Patterns for This Node
{json.dumps(historical_patterns, indent=2)}

---

Analyze this alert and provide:

1. **Root Cause Analysis**: What is likely causing this issue? (noise ingress, plant damage, equipment failure, capacity, etc.)

2. **Impact Assessment**: How severe is this issue and what services/customers are affected?

3. **Recommended Actions**: Specific remediation steps in priority order.

4. **Prevention**: How can similar issues be prevented in the future?

Format your response as JSON:
{{
  "root_cause": {{
    "primary_cause": "...",
    "contributing_factors": ["...", "..."],
    "confidence": 0.0-1.0
  }},
  "impact": {{
    "severity": "critical|warning|info",
    "affected_services": ["...", "..."],
    "estimated_customers_impacted": number
  }},
  "remediation": {{
    "immediate_actions": ["...", "..."],
    "follow_up_actions": ["...", "..."],
    "estimated_resolution_time_minutes": number
  }},
  "prevention": ["...", "..."]
}}
"""
    return prompt


async def generate_llm_executive_summary(
    db: Session,
    period_hours: int = 24
) -> Optional[Dict[str, Any]]:
    """
    Generate an LLM-powered executive summary using historical data.

    Returns None if LLM is not configured or unavailable.
    """
    # Get LLM config
    config = get_llm_config(db)
    if not config:
        logger.info("LLM not configured or disabled - skipping LLM summary")
        return None

    try:
        # Gather historical data
        kpi_trends = get_kpi_trends(db, period_hours, max_points=50)
        kpi_averages = get_historical_kpi_averages(db, period_hours)
        period_comparison = calculate_period_comparison(db, period_hours)
        revenue_loss = get_historical_revenue_loss(db, period_hours)
        incident_stats = get_incident_statistics(db, period_hours)
        alert_patterns = get_historical_alert_patterns(db, period_hours)

        # Build prompt
        prompt = build_executive_summary_prompt(
            kpi_trends,
            kpi_averages,
            period_comparison,
            revenue_loss,
            incident_stats,
            alert_patterns,
            period_hours
        )

        # Call LLM
        response_text = await call_llm(prompt, config)

        # Parse JSON response
        # Try to extract JSON from response (it may have markdown formatting)
        json_start = response_text.find('{')
        json_end = response_text.rfind('}') + 1
        if json_start >= 0 and json_end > json_start:
            json_str = response_text[json_start:json_end]
            result = json.loads(json_str)
        else:
            result = {"raw_response": response_text}

        result["generated_at"] = datetime.now().isoformat()
        result["model_used"] = config.get("model_name", config.get("provider", "unknown"))
        result["period_hours"] = period_hours
        result["data_sources"] = [
            kpi_averages.get("data_source", "aggregated_kpis"),
            "alerts",
            "self_healing_actions",
        ]

        return result

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response as JSON: {e}")
        return {
            "error": "Failed to parse LLM response",
            "raw_response": response_text if 'response_text' in dir() else None,
            "generated_at": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Failed to generate LLM executive summary: {e}")
        return {
            "error": str(e),
            "generated_at": datetime.now().isoformat(),
        }


def generate_rule_based_executive_insights(
    db: Session,
    period_hours: int = 24,
    # Optional pre-computed data to avoid duplicate queries
    precomputed_period_comparison: Optional[List[Dict[str, Any]]] = None,
    precomputed_revenue_loss: Optional[Dict[str, float]] = None,
    precomputed_incident_stats: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Generate rule-based executive insights without LLM.

    This provides instant insights that don't require LLM API calls.
    Uses cable network KPIs (DS/US SNR, throughput, latency, etc.).

    Args:
        db: Database session
        period_hours: Period to analyze
        precomputed_period_comparison: Pre-computed period comparison data (optional, avoids duplicate query)
        precomputed_revenue_loss: Pre-computed revenue loss data (optional, avoids duplicate query)
        precomputed_incident_stats: Pre-computed incident statistics (optional, avoids duplicate query)
    """
    insights = []
    now = datetime.now()

    # Get historical data - use pre-computed values if provided to avoid duplicate queries
    kpi_averages = get_historical_kpi_averages(db, period_hours)
    period_comparison = precomputed_period_comparison if precomputed_period_comparison is not None else calculate_period_comparison(db, period_hours)
    revenue_loss = precomputed_revenue_loss if precomputed_revenue_loss is not None else get_historical_revenue_loss(db, period_hours)
    incident_stats = precomputed_incident_stats if precomputed_incident_stats is not None else get_incident_statistics(db, period_hours)

    # Insight 1: Overall Cable Plant Health (based on DS SNR and latency)
    ds_snr = kpi_averages.get("ds_snr_db", 38.0)
    latency = kpi_averages.get("latency_ms", 15.0)

    if ds_snr >= 36.0 and latency <= 20:
        health_status = "excellent"
        severity = "info"
    elif ds_snr >= 33.0 and latency <= 35:
        health_status = "good"
        severity = "info"
    elif ds_snr >= 30.0:
        health_status = "moderate"
        severity = "warning"
    else:
        health_status = "concerning"
        severity = "critical"

    insights.append({
        "id": f"exec-health-{int(now.timestamp())}",
        "type": "network_health",
        "severity": severity,
        "title": f"Cable Plant Health: {health_status.title()}",
        "description": f"DS SNR: {ds_snr:.1f} dB, Average latency: {latency:.1f} ms",
        "recommendation": "Continue monitoring" if health_status in ("excellent", "good") else "Review degraded RF plant segments",
    })

    # Insight 2: Trend Analysis
    declining_metrics = [c for c in period_comparison if c.get("trend") == "declining"]
    improving_metrics = [c for c in period_comparison if c.get("trend") == "improving"]

    if len(declining_metrics) > len(improving_metrics):
        trend = "declining"
        trend_severity = "warning"
    elif len(improving_metrics) > len(declining_metrics):
        trend = "improving"
        trend_severity = "info"
    else:
        trend = "stable"
        trend_severity = "info"

    insights.append({
        "id": f"exec-trend-{int(now.timestamp())}",
        "type": "trend_analysis",
        "severity": trend_severity,
        "title": f"Network Trend: {trend.title()}",
        "description": f"{len(improving_metrics)} metrics improving, {len(declining_metrics)} declining",
        "recommendation": "Investigate declining metrics" if declining_metrics else "Maintain current operations",
        "details": {
            "improving": [m.get("metric_name") for m in improving_metrics],
            "declining": [m.get("metric_name") for m in declining_metrics],
        },
    })

    # Insight 3: Financial Impact
    total_loss = revenue_loss.get("total_loss", 0)
    if total_loss > 100000:
        fin_severity = "critical"
        fin_desc = "Significant revenue impact detected"
    elif total_loss > 10000:
        fin_severity = "warning"
        fin_desc = "Moderate revenue impact"
    else:
        fin_severity = "info"
        fin_desc = "Revenue impact within acceptable range"

    insights.append({
        "id": f"exec-financial-{int(now.timestamp())}",
        "type": "financial_impact",
        "severity": fin_severity,
        "title": f"Financial Impact: ${total_loss:,.0f}",
        "description": fin_desc,
        "recommendation": "Focus on reducing outage duration and truck rolls" if total_loss > 10000 else "Continue monitoring",
        "details": revenue_loss,
    })

    # Insight 4: Self-Healing / Auto-Resolution Performance
    success_rate = incident_stats.get("success_rate", 0)
    mttr = incident_stats.get("mttr_minutes", 30)

    if success_rate >= 90 and mttr <= 20:
        healing_status = "excellent"
        healing_severity = "info"
    elif success_rate >= 75:
        healing_status = "good"
        healing_severity = "info"
    else:
        healing_status = "needs improvement"
        healing_severity = "warning"

    insights.append({
        "id": f"exec-healing-{int(now.timestamp())}",
        "type": "self_healing_performance",
        "severity": healing_severity,
        "title": f"Auto-Resolution: {success_rate:.1f}% Success Rate",
        "description": f"MTTR: {mttr:.1f} minutes, Status: {healing_status}",
        "recommendation": "Review failed auto-resolution actions" if success_rate < 85 else "Maintain AI automation",
        "details": incident_stats,
    })

    return insights
