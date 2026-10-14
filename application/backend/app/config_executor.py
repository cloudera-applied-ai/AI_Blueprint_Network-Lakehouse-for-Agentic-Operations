"""
Config Executor Module - Executes and rolls back configuration change requests.

Follows the autonomous_executor.py pattern: plan execution with audit trail.
"""

import uuid
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

from sqlalchemy.orm import Session

from .models import (
    NetworkDeviceModel, ConfigChangeLogModel, ChangeRequestModel,
)

logger = logging.getLogger(__name__)


def execute_change_request(db: Session, request_id: str) -> Dict[str, Any]:
    """
    Execute a multi-device change request in order.
    Creates ConfigChangeLogModel entries for audit trail.
    Returns execution result dict.
    """
    cr = db.query(ChangeRequestModel).filter(ChangeRequestModel.request_id == request_id).first()
    if not cr:
        return {"status": "error", "message": "Change request not found"}
    if cr.status != "approved":
        return {"status": "error", "message": f"Change request must be approved, current: {cr.status}"}

    cr.status = "executing"
    cr.execution_started_at = datetime.utcnow()
    execution_log = []

    try:
        for target in (cr.target_devices or []):
            device_id = target.get("device_id")
            result = execute_device_change(db, device_id, request_id, target.get("changes"))
            execution_log.append(result)

            if result.get("status") == "failed":
                logger.warning(f"Device change failed for {device_id}: {result.get('reason')}")

        all_ok = all(e.get("status") == "applied" for e in execution_log)
        cr.status = "completed" if all_ok else "failed"
        cr.execution_completed_at = datetime.utcnow()
        cr.execution_log = execution_log
        cr.rollback_available = True
        cr.rollback_deadline = datetime.utcnow() + timedelta(hours=24)

        if not all_ok:
            failed = [e for e in execution_log if e.get("status") != "applied"]
            cr.failure_reason = f"{len(failed)} device(s) failed"

    except Exception as e:
        cr.status = "failed"
        cr.failure_reason = str(e)
        cr.execution_log = execution_log
        logger.error(f"Change request execution error: {e}")

    db.commit()
    return {
        "request_id": request_id,
        "status": cr.status,
        "execution_log": execution_log,
        "completed_at": cr.execution_completed_at.isoformat() if cr.execution_completed_at else None,
    }


def execute_device_change(
    db: Session,
    device_id: str,
    request_id: str,
    changes: Optional[Dict] = None,
) -> Dict[str, Any]:
    """
    Execute a single device configuration change (simulated).
    Creates a ConfigChangeLogModel entry.
    """
    device = db.query(NetworkDeviceModel).filter(NetworkDeviceModel.device_id == device_id).first()
    if not device:
        return {"device_id": device_id, "status": "skipped", "reason": "device not found"}

    old_config = device.running_config or {}
    new_config = dict(old_config)

    # Apply changes (simulated - in production this would push config to device)
    new_config["_last_change_request"] = request_id
    new_config["_change_applied_at"] = datetime.utcnow().isoformat()
    if changes:
        for key, value in changes.items():
            new_config[key] = value

    device.running_config = new_config
    device.last_config_change = datetime.utcnow()
    device.config_hash = uuid.uuid4().hex[:16]

    change_id = f"CHG-{uuid.uuid4().hex[:12].upper()}"
    change_log = ConfigChangeLogModel(
        change_id=change_id,
        device_id=device_id,
        change_request_id=request_id,
        change_type="automated",
        change_description=f"Automated change via request {request_id}",
        config_before=old_config,
        config_after=new_config,
        config_diff={"change_request": request_id, "changes_applied": changes or {}},
        status="applied",
        applied_by="config_executor",
        change_timestamp=datetime.utcnow(),
        rollback_available=True,
        rollback_deadline=datetime.utcnow() + timedelta(hours=24),
    )
    db.add(change_log)
    db.flush()

    return {"device_id": device_id, "status": "applied", "change_id": change_id}


def rollback_change_request(db: Session, request_id: str) -> Dict[str, Any]:
    """
    Roll back all changes from a change request.
    Restores config_before for each device.
    """
    cr = db.query(ChangeRequestModel).filter(ChangeRequestModel.request_id == request_id).first()
    if not cr:
        return {"status": "error", "message": "Change request not found"}
    if not cr.rollback_available:
        return {"status": "error", "message": "Rollback not available"}

    # Find all change log entries for this request
    changes = db.query(ConfigChangeLogModel).filter(
        ConfigChangeLogModel.change_request_id == request_id,
        ConfigChangeLogModel.status == "applied",
    ).all()

    rollback_log = []
    for change in changes:
        device = db.query(NetworkDeviceModel).filter(
            NetworkDeviceModel.device_id == change.device_id
        ).first()

        if device and change.config_before:
            device.running_config = change.config_before
            device.last_config_change = datetime.utcnow()
            device.config_hash = uuid.uuid4().hex[:16]

        change.status = "rolled_back"
        change.rolled_back_at = datetime.utcnow()
        change.rollback_available = False

        # Create rollback audit entry
        rb_log = ConfigChangeLogModel(
            change_id=f"CHG-{uuid.uuid4().hex[:12].upper()}",
            device_id=change.device_id,
            change_request_id=request_id,
            change_type="rollback",
            change_description=f"Rollback of {change.change_id} from request {request_id}",
            config_before=change.config_after,
            config_after=change.config_before,
            status="applied",
            applied_by="rollback_system",
            change_timestamp=datetime.utcnow(),
            rollback_available=False,
        )
        db.add(rb_log)
        rollback_log.append({"device_id": change.device_id, "original_change_id": change.change_id, "status": "rolled_back"})

    cr.status = "rolled_back"
    cr.rollback_available = False
    db.commit()

    return {
        "request_id": request_id,
        "status": "rolled_back",
        "devices_rolled_back": len(rollback_log),
        "rollback_log": rollback_log,
    }
