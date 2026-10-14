"""AI Insights, Alert Analysis, and Action Plan endpoints"""
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from ..config import settings
from ..database import get_db
from ..models import (
    AIInsightModel,
    AIAlertAnalysisModel,
    AIActionPlanModel,
    AlertModel,
    FiberNodeModel,
    LLMConfigModel,
)
from ..schemas import (
    AIInsight as AIInsightSchema,
    AIInsightListResponse,
    AIAlertAnalysis as AIAlertAnalysisSchema,
    AIAlertAnalysisListResponse,
    AIActionPlan as AIActionPlanSchema,
    AIActionPlanListResponse,
)
from . import app_state, safe_error_response, logger

router = APIRouter(prefix=settings.API_V1_STR, tags=["ai"])


# =============================================================================
# AI INSIGHTS ENDPOINTS - Autonomous Network Analysis
# =============================================================================

# Cache for insights - regenerated every 30 seconds
_insights_cache = {
    "insights": [],
    "generated_at": None,
    "expires_at": None,
}


@router.get("/ai/insights", response_model=AIInsightListResponse)
def get_ai_insights(
    severity: Optional[str] = Query(None, description="Filter by severity (info, warning, critical)"),
    insight_type: Optional[str] = Query(None, description="Filter by insight type"),
    node_id: Optional[str] = Query(None, description="Filter by affected node ID"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of insights to return"),
    regenerate: bool = Query(False, description="Force regeneration of insights"),
    db: Session = Depends(get_db),
):
    """
    Get AI-generated insights about network state.

    Insights are rule-based analysis that runs automatically and doesn't require LLM.
    They analyze patterns across nodes, alerts, actions, and sensor data to provide
    actionable recommendations.

    Categories include:
    - Network health overview (30-day trends)
    - Maintenance analysis (overdue, upcoming)
    - Equipment lifecycle analysis
    - Regional health distribution
    - Technology coverage analysis
    - Power and redundancy alerts
    - Equipment component health
    - Antenna alignment issues
    - Environmental conditions
    - Alert pattern detection
    - Self-healing effectiveness
    """
    from ..ai_insights import generate_rule_based_insights

    now = datetime.utcnow()

    # Check if we need to regenerate insights
    cache_valid = (
        _insights_cache["expires_at"] is not None
        and _insights_cache["expires_at"] > now
        and not regenerate
    )

    if not cache_valid:
        # Generate fresh insights
        try:
            insights = generate_rule_based_insights(db)
            _insights_cache["insights"] = insights
            _insights_cache["generated_at"] = now
            _insights_cache["expires_at"] = now + timedelta(seconds=30)
            print(f"📊 Generated {len(insights)} AI insights")
        except Exception as e:
            logger.error(f"Failed to generate insights: {e}", exc_info=True)
            # Return cached insights if available, otherwise empty list
            if not _insights_cache["insights"]:
                return {
                    "total": 0,
                    "items": [],
                    "generated_at": now,
                }

    insights = _insights_cache["insights"]

    # Apply filters
    if severity:
        insights = [i for i in insights if i.severity == severity]
    if insight_type:
        insights = [i for i in insights if i.insight_type.value == insight_type]
    if node_id:
        insights = [i for i in insights if node_id in i.affected_node_ids]

    # Convert to response format
    result_items = []
    for insight in insights[:limit]:
        result_items.append({
            "id": hash(insight.id) % 1000000,  # Generate a numeric ID
            "insight_id": insight.id,
            "insight_type": insight.insight_type.value,
            "severity": insight.severity,
            "title": insight.title,
            "description": insight.description,
            "recommendation": insight.recommendation,
            "confidence": insight.confidence,
            "affected_node_ids": insight.affected_node_ids[:100],  # Limit for response size
            "related_alert_ids": insight.related_alert_ids[:50],
            "metadata": insight.metadata,
            "expires_at": insight.expires_at.isoformat() if insight.expires_at else None,
            "created_at": insight.timestamp,
        })

    return {
        "total": len(result_items),
        "items": result_items,
        "generated_at": _insights_cache["generated_at"] or now,
    }


@router.get("/ai/status")
def get_ai_status(db: Session = Depends(get_db)):
    """
    Get status of the autonomous AI analysis system.

    Returns current state of insights generation, analysis queue, and action plans.
    """
    now = datetime.utcnow()

    # Count active insights
    insights_count = len(_insights_cache.get("insights", []))

    # Check LLM config for enabled status
    llm_query = select(LLMConfigModel).where(LLMConfigModel.id == 1)
    llm_result = db.execute(llm_query)
    llm_config = llm_result.scalar_one_or_none()
    llm_enabled = llm_config.enabled if llm_config else False

    # Count active analyses and plans
    # Get analysis counts
    try:
        analysis_count = db.execute(
            select(func.count(AIAlertAnalysisModel.id))
        ).scalar() or 0
    except:
        analysis_count = 0

    # Get plan counts
    try:
        pending_plans = db.execute(
            select(func.count(AIActionPlanModel.id)).where(
                AIActionPlanModel.status == 'pending'
            )
        ).scalar() or 0
        executing_plans = db.execute(
            select(func.count(AIActionPlanModel.id)).where(
                AIActionPlanModel.status == 'executing'
            )
        ).scalar() or 0
        completed_24h = db.execute(
            select(func.count(AIActionPlanModel.id)).where(
                AIActionPlanModel.status == 'completed',
                AIActionPlanModel.completed_at >= now - timedelta(hours=24)
            )
        ).scalar() or 0
        failed_24h = db.execute(
            select(func.count(AIActionPlanModel.id)).where(
                AIActionPlanModel.status == 'failed',
                AIActionPlanModel.completed_at >= now - timedelta(hours=24)
            )
        ).scalar() or 0
    except:
        pending_plans = 0
        executing_plans = 0
        completed_24h = 0
        failed_24h = 0

    return {
        "enabled": True,  # Rule-based insights always enabled
        "llm_enabled": llm_enabled,
        "insights_count": insights_count,
        "insights_last_generated": _insights_cache.get("generated_at"),
        "insights_expires_at": _insights_cache.get("expires_at"),
        "active_analyses": analysis_count,
        "pending_plans": pending_plans,
        "executing_plans": executing_plans,
        "completed_plans_24h": completed_24h,
        "failed_plans_24h": failed_24h,
        "timestamp": now.isoformat(),
    }


# =============================================================================
# AI ALERT ANALYSIS ENDPOINTS
# =============================================================================

# Cache for recent analyses
_analysis_cache: Dict[str, Dict[str, Any]] = {}


@router.post("/ai/analyze/{alert_id}")
async def analyze_alert_endpoint(
    alert_id: str,
    use_llm: bool = Query(True, description="Use LLM analysis (if available) vs rule-based only"),
    db: Session = Depends(get_db),
):
    """
    Trigger AI analysis for a specific alert.

    This can be called manually or is triggered automatically when alerts are generated.

    Returns the analysis result including:
    - Root cause analysis
    - Recommendations
    - Confidence score
    - Whether to execute autonomously
    - Urgency score
    """
    from ..ai_analyzer import analyze_alert_with_llm, analyze_alert_rule_based, get_llm_config

    # Check if alert exists
    alert_query = select(AlertModel).where(AlertModel.alert_id == alert_id)
    alert = db.execute(alert_query).scalar_one_or_none()

    if not alert:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")

    # Perform analysis
    analysis = None
    if use_llm:
        llm_config = get_llm_config(db)
        if llm_config:
            analysis = await analyze_alert_with_llm(db, alert_id)

    if not analysis:
        # Fall back to rule-based
        analysis = analyze_alert_rule_based(db, alert_id)

    if not analysis:
        raise HTTPException(status_code=500, detail="Analysis failed")

    # Store in database
    try:
        max_id_result = db.execute(select(func.max(AIAlertAnalysisModel.id)))
        next_id = (max_id_result.scalar() or 0) + 1

        analysis_record = AIAlertAnalysisModel(
            id=next_id,
            analysis_id=f"analysis-{uuid.uuid4().hex[:12]}",
            alert_id=alert_id,
            node_id=analysis.node_id,
            summary=analysis.summary,
            root_cause=analysis.root_cause,
            recommendations=analysis.recommendations,
            confidence=analysis.confidence,
            reasoning=analysis.reasoning,
            should_execute_autonomously=analysis.should_execute_autonomously,
            urgency_score=analysis.urgency_score,
            sensor_data_used=analysis.sensor_data_used,
        )
        db.add(analysis_record)
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to store analysis: {e}")

    return {
        "alert_id": alert_id,
        "node_id": analysis.node_id,
        "summary": analysis.summary,
        "root_cause": analysis.root_cause,
        "recommendations": analysis.recommendations,
        "confidence": analysis.confidence,
        "reasoning": analysis.reasoning,
        "should_execute_autonomously": analysis.should_execute_autonomously,
        "urgency_score": analysis.urgency_score,
        "sensor_data_used": analysis.sensor_data_used,
        "analysis_time_ms": analysis.analysis_time_ms,
    }


@router.get("/ai/analyses")
def get_analyses(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    alert_id: Optional[str] = Query(None, description="Filter by alert ID"),
    node_id: Optional[str] = Query(None, description="Filter by node ID"),
    autonomous_only: bool = Query(False, description="Only show analyses recommending autonomous execution"),
    db: Session = Depends(get_db),
):
    """
    Get recent AI analyses with filtering.
    """
    query = select(AIAlertAnalysisModel)

    if alert_id:
        query = query.where(AIAlertAnalysisModel.alert_id == alert_id)
    if node_id:
        query = query.where(AIAlertAnalysisModel.node_id == node_id)
    if autonomous_only:
        query = query.where(AIAlertAnalysisModel.should_execute_autonomously == True)

    query = query.order_by(AIAlertAnalysisModel.created_at.desc())

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = db.execute(count_query).scalar() or 0

    # Get paginated results
    query = query.offset(skip).limit(limit)
    results = db.execute(query).scalars().all()

    return {
        "total": total,
        "items": [
            {
                "id": r.id,
                "analysis_id": r.analysis_id,
                "alert_id": r.alert_id,
                "node_id": r.node_id,
                "summary": r.summary,
                "root_cause": r.root_cause,
                "recommendations": r.recommendations,
                "confidence": r.confidence,
                "reasoning": r.reasoning,
                "should_execute_autonomously": r.should_execute_autonomously,
                "urgency_score": r.urgency_score,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in results
        ],
    }


@router.get("/ai/analyses/{analysis_id}")
def get_analysis(analysis_id: str, db: Session = Depends(get_db)):
    """
    Get a specific analysis by ID.
    """
    query = select(AIAlertAnalysisModel).where(
        AIAlertAnalysisModel.analysis_id == analysis_id
    )
    result = db.execute(query).scalar_one_or_none()

    if not result:
        raise HTTPException(status_code=404, detail=f"Analysis {analysis_id} not found")

    return {
        "id": result.id,
        "analysis_id": result.analysis_id,
        "alert_id": result.alert_id,
        "node_id": result.node_id,
        "summary": result.summary,
        "root_cause": result.root_cause,
        "recommendations": result.recommendations,
        "confidence": result.confidence,
        "reasoning": result.reasoning,
        "should_execute_autonomously": result.should_execute_autonomously,
        "urgency_score": result.urgency_score,
        "sensor_data_used": result.sensor_data_used,
        "created_at": result.created_at.isoformat() if result.created_at else None,
    }


# =============================================================================
# AI ACTION PLAN ENDPOINTS
# =============================================================================


@router.get("/ai/plans")
def get_action_plans(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    status: Optional[str] = Query(None, description="Filter by status (pending, executing, completed, failed)"),
    node_id: Optional[str] = Query(None, description="Filter by node ID"),
    priority: Optional[str] = Query(None, description="Filter by priority (low, medium, high, critical)"),
    db: Session = Depends(get_db),
):
    """
    Get AI action plans with filtering.
    """
    query = select(AIActionPlanModel)

    if status:
        query = query.where(AIActionPlanModel.status == status)
    if node_id:
        query = query.where(AIActionPlanModel.node_id == node_id)
    if priority:
        query = query.where(AIActionPlanModel.priority == priority)

    query = query.order_by(AIActionPlanModel.created_at.desc())

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = db.execute(count_query).scalar() or 0

    # Get paginated results
    query = query.offset(skip).limit(limit)
    results = db.execute(query).scalars().all()

    return {
        "total": total,
        "items": [
            {
                "id": r.id,
                "plan_id": r.plan_id,
                "alert_id": r.alert_id,
                "node_id": r.node_id,
                "analysis_id": r.analysis_id,
                "root_cause": r.root_cause,
                "priority": r.priority,
                "status": r.status,
                "steps": r.steps,
                "current_step_index": r.current_step_index,
                "started_at": r.started_at.isoformat() if r.started_at else None,
                "completed_at": r.completed_at.isoformat() if r.completed_at else None,
                "success": r.success,
                "created_actions": r.created_actions,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in results
        ],
    }


@router.get("/ai/plans/{plan_id}")
def get_action_plan(plan_id: str, db: Session = Depends(get_db)):
    """
    Get a specific action plan by ID.
    """
    query = select(AIActionPlanModel).where(
        AIActionPlanModel.plan_id == plan_id
    )
    result = db.execute(query).scalar_one_or_none()

    if not result:
        raise HTTPException(status_code=404, detail=f"Action plan {plan_id} not found")

    return {
        "id": result.id,
        "plan_id": result.plan_id,
        "alert_id": result.alert_id,
        "node_id": result.node_id,
        "analysis_id": result.analysis_id,
        "root_cause": result.root_cause,
        "priority": result.priority,
        "status": result.status,
        "steps": result.steps,
        "current_step_index": result.current_step_index,
        "started_at": result.started_at.isoformat() if result.started_at else None,
        "completed_at": result.completed_at.isoformat() if result.completed_at else None,
        "execution_log": result.execution_log,
        "failure_reason": result.failure_reason,
        "success": result.success,
        "created_actions": result.created_actions,
        "created_at": result.created_at.isoformat() if result.created_at else None,
        "updated_at": result.updated_at.isoformat() if result.updated_at else None,
    }


@router.post("/ai/plans/{plan_id}/cancel")
def cancel_action_plan(plan_id: str, db: Session = Depends(get_db)):
    """
    Cancel a pending or executing action plan.
    """
    query = select(AIActionPlanModel).where(
        AIActionPlanModel.plan_id == plan_id
    )
    plan = db.execute(query).scalar_one_or_none()

    if not plan:
        raise HTTPException(status_code=404, detail=f"Action plan {plan_id} not found")

    if plan.status in ("completed", "failed", "cancelled"):
        raise HTTPException(status_code=400, detail=f"Cannot cancel plan with status: {plan.status}")

    plan.status = "cancelled"
    plan.completed_at = datetime.utcnow()
    plan.failure_reason = "Cancelled by user"

    db.commit()

    return {"message": f"Plan {plan_id} cancelled", "status": "cancelled"}


@router.post("/ai/analyze-and-execute/{alert_id}")
async def analyze_and_execute_alert(
    alert_id: str,
    execute: bool = Query(True, description="Execute the plan after analysis"),
    db: Session = Depends(get_db),
):
    """
    Trigger full AI analysis and autonomous execution for an alert.

    This is the main endpoint for triggering the complete autonomous healing flow:
    1. Analyze alert with AI
    2. Create action plan
    3. Execute plan (if execute=True)
    """
    from ..ai_analyzer import analyze_new_alert
    from ..autonomous_executor import create_action_plan, execute_plan, save_plan_to_db

    # Check if alert exists
    alert_query = select(AlertModel).where(AlertModel.alert_id == alert_id)
    alert = db.execute(alert_query).scalar_one_or_none()

    if not alert:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")

    # Perform analysis
    analysis = await analyze_new_alert(db, alert_id)

    if not analysis:
        raise HTTPException(status_code=500, detail="Analysis failed")

    # Create action plan
    plan = await create_action_plan(db, analysis)

    if not plan:
        return {
            "analysis": {
                "alert_id": analysis.alert_id,
                "summary": analysis.summary,
                "root_cause": analysis.root_cause,
                "recommendations": analysis.recommendations,
                "confidence": analysis.confidence,
                "should_execute_autonomously": analysis.should_execute_autonomously,
            },
            "plan": None,
            "message": "Analysis complete, but no action plan created",
        }

    # Save plan to database
    save_plan_to_db(db, plan)

    # Execute if requested and autonomous execution is recommended
    if execute and analysis.should_execute_autonomously:
        await execute_plan(db, plan)
        save_plan_to_db(db, plan)

    return {
        "analysis": {
            "alert_id": analysis.alert_id,
            "summary": analysis.summary,
            "root_cause": analysis.root_cause,
            "recommendations": analysis.recommendations,
            "confidence": analysis.confidence,
            "should_execute_autonomously": analysis.should_execute_autonomously,
            "urgency_score": analysis.urgency_score,
        },
        "plan": plan.to_dict(),
        "executed": execute and analysis.should_execute_autonomously,
    }
