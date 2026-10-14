"""Agentic Capacity Planning endpoints"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..config import settings
from ..database import get_db
from ..schemas import (
    AgentThought,
    AgenticCapacityPlanningRequest,
    AgenticCapacityPlanningStartResponse,
    AgenticCapacityPlanningStatus,
)
from . import safe_error_response, logger

router = APIRouter(prefix=settings.API_V1_STR, tags=["capacity-planning"])


@router.post("/capacity-planning/agentic/start", response_model=AgenticCapacityPlanningStartResponse)
def start_agentic_capacity_planning(
    request: AgenticCapacityPlanningRequest,
    db: Session = Depends(get_db),
):
    """
    Start an agentic capacity planning analysis.

    This endpoint initiates a multi-agent analysis pipeline:
    1. Data Collector Agent - Gathers node/DC data by backhaul type
    2. Upgrade Analyzer Agent - Calculates bandwidth/latency improvement
    3. Hardware Checker Agent - Checks equipment compatibility and costs
    4. Capacity Forecaster Agent - LLM-powered forecasting

    Analysis Modes:
    - current_state: Analyze current capacity without upgrade scenarios
    - upgrade_scenario: Analyze impact of upgrading to target backhaul type
    - add_redundancy: Analyze adding redundant connections

    Returns an execution_id for polling status via GET endpoint.
    """
    from ..agentic_capacity_planner import start_agentic_capacity_planning as start_planning

    execution_id = start_planning(
        db=db,
        analysis_mode=request.analysis_mode,
        target_backhaul_type=request.target_upgrade_type,
        current_backhaul_filter=request.current_node_type_filter or [],
        region=request.region,
        city=request.city,
        datacenter_ids=request.headend_ids or [],
        node_ids=request.node_ids or [],
        include_nodes=request.include_nodes,
        include_datacenters=request.include_headends,
        include_cost_estimate=request.include_cost_estimate,
        forecast_periods=request.forecast_periods,
    )

    return AgenticCapacityPlanningStartResponse(
        execution_id=execution_id,
        status="running",
    )


@router.get("/capacity-planning/agentic/{execution_id}", response_model=AgenticCapacityPlanningStatus)
def get_agentic_capacity_planning_status(
    execution_id: str,
    db: Session = Depends(get_db),
):
    """
    Get the status of an agentic capacity planning execution.

    Poll this endpoint every 1-2 seconds while status is "running" to:
    - Track which agent is currently active
    - View the stream of agent "thoughts" and actions
    - Get progress percentage

    When status is "completed", the result field contains:
    - Capacity forecasts (30/60/90 days)
    - Upgrade impact analysis (if upgrade_scenario mode)
    - Hardware compatibility report
    - Cost estimates
    - LLM-generated recommendations
    """
    from ..agentic_capacity_planner import get_execution_status

    status = get_execution_status(execution_id, db=db)

    if not status:
        raise HTTPException(status_code=404, detail=f"Execution {execution_id} not found")

    # Convert to response model
    thoughts = [AgentThought(**t) for t in status.get("thoughts", [])]

    return AgenticCapacityPlanningStatus(
        execution_id=status["execution_id"],
        status=status["status"],
        started_at=status["started_at"],
        completed_at=status.get("completed_at"),
        current_agent=status.get("current_agent"),
        current_agent_name=status.get("current_agent_name"),
        progress_percent=status.get("progress_percent", 0),
        thoughts=thoughts,
        analysis_mode=status.get("analysis_mode", "current_state"),
        target_upgrade_type=status.get("target_backhaul_type"),
        upgrade_analysis=status.get("upgrade_analysis"),
        hardware_compatibility=status.get("hardware_compatibility"),
        headend_analysis=status.get("datacenter_analysis"),
        result=status.get("result"),
        error=status.get("error"),
    )
