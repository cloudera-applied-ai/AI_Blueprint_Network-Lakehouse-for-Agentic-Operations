"""Slack integration endpoints"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..config import settings
from ..database import get_db

router = APIRouter(prefix=settings.API_V1_STR, tags=["slack"])


@router.get("/slack/status")
def get_slack_status(db: Session = Depends(get_db)):
    """Get Slack integration status"""
    from ..slack_service import slack_service
    slack_service.load_config_from_db(db)
    return slack_service.get_status()


@router.post("/slack/test")
async def test_slack_notification(db: Session = Depends(get_db)):
    """Send a test notification to Slack"""
    from ..slack_service import slack_service
    slack_service.load_config_from_db(db)

    if not slack_service.is_enabled():
        raise HTTPException(status_code=400, detail="Slack not configured. Configure Slack in Settings.")

    success = await slack_service.send_message({
        "text": "Test notification from Cable NOC Dashboard",
        "attachments": [
            {
                "color": "#3b82f6",
                "text": "If you see this message, Slack integration is working correctly!"
            }
        ]
    })

    if success:
        return {"status": "success", "message": "Test notification sent to Slack"}
    else:
        raise HTTPException(status_code=500, detail="Failed to send Slack notification")


@router.post("/slack/notify/alert")
async def send_alert_notification(request: dict, db: Session = Depends(get_db)):
    """Manually send an alert notification to Slack"""
    from ..slack_service import slack_service
    slack_service.load_config_from_db(db)

    if not slack_service.is_enabled():
        raise HTTPException(status_code=400, detail="Slack not configured")

    success = await slack_service.notify_alert(
        node_id=request.get('node_id', 'UNKNOWN'),
        alert_type=request.get('alert_type', 'MANUAL_ALERT'),
        severity=request.get('severity', 'info'),
        description=request.get('description', 'Manual alert notification')
    )

    return {"status": "success" if success else "failed", "sent": success}


@router.post("/slack/notify/action")
async def send_action_notification(request: dict, db: Session = Depends(get_db)):
    """Manually send a self-healing action notification to Slack"""
    from ..slack_service import slack_service
    slack_service.load_config_from_db(db)

    if not slack_service.is_enabled():
        raise HTTPException(status_code=400, detail="Slack not configured")

    success = await slack_service.notify_self_healing_action(
        node_id=request.get('node_id', 'UNKNOWN'),
        action_type=request.get('action_type', 'MANUAL_ACTION'),
        status=request.get('status', 'PENDING'),
        alert_id=request.get('alert_id'),
        effectiveness_score=request.get('effectiveness_score')
    )

    return {"status": "success" if success else "failed", "sent": success}


@router.post("/slack/notify/sdn")
async def send_sdn_notification(request: dict, db: Session = Depends(get_db)):
    """Send an SDN command notification to Slack"""
    from ..slack_service import slack_service
    slack_service.load_config_from_db(db)

    if not slack_service.is_enabled():
        raise HTTPException(status_code=400, detail="Slack not configured")

    success = await slack_service.notify_sdn_command(
        node_id=request.get('node_id', 'UNKNOWN'),
        command_type=request.get('command_type', 'UNKNOWN'),
        parameters=request.get('parameters', {}),
        simulated=request.get('simulated', True)
    )

    return {"status": "success" if success else "failed", "sent": success}
