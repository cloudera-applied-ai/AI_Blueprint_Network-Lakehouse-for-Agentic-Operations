"""
Autonomous Executor Module - AI-driven action planning and execution.

This module handles:
- Creating action plans from AI analysis results
- Executing action steps autonomously
- Tracking execution progress
- Creating SelfHealingAction records
- Resolving alerts after successful execution

Ported from src/services/autonomousExecutor.ts
"""

import json
import re
import uuid
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

from sqlalchemy.orm import Session
from sqlalchemy import select, func

from .models import (
    FiberNodeModel,
    KPIMetricsModel,
    AlertModel,
    SelfHealingActionModel,
    AIActionPlanModel,
    AIAlertAnalysisModel,
    LLMConfigModel,
)
from .sensor_generator import generate_all_sensor_data
from .ai_analyzer import AgentAnalysis, get_llm_config
from .llm_queue import llm_queue


class StepType(str, Enum):
    AUTOMATED_HEALING = "automated_healing"
    CREW_DISPATCH = "crew_dispatch"
    CONFIGURATION_CHANGE = "configuration_change"
    MONITORING = "monitoring"


class PlanStatus(str, Enum):
    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepStatus(str, Enum):
    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class ActionStep:
    """Single step in an action plan"""
    step_number: int
    step_type: StepType
    description: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    estimated_duration_seconds: int = 30
    status: StepStatus = StepStatus.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_number": self.step_number,
            "action_type": self.step_type.value,
            "description": self.description,
            "parameters": self.parameters,
            "estimated_duration_seconds": self.estimated_duration_seconds,
            "status": self.status.value,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "result": self.result,
        }


@dataclass
class ActionPlan:
    """Complete action plan for an alert"""
    plan_id: str
    alert_id: str
    node_id: str
    analysis_id: Optional[str]
    root_cause: str
    priority: str  # low, medium, high, critical
    status: PlanStatus
    steps: List[ActionStep]
    current_step_index: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    execution_log: List[Dict[str, Any]] = field(default_factory=list)
    failure_reason: Optional[str] = None
    success: Optional[bool] = None
    created_actions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "alert_id": self.alert_id,
            "node_id": self.node_id,
            "analysis_id": self.analysis_id,
            "root_cause": self.root_cause,
            "priority": self.priority,
            "status": self.status.value,
            "steps": [s.to_dict() for s in self.steps],
            "current_step_index": self.current_step_index,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "execution_log": self.execution_log,
            "failure_reason": self.failure_reason,
            "success": self.success,
            "created_actions": self.created_actions,
        }


# Map action types to SelfHealingAction types
ACTION_TYPE_MAP = {
    "automated_healing": ["MODEM_REMOTE_REBOOT", "PROVISIONING_REFRESH", "SIGNAL_LEVEL_ADJUSTMENT", "TRAFFIC_REROUTE"],
    "crew_dispatch": ["TICKET_CREATION"],
    "configuration_change": ["FIRMWARE_PUSH", "CMTS_PORT_RESET", "NODE_CAPACITY_REBALANCE"],
    "monitoring": ["TICKET_CREATION"],
}


def infer_action_type(description: str) -> str:
    """Infer specific action type from step description"""
    desc_lower = description.lower()

    if "reboot" in desc_lower or "restart" in desc_lower or "modem" in desc_lower:
        return "MODEM_REMOTE_REBOOT"
    elif "firmware" in desc_lower or "update" in desc_lower or "push" in desc_lower:
        return "FIRMWARE_PUSH"
    elif "provision" in desc_lower or "refresh" in desc_lower:
        return "PROVISIONING_REFRESH"
    elif ("cmts" in desc_lower or "port" in desc_lower) and "reset" in desc_lower:
        return "CMTS_PORT_RESET"
    elif "signal" in desc_lower or "level" in desc_lower or "power" in desc_lower:
        return "SIGNAL_LEVEL_ADJUSTMENT"
    elif "reroute" in desc_lower or "redirect" in desc_lower or "traffic" in desc_lower:
        return "TRAFFIC_REROUTE"
    elif "balance" in desc_lower or "capacity" in desc_lower or "rebalance" in desc_lower:
        return "NODE_CAPACITY_REBALANCE"
    elif "ticket" in desc_lower or "dispatch" in desc_lower or "crew" in desc_lower:
        return "TICKET_CREATION"
    else:
        return "PROVISIONING_REFRESH"


def build_action_plan_prompt(
    analysis: AgentAnalysis,
    node: FiberNodeModel,
    sensor_data: Dict[str, Any],
) -> List[Dict[str, str]]:
    """Build the LLM prompt for action plan generation"""
    system_prompt = """You are an autonomous AI executor for cable network (HFC plant) operations.
Based on the analysis provided, create an EXECUTABLE action plan with specific steps.

You must create steps that can be executed automatically without human intervention.
Each step should be specific and actionable.

Available action types:
1. automated_healing: Software/config fixes (modem reboot, provisioning refresh, signal adjustment, traffic reroute)
2. crew_dispatch: Hardware repairs that need field technicians (ONLY for physical plant issues)
3. configuration_change: Network parameter adjustments (firmware push, CMTS port reset, capacity rebalance)
4. monitoring: Set up enhanced tracking

Respond with valid JSON only:
{
    "rootCause": "specific root cause",
    "priority": "critical|high|medium|low",
    "confidence": 0.85,
    "reasoning": "why this plan will resolve the issue",
    "steps": [
        {
            "order": 1,
            "type": "automated_healing|crew_dispatch|configuration_change|monitoring",
            "description": "SPECIFIC action to take",
            "estimated_duration_seconds": 30
        }
    ]
}"""

    # Build context from analysis and sensor data
    context = f"""Based on the AI analysis, create an executable action plan:

**ANALYSIS:**
- Alert ID: {analysis.alert_id}
- Node: {node.node_id} ({node.city}, {node.region})
- Root Cause: {analysis.root_cause}
- Urgency: {analysis.urgency_score}/10
- Confidence: {analysis.confidence * 100:.0f}%
- Reasoning: {analysis.reasoning}

**RECOMMENDATIONS FROM ANALYSIS:**
"""
    for i, rec in enumerate(analysis.recommendations, 1):
        rec_text = rec if isinstance(rec, str) else str(rec)
        context += f"{i}. {rec_text}\n"

    context += f"""
**NODE INFO:**
- Status: {node.status}
- Node Type: {node.node_type}
- DOCSIS Version: {node.docsis_version}
- Homes Passed: {node.homes_passed}
- Homes Active: {node.homes_active}
- Manufacturer: {node.manufacturer} {node.hardware_model}

**SENSOR DATA HIGHLIGHTS:**
"""

    # Add RF plant issues
    rf_plant = sensor_data.get("antenna", {})
    if rf_plant:
        if rf_plant.get("rf_ingress_detected", False):
            context += f"- RF INGRESS DETECTED\n"
        if rf_plant.get("fec_uncorrected_codewords", 0) > 0:
            context += f"- FEC UNCORRECTED CODEWORDS: {rf_plant.get('fec_uncorrected_codewords', 0)}\n"
        if rf_plant.get("ds_snr_db", 40) < 33:
            context += f"- LOW DOWNSTREAM SNR: {rf_plant.get('ds_snr_db', 40):.1f} dB\n"
        if rf_plant.get("us_snr_db", 30) < 25:
            context += f"- LOW UPSTREAM SNR: {rf_plant.get('us_snr_db', 30):.1f} dB\n"

    # Add equipment issues
    equipment = sensor_data.get("equipment", {})
    if equipment:
        components = equipment.get("component_health", [])
        failed = [c for c in components if c.get("status") in ("failed", "critical")]
        if failed:
            context += f"- FAILED COMPONENTS: {', '.join(c.get('component_name', 'Unknown') for c in failed)}\n"
        degraded = [c for c in components if c.get("status") == "degraded"]
        if degraded:
            context += f"- DEGRADED COMPONENTS: {', '.join(c.get('component_name', 'Unknown') for c in degraded)}\n"

    # Add environmental issues
    environmental = sensor_data.get("environmental", {})
    if environmental:
        if environmental.get("power_quality", 100) < 85:
            context += f"- POWER QUALITY: {environmental.get('power_quality', 100):.0f}%\n"
        if environmental.get("cabinet_temperature", 30) > 45:
            context += f"- HIGH TEMP: {environmental.get('cabinet_temperature', 30):.1f}C\n"
        if environmental.get("interference_level", 0) > 30:
            context += f"- RF INTERFERENCE: {environmental.get('interference_level', 0):.0f}%\n"

    context += """
Create a step-by-step action plan that will be EXECUTED IMMEDIATELY.
Focus on automated actions that don't require physical access.
Only include crew_dispatch for actual plant damage or hardware failures requiring site visit."""

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": context},
    ]


def parse_action_plan_response(
    response_content: str,
    alert_id: str,
    node_id: str,
    analysis_id: Optional[str],
) -> ActionPlan:
    """Parse LLM response into an ActionPlan object"""
    try:
        # Try to extract JSON from response
        json_match = re.search(r'\{[\s\S]*\}', response_content)
        if json_match:
            data = json.loads(json_match.group())
        else:
            raise ValueError("No JSON found in response")
    except (json.JSONDecodeError, ValueError) as e:
        # Return a fallback plan
        return ActionPlan(
            plan_id=f"plan-{uuid.uuid4().hex[:12]}",
            alert_id=alert_id,
            node_id=node_id,
            analysis_id=analysis_id,
            root_cause="Unable to parse LLM response",
            priority="medium",
            status=PlanStatus.PENDING,
            steps=[
                ActionStep(
                    step_number=1,
                    step_type=StepType.MONITORING,
                    description="Enhanced monitoring activated - manual review required",
                    estimated_duration_seconds=10,
                )
            ],
            execution_log=[{"error": str(e), "raw_response": response_content[:500]}],
        )

    # Parse steps
    steps = []
    for i, step_data in enumerate(data.get("steps", []), 1):
        step_type_str = step_data.get("type", "monitoring").lower()
        try:
            step_type = StepType(step_type_str)
        except ValueError:
            step_type = StepType.MONITORING

        steps.append(ActionStep(
            step_number=i,
            step_type=step_type,
            description=step_data.get("description", "Execute action"),
            estimated_duration_seconds=step_data.get("estimated_duration_seconds", 30),
        ))

    if not steps:
        # Add default step if none parsed
        steps.append(ActionStep(
            step_number=1,
            step_type=StepType.MONITORING,
            description="Enhanced monitoring activated",
            estimated_duration_seconds=10,
        ))

    # Parse priority
    priority = data.get("priority", "medium").lower()
    if priority not in ("low", "medium", "high", "critical"):
        priority = "medium"

    return ActionPlan(
        plan_id=f"plan-{uuid.uuid4().hex[:12]}",
        alert_id=alert_id,
        node_id=node_id,
        analysis_id=analysis_id,
        root_cause=data.get("rootCause", "Unknown root cause"),
        priority=priority,
        status=PlanStatus.PENDING,
        steps=steps,
    )


async def create_action_plan(
    db: Session,
    analysis: AgentAnalysis,
    use_llm: bool = True,
) -> Optional[ActionPlan]:
    """
    Create an action plan based on AI analysis.

    Args:
        db: Database session
        analysis: The AgentAnalysis result
        use_llm: Whether to use LLM to generate plan (vs rule-based)

    Returns:
        ActionPlan or None if creation failed
    """
    # Get node
    node_query = select(FiberNodeModel).where(FiberNodeModel.node_id == analysis.node_id)
    node = db.execute(node_query).scalar_one_or_none()
    if not node:
        print(f"Node {analysis.node_id} not found for action plan")
        return None

    # Generate sensor data - convert node model to dict for sensor generator
    node_dict = {
        "node_id": node.node_id,
        "status": node.status,
        "latitude": node.latitude,
        "longitude": node.longitude,
        "region": node.region,
        "climate_zone": getattr(node, "climate_zone", None),
        "manufacturer": node.manufacturer,
        "hardware_model": node.hardware_model,
    }
    sensor_data = generate_all_sensor_data(node_dict)

    # Check if analysis recommends autonomous execution
    if not analysis.should_execute_autonomously:
        print(f"Analysis recommends manual intervention for {analysis.alert_id[:8]}")
        # Still create a plan for tracking, but mark as pending manual review
        plan = ActionPlan(
            plan_id=f"plan-{uuid.uuid4().hex[:12]}",
            alert_id=analysis.alert_id,
            node_id=analysis.node_id,
            analysis_id=None,
            root_cause=f"[MANUAL REVIEW] {analysis.root_cause}",
            priority="high" if analysis.urgency_score >= 7 else "medium",
            status=PlanStatus.PENDING,
            steps=[
                ActionStep(
                    step_number=1,
                    step_type=StepType.CREW_DISPATCH,
                    description=f"Manual review required: {analysis.summary}",
                    estimated_duration_seconds=60,
                ),
                ActionStep(
                    step_number=2,
                    step_type=StepType.MONITORING,
                    description="Enhanced monitoring activated pending resolution",
                    estimated_duration_seconds=10,
                ),
            ],
        )
        return plan

    # Use LLM to generate action plan if available
    if use_llm:
        llm_config = get_llm_config(db)
        if llm_config:
            messages = build_action_plan_prompt(analysis, node, sensor_data)

            # Build API request
            api_url = llm_config["endpoint_url"]
            headers = {"Content-Type": "application/json"}

            if llm_config.get("api_key"):
                headers["Authorization"] = f"Bearer {llm_config['api_key']}"
            elif llm_config.get("jwt_token"):
                headers["Authorization"] = f"Bearer {llm_config['jwt_token']}"

            payload = {
                "messages": messages,
                "temperature": llm_config.get("temperature", 0.7),
                "max_tokens": llm_config.get("max_tokens", 1500),
            }

            if llm_config.get("model_name"):
                payload["model"] = llm_config["model_name"]

            try:
                job_id = llm_queue.submit_and_process_parallel(
                    messages=messages,
                    provider=llm_config["provider"],
                    api_url=api_url,
                    headers=headers,
                    payload=payload,
                    priority=5,
                )

                result = llm_queue.wait_for_job(job_id, timeout=60.0)

                if result:
                    response_content = ""
                    if "choices" in result and len(result["choices"]) > 0:
                        choice = result["choices"][0]
                        if "message" in choice:
                            response_content = choice["message"].get("content", "")
                        elif "text" in choice:
                            response_content = choice["text"]
                    elif "content" in result:
                        response_content = result["content"]

                    if response_content:
                        plan = parse_action_plan_response(
                            response_content,
                            analysis.alert_id,
                            analysis.node_id,
                            None,
                        )
                        print(f"LLM Action Plan Created: {len(plan.steps)} steps for {node.node_id}")
                        return plan

            except Exception as e:
                print(f"LLM action plan generation failed: {e}")

    # Fall back to rule-based action plan
    plan = create_rule_based_plan(analysis, node, sensor_data)
    print(f"Rule-based Action Plan Created: {len(plan.steps)} steps for {node.node_id}")
    return plan


def create_rule_based_plan(
    analysis: AgentAnalysis,
    node: FiberNodeModel,
    sensor_data: Dict[str, Any],
) -> ActionPlan:
    """Create a rule-based action plan without LLM"""
    steps = []
    step_num = 0

    root_cause_lower = analysis.root_cause.lower()
    urgency = analysis.urgency_score

    # Determine primary action based on root cause
    if "noise" in root_cause_lower or "ingress" in root_cause_lower:
        step_num += 1
        steps.append(ActionStep(
            step_number=step_num,
            step_type=StepType.AUTOMATED_HEALING,
            description="Adjust signal levels to compensate for ingress noise",
            estimated_duration_seconds=30,
        ))
        step_num += 1
        steps.append(ActionStep(
            step_number=step_num,
            step_type=StepType.CREW_DISPATCH,
            description="Dispatch line technician to locate and resolve RF ingress source",
            estimated_duration_seconds=60,
        ))

    elif "power" in root_cause_lower or "battery" in root_cause_lower:
        step_num += 1
        steps.append(ActionStep(
            step_number=step_num,
            step_type=StepType.MONITORING,
            description="Activate enhanced power monitoring for node power supply",
            estimated_duration_seconds=10,
        ))
        step_num += 1
        steps.append(ActionStep(
            step_number=step_num,
            step_type=StepType.CREW_DISPATCH,
            description="Dispatch technician to check node power supply and battery backup",
            estimated_duration_seconds=60,
        ))

    elif "congestion" in root_cause_lower or "capacity" in root_cause_lower or "utilization" in root_cause_lower:
        step_num += 1
        steps.append(ActionStep(
            step_number=step_num,
            step_type=StepType.AUTOMATED_HEALING,
            description="Reroute traffic across available CMTS ports to reduce congestion",
            estimated_duration_seconds=25,
        ))
        step_num += 1
        steps.append(ActionStep(
            step_number=step_num,
            step_type=StepType.CONFIGURATION_CHANGE,
            description="Rebalance OFDM channel allocation for optimal capacity distribution",
            estimated_duration_seconds=20,
        ))

    elif "modem" in root_cause_lower or "cpe" in root_cause_lower or "offline" in root_cause_lower:
        step_num += 1
        steps.append(ActionStep(
            step_number=step_num,
            step_type=StepType.AUTOMATED_HEALING,
            description="Initiate remote modem reboot for affected CPE devices",
            estimated_duration_seconds=25,
        ))
        step_num += 1
        steps.append(ActionStep(
            step_number=step_num,
            step_type=StepType.AUTOMATED_HEALING,
            description="Execute provisioning refresh for affected modems",
            estimated_duration_seconds=20,
        ))

    elif "snr" in root_cause_lower or "signal" in root_cause_lower or "fec" in root_cause_lower:
        step_num += 1
        steps.append(ActionStep(
            step_number=step_num,
            step_type=StepType.AUTOMATED_HEALING,
            description="Adjust downstream and upstream signal levels to optimize SNR",
            estimated_duration_seconds=30,
        ))
        step_num += 1
        steps.append(ActionStep(
            step_number=step_num,
            step_type=StepType.MONITORING,
            description="Monitor SNR and FEC error rate improvements",
            estimated_duration_seconds=10,
        ))

    elif "cmts" in root_cause_lower or "port" in root_cause_lower:
        step_num += 1
        steps.append(ActionStep(
            step_number=step_num,
            step_type=StepType.AUTOMATED_HEALING,
            description="Reset CMTS port and verify modem re-registration",
            estimated_duration_seconds=45,
        ))
        step_num += 1
        steps.append(ActionStep(
            step_number=step_num,
            step_type=StepType.MONITORING,
            description="Verify modem re-registration after CMTS port reset",
            estimated_duration_seconds=15,
        ))

    elif "firmware" in root_cause_lower or "software" in root_cause_lower:
        step_num += 1
        steps.append(ActionStep(
            step_number=step_num,
            step_type=StepType.CONFIGURATION_CHANGE,
            description="Push firmware update to affected node equipment",
            estimated_duration_seconds=45,
        ))
        step_num += 1
        steps.append(ActionStep(
            step_number=step_num,
            step_type=StepType.MONITORING,
            description="Verify firmware update applied successfully",
            estimated_duration_seconds=15,
        ))

    elif "temperature" in root_cause_lower or "thermal" in root_cause_lower:
        step_num += 1
        steps.append(ActionStep(
            step_number=step_num,
            step_type=StepType.MONITORING,
            description="Activate thermal monitoring for affected node enclosure",
            estimated_duration_seconds=10,
        ))
        step_num += 1
        steps.append(ActionStep(
            step_number=step_num,
            step_type=StepType.CREW_DISPATCH,
            description="Dispatch technician for cooling system check at node site",
            estimated_duration_seconds=60,
        ))

    else:
        # Default actions
        step_num += 1
        steps.append(ActionStep(
            step_number=step_num,
            step_type=StepType.AUTOMATED_HEALING,
            description="Apply provisioning refresh and signal level optimization",
            estimated_duration_seconds=25,
        ))

    # Always add monitoring as final step
    step_num += 1
    steps.append(ActionStep(
        step_number=step_num,
        step_type=StepType.MONITORING,
        description="Enhanced monitoring activated for 30 minutes on affected node",
        estimated_duration_seconds=10,
    ))

    # Determine priority
    if urgency >= 8:
        priority = "critical"
    elif urgency >= 6:
        priority = "high"
    elif urgency >= 4:
        priority = "medium"
    else:
        priority = "low"

    return ActionPlan(
        plan_id=f"plan-{uuid.uuid4().hex[:12]}",
        alert_id=analysis.alert_id,
        node_id=analysis.node_id,
        analysis_id=None,
        root_cause=analysis.root_cause,
        priority=priority,
        status=PlanStatus.PENDING,
        steps=steps,
    )


async def execute_step(
    db: Session,
    plan: ActionPlan,
    step: ActionStep,
) -> bool:
    """
    Execute a single step in the action plan.

    Returns True if step completed successfully.
    """
    now = datetime.utcnow()

    # Start step if pending
    if step.status == StepStatus.PENDING:
        step.status = StepStatus.EXECUTING
        step.started_at = now
        plan.execution_log.append({
            "timestamp": now.isoformat(),
            "event": "step_started",
            "step": step.step_number,
            "type": step.step_type.value,
            "description": step.description,
        })

    # Check if enough time has passed (simulated execution)
    if step.started_at:
        elapsed = (now - step.started_at).total_seconds()
        if elapsed < step.estimated_duration_seconds:
            return False  # Still executing

    # Execute based on step type
    try:
        if step.step_type == StepType.AUTOMATED_HEALING:
            result = await execute_automated_healing(db, plan, step)
        elif step.step_type == StepType.CREW_DISPATCH:
            result = execute_crew_dispatch(db, plan, step)
        elif step.step_type == StepType.CONFIGURATION_CHANGE:
            result = execute_configuration_change(db, plan, step)
        elif step.step_type == StepType.MONITORING:
            result = execute_monitoring(db, plan, step)
        else:
            result = "Unknown step type"

        step.status = StepStatus.COMPLETED
        step.completed_at = now
        step.result = result

        plan.execution_log.append({
            "timestamp": now.isoformat(),
            "event": "step_completed",
            "step": step.step_number,
            "result": result,
        })

        return True

    except Exception as e:
        step.status = StepStatus.FAILED
        step.completed_at = now
        step.result = str(e)

        plan.execution_log.append({
            "timestamp": now.isoformat(),
            "event": "step_failed",
            "step": step.step_number,
            "error": str(e),
        })

        return False


async def execute_automated_healing(
    db: Session,
    plan: ActionPlan,
    step: ActionStep,
) -> str:
    """Execute automated healing action"""
    import random

    action_type = infer_action_type(step.description)

    # Create SelfHealingAction record
    max_id_result = db.execute(select(func.max(SelfHealingActionModel.id)))
    next_id = (max_id_result.scalar() or 0) + 1

    action_id = f"ai-heal-{uuid.uuid4().hex[:8]}"
    now = datetime.utcnow()

    action = SelfHealingActionModel(
        id=next_id,
        action_id=action_id,
        alert_id=plan.alert_id,
        node_id=plan.node_id,
        action_type=action_type,
        description=f"[AI Autonomous] {step.description}",
        status="COMPLETED",
        start_time=step.started_at or now,
        end_time=now,
        effectiveness_score=80 + random.uniform(0, 15),  # 80-95%
    )

    db.add(action)
    plan.created_actions.append(action_id)

    return f"Automated healing completed: {action_type} (ID: {action_id})"


def execute_crew_dispatch(
    db: Session,
    plan: ActionPlan,
    step: ActionStep,
) -> str:
    """Execute crew dispatch action"""
    import random

    # Create a ticket/action for crew dispatch
    max_id_result = db.execute(select(func.max(SelfHealingActionModel.id)))
    next_id = (max_id_result.scalar() or 0) + 1

    action_id = f"ai-dispatch-{uuid.uuid4().hex[:8]}"
    now = datetime.utcnow()

    action = SelfHealingActionModel(
        id=next_id,
        action_id=action_id,
        alert_id=plan.alert_id,
        node_id=plan.node_id,
        action_type="TICKET_CREATION",
        description=f"[AI Crew Dispatch] {step.description}",
        status="PENDING",  # Crew dispatch stays pending until manually resolved
        start_time=now,
        effectiveness_score=0,  # Not yet effective
    )

    db.add(action)
    plan.created_actions.append(action_id)

    return f"Crew dispatch ticket created (ID: {action_id})"


def execute_configuration_change(
    db: Session,
    plan: ActionPlan,
    step: ActionStep,
) -> str:
    """Execute configuration change action"""
    # Simulate configuration change
    configs = [
        "OFDM channel allocation optimized",
        "Upstream frequency plan adjusted",
        "CMTS port configuration updated",
        "Modem provisioning parameters refreshed",
        "Node signal levels rebalanced",
    ]

    import random
    config_applied = random.choice(configs)
    return f"Configuration applied: {config_applied}"


def execute_monitoring(
    db: Session,
    plan: ActionPlan,
    step: ActionStep,
) -> str:
    """Execute monitoring setup action"""
    return "Enhanced monitoring activated for affected node"


async def execute_plan(db: Session, plan: ActionPlan) -> None:
    """
    Execute all steps in an action plan.

    This is called by the background task to process pending plans.
    """
    now = datetime.utcnow()

    # Start execution if pending
    if plan.status == PlanStatus.PENDING:
        plan.status = PlanStatus.EXECUTING
        plan.started_at = now
        plan.execution_log.append({
            "timestamp": now.isoformat(),
            "event": "plan_started",
            "root_cause": plan.root_cause,
        })
        print(f"Executing AI Plan: {plan.root_cause}")

    # Check if plan contains manual intervention requirement
    if "[MANUAL REVIEW]" in plan.root_cause:
        print(f"Plan {plan.plan_id[:12]} requires manual intervention - skipping auto-execution")
        return

    # Execute current step
    if plan.current_step_index < len(plan.steps):
        step = plan.steps[plan.current_step_index]

        completed = await execute_step(db, plan, step)

        if completed:
            plan.current_step_index += 1
            print(f"   Step {step.step_number}/{len(plan.steps)} completed: {step.result}")

    # Check if all steps completed
    all_completed = all(
        s.status in (StepStatus.COMPLETED, StepStatus.SKIPPED)
        for s in plan.steps
    )

    if all_completed:
        plan.status = PlanStatus.COMPLETED
        plan.completed_at = now
        plan.success = True
        plan.execution_log.append({
            "timestamp": now.isoformat(),
            "event": "plan_completed",
            "actions_created": len(plan.created_actions),
        })
        print(f"AI Plan Completed: {plan.root_cause}")

        # Resolve the associated alert
        try:
            alert_query = select(AlertModel).where(AlertModel.alert_id == plan.alert_id)
            alert = db.execute(alert_query).scalar_one_or_none()
            if alert and alert.status == "ACTIVE":
                alert.status = "RESOLVED"
                alert.resolved_at = now
                print(f"   Alert {plan.alert_id[:8]} resolved")
        except Exception as e:
            print(f"   Warning: Could not resolve alert: {e}")

    # Check for failures
    failed_steps = [s for s in plan.steps if s.status == StepStatus.FAILED]
    if failed_steps:
        plan.status = PlanStatus.FAILED
        plan.completed_at = now
        plan.success = False
        plan.failure_reason = f"Step {failed_steps[0].step_number} failed: {failed_steps[0].result}"
        plan.execution_log.append({
            "timestamp": now.isoformat(),
            "event": "plan_failed",
            "reason": plan.failure_reason,
        })
        print(f"AI Plan Failed: {plan.failure_reason}")


def save_plan_to_db(db: Session, plan: ActionPlan) -> None:
    """Save or update action plan in database"""
    try:
        # Check if plan exists
        existing = db.execute(
            select(AIActionPlanModel).where(AIActionPlanModel.plan_id == plan.plan_id)
        ).scalar_one_or_none()

        if existing:
            # Update existing
            existing.status = plan.status.value
            existing.steps = [s.to_dict() for s in plan.steps]
            existing.current_step_index = plan.current_step_index
            existing.started_at = plan.started_at
            existing.completed_at = plan.completed_at
            existing.execution_log = plan.execution_log
            existing.failure_reason = plan.failure_reason
            existing.success = plan.success
            existing.created_actions = plan.created_actions
        else:
            # Create new
            max_id_result = db.execute(select(func.max(AIActionPlanModel.id)))
            next_id = (max_id_result.scalar() or 0) + 1

            db_plan = AIActionPlanModel(
                id=next_id,
                plan_id=plan.plan_id,
                alert_id=plan.alert_id,
                node_id=plan.node_id,
                analysis_id=plan.analysis_id,
                root_cause=plan.root_cause,
                priority=plan.priority,
                status=plan.status.value,
                steps=[s.to_dict() for s in plan.steps],
                current_step_index=plan.current_step_index,
                started_at=plan.started_at,
                completed_at=plan.completed_at,
                execution_log=plan.execution_log,
                failure_reason=plan.failure_reason,
                success=plan.success,
                created_actions=plan.created_actions,
            )
            db.add(db_plan)

        db.commit()

    except Exception as e:
        db.rollback()
        print(f"Failed to save plan to database: {e}")
