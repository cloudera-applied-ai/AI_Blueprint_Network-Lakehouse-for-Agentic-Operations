"""Configuration Management endpoints for network devices"""
import uuid
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func as sql_func, case
from typing import Optional

from ..config import settings
from ..database import get_db
from ..models import (
    NetworkDeviceModel, ConfigurationTemplateModel,
    ConfigChangeLogModel, ConfigComplianceModel, ChangeRequestModel,
)
from . import logger

router = APIRouter(prefix=settings.API_V1_STR, tags=["config-management"])


# ===== DEVICE ENDPOINTS =====

@router.get("/config/devices/summary")
def get_device_summary(db: Session = Depends(get_db)):
    """Dashboard summary: device counts by type, compliance %, drift count, recent changes"""
    # Consolidated query: counts by type + status + compliance in one pass
    rows = db.query(
        NetworkDeviceModel.device_type,
        NetworkDeviceModel.status,
        NetworkDeviceModel.compliance_status,
        sql_func.count(NetworkDeviceModel.id).label('cnt'),
    ).group_by(
        NetworkDeviceModel.device_type,
        NetworkDeviceModel.status,
        NetworkDeviceModel.compliance_status,
    ).all()

    total = 0
    by_type = {}
    by_status = {}
    compliant_count = 0
    drift_count = 0

    for row in rows:
        total += row.cnt
        by_type[row.device_type] = by_type.get(row.device_type, 0) + row.cnt
        by_status[row.status or "unknown"] = by_status.get(row.status or "unknown", 0) + row.cnt
        if row.compliance_status == "compliant":
            compliant_count += row.cnt
        elif row.compliance_status == "drifted":
            drift_count += row.cnt

    compliance_rate = round((compliant_count / total * 100), 1) if total > 0 else 100.0

    # Recent changes (last 24h)
    cutoff = datetime.utcnow() - timedelta(hours=24)
    recent_changes = db.query(sql_func.count(ConfigChangeLogModel.id)).filter(
        ConfigChangeLogModel.change_timestamp >= cutoff
    ).scalar() or 0

    return {
        "total_devices": total,
        "by_type": by_type,
        "by_status": by_status,
        "compliance_rate": compliance_rate,
        "drift_count": drift_count,
        "recent_changes": recent_changes,
    }


@router.get("/config/devices")
def list_devices(
    device_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    headend_id: Optional[str] = Query(None),
    hub_id: Optional[str] = Query(None),
    region: Optional[str] = Query(None),
    compliance_status: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """List devices with filters and pagination"""
    query = db.query(NetworkDeviceModel)
    if device_type:
        query = query.filter(NetworkDeviceModel.device_type == device_type)
    if status:
        query = query.filter(NetworkDeviceModel.status == status)
    if headend_id:
        query = query.filter(NetworkDeviceModel.headend_id == headend_id)
    if hub_id:
        query = query.filter(NetworkDeviceModel.hub_id == hub_id)
    if region:
        query = query.filter(NetworkDeviceModel.region == region)
    if compliance_status:
        query = query.filter(NetworkDeviceModel.compliance_status == compliance_status)

    total = query.count()
    devices = query.order_by(NetworkDeviceModel.device_type, NetworkDeviceModel.hostname).offset(skip).limit(limit).all()

    return {
        "total": total,
        "devices": [_device_to_dict(d) for d in devices],
    }


@router.get("/config/devices/{device_id}")
def get_device_detail(device_id: str, db: Session = Depends(get_db)):
    """Device detail with config, compliance history, and change log"""
    device = db.query(NetworkDeviceModel).filter(NetworkDeviceModel.device_id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    # Recent changes for this device
    changes = db.query(ConfigChangeLogModel).filter(
        ConfigChangeLogModel.device_id == device_id
    ).order_by(ConfigChangeLogModel.change_timestamp.desc()).limit(10).all()

    # Latest compliance record
    compliance = db.query(ConfigComplianceModel).filter(
        ConfigComplianceModel.device_id == device_id
    ).order_by(ConfigComplianceModel.scan_timestamp.desc()).limit(5).all()

    return {
        "device": _device_to_dict(device),
        "recent_changes": [_change_to_dict(c) for c in changes],
        "compliance_history": [_compliance_to_dict(c) for c in compliance],
    }


@router.post("/config/devices/{device_id}/sync")
def sync_device_config(device_id: str, db: Session = Depends(get_db)):
    """Trigger config sync (simulated) - copies running_config to startup_config"""
    device = db.query(NetworkDeviceModel).filter(NetworkDeviceModel.device_id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    device.startup_config = device.running_config
    device.last_config_backup = datetime.utcnow()
    db.commit()

    return {"status": "synced", "device_id": device_id, "synced_at": datetime.utcnow().isoformat()}


# ===== TEMPLATE ENDPOINTS =====

@router.get("/config/templates")
def list_templates(
    device_type: Optional[str] = Query(None),
    device_role: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """List configuration templates"""
    query = db.query(ConfigurationTemplateModel).filter(ConfigurationTemplateModel.is_active == True)
    if device_type:
        query = query.filter(ConfigurationTemplateModel.device_type == device_type)
    if device_role:
        query = query.filter(ConfigurationTemplateModel.device_role == device_role)

    templates = query.order_by(ConfigurationTemplateModel.device_type, ConfigurationTemplateModel.name).all()

    return {
        "total": len(templates),
        "templates": [
            {
                "template_id": t.template_id,
                "name": t.name,
                "description": t.description,
                "device_type": t.device_type,
                "device_role": t.device_role,
                "config_template": t.config_template,
                "version": t.version,
                "is_active": t.is_active,
                "created_by": t.created_by,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in templates
        ],
    }


@router.post("/config/templates")
def create_template(
    name: str = Query(...),
    device_type: str = Query(...),
    device_role: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Create a new configuration template"""
    from ..generator import generate_config_template
    t = generate_config_template(device_type, device_role or "access")
    t["name"] = name

    model = ConfigurationTemplateModel(
        template_id=t["template_id"],
        name=t["name"],
        description=t["description"],
        device_type=t["device_type"],
        device_role=t["device_role"],
        config_template=t["config_template"],
        version=t["version"],
        is_active=True,
        created_by="api",
    )
    db.add(model)
    db.commit()
    db.refresh(model)

    return {"template_id": model.template_id, "name": model.name, "created": True}


# ===== CHANGE LOG ENDPOINTS =====

@router.get("/config/changes")
def list_changes(
    device_id: Optional[str] = Query(None),
    change_type: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """List configuration change log with filters"""
    query = db.query(ConfigChangeLogModel)
    if device_id:
        query = query.filter(ConfigChangeLogModel.device_id == device_id)
    if change_type:
        query = query.filter(ConfigChangeLogModel.change_type == change_type)

    total = query.count()
    changes = query.order_by(ConfigChangeLogModel.change_timestamp.desc()).offset(skip).limit(limit).all()

    return {
        "total": total,
        "changes": [_change_to_dict(c) for c in changes],
    }


@router.post("/config/changes/{change_id}/rollback")
def rollback_change(change_id: str, db: Session = Depends(get_db)):
    """Rollback a configuration change"""
    change = db.query(ConfigChangeLogModel).filter(ConfigChangeLogModel.change_id == change_id).first()
    if not change:
        raise HTTPException(status_code=404, detail="Change not found")
    if not change.rollback_available:
        raise HTTPException(status_code=400, detail="Rollback not available for this change")
    if change.status == "rolled_back":
        raise HTTPException(status_code=400, detail="Change already rolled back")

    # Restore config_before on the device
    device = db.query(NetworkDeviceModel).filter(NetworkDeviceModel.device_id == change.device_id).first()
    if device and change.config_before:
        device.running_config = change.config_before
        device.last_config_change = datetime.utcnow()

    change.status = "rolled_back"
    change.rolled_back_at = datetime.utcnow()
    change.rollback_available = False

    # Create rollback log entry
    rollback_log = ConfigChangeLogModel(
        change_id=f"CHG-{uuid.uuid4().hex[:12].upper()}",
        device_id=change.device_id,
        change_request_id=change.change_request_id,
        change_type="rollback",
        change_description=f"Rollback of change {change_id}",
        config_before=change.config_after,
        config_after=change.config_before,
        status="applied",
        applied_by="rollback_system",
        change_timestamp=datetime.utcnow(),
        rollback_available=False,
    )
    db.add(rollback_log)
    db.commit()

    return {"status": "rolled_back", "change_id": change_id, "rolled_back_at": change.rolled_back_at.isoformat()}


# ===== COMPLIANCE ENDPOINTS =====

@router.get("/config/compliance/summary")
def get_compliance_summary(db: Session = Depends(get_db)):
    """Compliance overview by device type"""
    rows = db.query(
        NetworkDeviceModel.device_type,
        NetworkDeviceModel.compliance_status,
        sql_func.count(NetworkDeviceModel.id).label('cnt'),
    ).group_by(
        NetworkDeviceModel.device_type,
        NetworkDeviceModel.compliance_status,
    ).all()

    by_type = {}
    totals = {"compliant": 0, "drifted": 0, "non_compliant": 0, "unknown": 0}

    for row in rows:
        dt = row.device_type
        cs = row.compliance_status or "unknown"
        if dt not in by_type:
            by_type[dt] = {"compliant": 0, "drifted": 0, "non_compliant": 0, "unknown": 0, "total": 0}
        by_type[dt][cs] = by_type[dt].get(cs, 0) + row.cnt
        by_type[dt]["total"] += row.cnt
        totals[cs] = totals.get(cs, 0) + row.cnt

    total_devices = sum(totals.values())
    overall_rate = round((totals["compliant"] / total_devices * 100), 1) if total_devices > 0 else 100.0

    return {
        "overall_compliance_rate": overall_rate,
        "totals": totals,
        "by_device_type": by_type,
    }


@router.post("/config/compliance/scan")
def trigger_compliance_scan(db: Session = Depends(get_db)):
    """Trigger a compliance scan across all devices (simulated)"""
    import random

    devices = db.query(NetworkDeviceModel).all()
    scan_time = datetime.utcnow()
    scanned = 0

    for device in devices:
        # Simulate drift detection
        is_drifted = random.random() < 0.12  # ~12% drift rate
        status = "drifted" if is_drifted else "compliant"
        severity = random.choice(["low", "medium", "high"]) if is_drifted else "low"

        drift_details = None
        drift_count = 0
        if is_drifted:
            drift_count = random.randint(1, 5)
            drift_details = [
                {"field": random.choice(["acl_rules", "vlans", "routing", "qos", "security_zones"]),
                 "expected": "baseline_value", "actual": "current_value"}
                for _ in range(drift_count)
            ]

        device.compliance_status = status
        device.last_compliance_scan = scan_time

        record = ConfigComplianceModel(
            compliance_id=f"CMP-{uuid.uuid4().hex[:12].upper()}",
            device_id=device.device_id,
            compliance_status=status,
            severity=severity,
            drift_details=drift_details,
            drift_count=drift_count,
            scan_timestamp=scan_time,
        )
        db.add(record)
        scanned += 1

    db.commit()
    drifted = sum(1 for d in devices if d.compliance_status == "drifted")

    return {
        "status": "completed",
        "devices_scanned": scanned,
        "drifted_count": drifted,
        "scan_timestamp": scan_time.isoformat(),
    }


# ===== CHANGE REQUEST ENDPOINTS =====

@router.get("/config/change-requests")
def list_change_requests(
    status: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """List change requests"""
    query = db.query(ChangeRequestModel)
    if status:
        query = query.filter(ChangeRequestModel.status == status)

    total = query.count()
    requests = query.order_by(ChangeRequestModel.created_at.desc()).offset(skip).limit(limit).all()

    return {
        "total": total,
        "requests": [_request_to_dict(r) for r in requests],
    }


@router.post("/config/change-requests")
def create_change_request(
    title: str = Query(...),
    description: Optional[str] = Query(None),
    change_type: str = Query("maintenance"),
    device_ids: str = Query(..., description="Comma-separated device IDs"),
    requested_by: Optional[str] = Query("api_user"),
    db: Session = Depends(get_db),
):
    """Create a new change request"""
    device_id_list = [d.strip() for d in device_ids.split(",") if d.strip()]

    # Verify all devices exist
    devices = db.query(NetworkDeviceModel).filter(
        NetworkDeviceModel.device_id.in_(device_id_list)
    ).all()

    if len(devices) != len(device_id_list):
        found = {d.device_id for d in devices}
        missing = [d for d in device_id_list if d not in found]
        raise HTTPException(status_code=404, detail=f"Devices not found: {missing}")

    target_devices = [{"device_id": d.device_id, "device_type": d.device_type, "hostname": d.hostname} for d in devices]

    request_model = ChangeRequestModel(
        request_id=f"CR-{uuid.uuid4().hex[:12].upper()}",
        title=title,
        description=description,
        change_type=change_type,
        target_devices=target_devices,
        device_count=len(target_devices),
        status="pending_review",
        requested_by=requested_by,
    )
    db.add(request_model)
    db.commit()
    db.refresh(request_model)

    return {"request_id": request_model.request_id, "status": "pending_review", "device_count": len(target_devices)}


@router.put("/config/change-requests/{request_id}")
def update_change_request(
    request_id: str,
    status: Optional[str] = Query(None),
    reviewed_by: Optional[str] = Query(None),
    approved_by: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Update a change request (approve/reject/cancel)"""
    cr = db.query(ChangeRequestModel).filter(ChangeRequestModel.request_id == request_id).first()
    if not cr:
        raise HTTPException(status_code=404, detail="Change request not found")

    if status:
        valid_transitions = {
            "pending_review": ["approved", "rejected", "cancelled"],
            "approved": ["executing", "cancelled"],
            "executing": ["completed", "failed"],
            "failed": ["rolled_back"],
        }
        allowed = valid_transitions.get(cr.status, [])
        if status not in allowed:
            raise HTTPException(status_code=400, detail=f"Cannot transition from '{cr.status}' to '{status}'")
        cr.status = status
        if status == "approved":
            cr.approved_at = datetime.utcnow()

    if reviewed_by:
        cr.reviewed_by = reviewed_by
    if approved_by:
        cr.approved_by = approved_by

    db.commit()

    return {"request_id": request_id, "status": cr.status}


@router.post("/config/change-requests/{request_id}/execute")
def execute_change_request(request_id: str, db: Session = Depends(get_db)):
    """Execute an approved change request (simulated)"""
    cr = db.query(ChangeRequestModel).filter(ChangeRequestModel.request_id == request_id).first()
    if not cr:
        raise HTTPException(status_code=404, detail="Change request not found")
    if cr.status != "approved":
        raise HTTPException(status_code=400, detail=f"Change request must be approved, current status: {cr.status}")

    cr.status = "executing"
    cr.execution_started_at = datetime.utcnow()
    execution_log = []

    try:
        for target in (cr.target_devices or []):
            device_id = target["device_id"]
            device = db.query(NetworkDeviceModel).filter(NetworkDeviceModel.device_id == device_id).first()
            if not device:
                execution_log.append({"device_id": device_id, "status": "skipped", "reason": "not found"})
                continue

            # Simulate config change
            old_config = device.running_config or {}
            new_config = dict(old_config)
            new_config["_last_change_request"] = request_id
            new_config["_change_applied_at"] = datetime.utcnow().isoformat()

            device.running_config = new_config
            device.last_config_change = datetime.utcnow()

            # Create change log entry
            change_log = ConfigChangeLogModel(
                change_id=f"CHG-{uuid.uuid4().hex[:12].upper()}",
                device_id=device_id,
                change_request_id=request_id,
                change_type="automated",
                change_description=f"Executed via change request {request_id}",
                config_before=old_config,
                config_after=new_config,
                config_diff={"change_request": request_id},
                status="applied",
                applied_by="config_executor",
                change_timestamp=datetime.utcnow(),
                rollback_available=True,
                rollback_deadline=datetime.utcnow() + timedelta(hours=24),
            )
            db.add(change_log)
            execution_log.append({"device_id": device_id, "status": "applied", "change_id": change_log.change_id})

        cr.status = "completed"
        cr.execution_completed_at = datetime.utcnow()
        cr.execution_log = execution_log
        cr.rollback_available = True
        cr.rollback_deadline = datetime.utcnow() + timedelta(hours=24)

    except Exception as e:
        cr.status = "failed"
        cr.failure_reason = str(e)
        cr.execution_log = execution_log

    db.commit()

    return {"request_id": request_id, "status": cr.status, "execution_log": execution_log}


# ===== HELPERS =====

def _device_to_dict(d: NetworkDeviceModel) -> dict:
    return {
        "id": d.id,
        "device_id": d.device_id,
        "device_type": d.device_type,
        "device_role": d.device_role,
        "hostname": d.hostname,
        "description": d.description,
        "headend_id": d.headend_id,
        "hub_id": d.hub_id,
        "region": d.region,
        "manufacturer": d.manufacturer,
        "hardware_model": d.hardware_model,
        "serial_number": d.serial_number,
        "firmware_version": d.firmware_version,
        "os_version": d.os_version,
        "management_ip": d.management_ip,
        "interfaces": d.interfaces,
        "uplink_speed_gbps": d.uplink_speed_gbps,
        "status": d.status,
        "last_seen": d.last_seen.isoformat() if d.last_seen else None,
        "uptime_seconds": d.uptime_seconds,
        "running_config": d.running_config,
        "config_hash": d.config_hash,
        "compliance_status": d.compliance_status,
        "last_compliance_scan": d.last_compliance_scan.isoformat() if d.last_compliance_scan else None,
        "last_config_change": d.last_config_change.isoformat() if d.last_config_change else None,
        "cpu_utilization": d.cpu_utilization,
        "memory_utilization": d.memory_utilization,
        "temperature_celsius": d.temperature_celsius,
        "created_at": d.created_at.isoformat() if d.created_at else None,
    }


def _change_to_dict(c: ConfigChangeLogModel) -> dict:
    return {
        "change_id": c.change_id,
        "device_id": c.device_id,
        "change_request_id": c.change_request_id,
        "change_type": c.change_type,
        "change_description": c.change_description,
        "config_diff": c.config_diff,
        "status": c.status,
        "applied_by": c.applied_by,
        "change_timestamp": c.change_timestamp.isoformat() if c.change_timestamp else None,
        "rollback_available": c.rollback_available,
        "rollback_deadline": c.rollback_deadline.isoformat() if c.rollback_deadline else None,
        "rolled_back_at": c.rolled_back_at.isoformat() if c.rolled_back_at else None,
    }


def _compliance_to_dict(c: ConfigComplianceModel) -> dict:
    return {
        "compliance_id": c.compliance_id,
        "device_id": c.device_id,
        "compliance_status": c.compliance_status,
        "severity": c.severity,
        "drift_details": c.drift_details,
        "drift_count": c.drift_count,
        "scan_timestamp": c.scan_timestamp.isoformat() if c.scan_timestamp else None,
        "resolved_at": c.resolved_at.isoformat() if c.resolved_at else None,
    }


def _request_to_dict(r: ChangeRequestModel) -> dict:
    return {
        "request_id": r.request_id,
        "title": r.title,
        "description": r.description,
        "change_type": r.change_type,
        "target_devices": r.target_devices,
        "device_count": r.device_count,
        "ai_risk_assessment": r.ai_risk_assessment,
        "ai_impact_score": r.ai_impact_score,
        "ai_recommendation": r.ai_recommendation,
        "status": r.status,
        "requested_by": r.requested_by,
        "reviewed_by": r.reviewed_by,
        "approved_by": r.approved_by,
        "approved_at": r.approved_at.isoformat() if r.approved_at else None,
        "execution_started_at": r.execution_started_at.isoformat() if r.execution_started_at else None,
        "execution_completed_at": r.execution_completed_at.isoformat() if r.execution_completed_at else None,
        "execution_log": r.execution_log,
        "failure_reason": r.failure_reason,
        "rollback_available": r.rollback_available,
        "rollback_deadline": r.rollback_deadline.isoformat() if r.rollback_deadline else None,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }
