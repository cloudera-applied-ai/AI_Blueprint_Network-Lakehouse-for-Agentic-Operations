"""Core Network Infrastructure endpoints - Cable/ISP network"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func as sql_func, case, select, literal_column
from typing import Optional
from ..config import settings
from ..database import get_db
from ..models import HeadendModel, CMTSModel, FiberNodeModel, CustomerAccountModel, HubModel, AmplifierModel, NetworkDeviceModel
from . import logger

router = APIRouter(prefix=settings.API_V1_STR, tags=["core-network"])


@router.get("/core-network/summary")
def get_core_network_summary(
    region: Optional[str] = Query(None, description="Filter by region"),
    db: Session = Depends(get_db),
):
    """Get summary statistics for all core network infrastructure"""

    # === Headend counts + health breakdown + regional aggregation (1 query) ===
    headend_q = db.query(
        HeadendModel.region,
        sql_func.count(HeadendModel.id).label('count'),
        sql_func.sum(case((sql_func.lower(sql_func.coalesce(HeadendModel.status, 'operational')) == 'operational', 1), else_=0)).label('operational'),
        sql_func.sum(case((sql_func.lower(sql_func.coalesce(HeadendModel.status, 'operational')) == 'degraded', 1), else_=0)).label('degraded'),
        sql_func.sum(case((sql_func.lower(sql_func.coalesce(HeadendModel.status, 'operational')) == 'maintenance', 1), else_=0)).label('maintenance'),
        sql_func.sum(case((sql_func.lower(sql_func.coalesce(HeadendModel.status, 'operational')) == 'failed', 1), else_=0)).label('failed'),
        sql_func.coalesce(sql_func.sum(HeadendModel.total_homes_served), 0).label('homes'),
        sql_func.coalesce(sql_func.sum(HeadendModel.total_active_subscribers), 0).label('subs'),
    ).group_by(HeadendModel.region)

    if region:
        headend_q = headend_q.filter(HeadendModel.region == region)

    headend_rows = headend_q.all()

    headend_health = {"operational": 0, "degraded": 0, "maintenance": 0, "failed": 0}
    by_region = {}
    total_headends = 0
    total_homes_served = 0
    total_subscribers = 0

    for row in headend_rows:
        reg = row.region or "Unknown"
        total_headends += row.count
        headend_health["operational"] += row.operational
        headend_health["degraded"] += row.degraded
        headend_health["maintenance"] += row.maintenance
        headend_health["failed"] += row.failed
        total_homes_served += row.homes
        total_subscribers += row.subs
        by_region[reg] = {
            "headends": row.count,
            "cmts_devices": 0,
            "total_homes_served": int(row.homes),
            "total_subscribers": int(row.subs),
        }

    # === CMTS health + port/modem totals + regional counts (1 query) ===
    # Use subquery to get headend regions for CMTS devices
    cmts_q = db.query(
        HeadendModel.region,
        sql_func.count(CMTSModel.id).label('count'),
        sql_func.sum(case((sql_func.lower(sql_func.coalesce(CMTSModel.status, 'operational')) == 'operational', 1), else_=0)).label('operational'),
        sql_func.sum(case((sql_func.lower(sql_func.coalesce(CMTSModel.status, 'operational')) == 'degraded', 1), else_=0)).label('degraded'),
        sql_func.sum(case((sql_func.lower(sql_func.coalesce(CMTSModel.status, 'operational')) == 'maintenance', 1), else_=0)).label('maintenance'),
        sql_func.sum(case((sql_func.lower(sql_func.coalesce(CMTSModel.status, 'operational')) == 'failed', 1), else_=0)).label('failed'),
        sql_func.coalesce(sql_func.sum(sql_func.coalesce(CMTSModel.total_ds_ports, 0) + sql_func.coalesce(CMTSModel.total_us_ports, 0)), 0).label('ports'),
        sql_func.coalesce(sql_func.sum(CMTSModel.active_modems), 0).label('modems'),
    ).join(HeadendModel, CMTSModel.headend_id == HeadendModel.headend_id
    ).group_by(HeadendModel.region)

    if region:
        cmts_q = cmts_q.filter(HeadendModel.region == region)

    cmts_rows = cmts_q.all()

    cmts_health = {"operational": 0, "degraded": 0, "maintenance": 0, "failed": 0}
    total_cmts = 0
    total_cmts_ports = 0
    total_active_modems = 0

    for row in cmts_rows:
        reg = row.region or "Unknown"
        total_cmts += row.count
        cmts_health["operational"] += row.operational
        cmts_health["degraded"] += row.degraded
        cmts_health["maintenance"] += row.maintenance
        cmts_health["failed"] += row.failed
        total_cmts_ports += row.ports
        total_active_modems += row.modems
        if reg in by_region:
            by_region[reg]["cmts_devices"] = row.count

    # === Node count (1 query) ===
    node_q = db.query(sql_func.count(FiberNodeModel.id))
    if region:
        node_q = node_q.filter(FiberNodeModel.region == region)
    total_nodes = node_q.scalar() or 0

    # === Active customer count using subquery (1 query, no Python list) ===
    cust_q = db.query(sql_func.count(CustomerAccountModel.id)).filter(
        CustomerAccountModel.account_status == "active"
    )
    if region:
        node_subq = select(FiberNodeModel.node_id).where(FiberNodeModel.region == region).scalar_subquery()
        cust_q = cust_q.filter(CustomerAccountModel.node_id.in_(node_subq))
    total_active_customers = cust_q.scalar() or 0

    # === Hub count (1 query) ===
    hub_q = db.query(sql_func.count(HubModel.id))
    if region:
        headend_subq = select(HeadendModel.headend_id).where(HeadendModel.region == region).scalar_subquery()
        hub_q = hub_q.filter(HubModel.headend_id.in_(headend_subq))
    total_hubs = hub_q.scalar() or 0

    # === Amplifier count (1 query) ===
    amp_q = db.query(sql_func.count(AmplifierModel.id))
    if region:
        node_subq2 = select(FiberNodeModel.node_id).where(FiberNodeModel.region == region).scalar_subquery()
        amp_q = amp_q.filter(AmplifierModel.node_id.in_(node_subq2))
    total_amplifiers = amp_q.scalar() or 0

    # === Network device count (1 query) ===
    netdev_q = db.query(sql_func.count(NetworkDeviceModel.id))
    if region:
        netdev_q = netdev_q.filter(NetworkDeviceModel.region == region)
    total_network_devices = netdev_q.scalar() or 0

    return {
        "total_headends": total_headends,
        "total_cmts": total_cmts,
        "total_nodes": total_nodes,
        "total_hubs": total_hubs,
        "total_amplifiers": total_amplifiers,
        "total_network_devices": total_network_devices,
        "total_active_customers": total_active_customers,
        "total_homes_served": int(total_homes_served),
        "total_subscribers": int(total_subscribers),
        "total_cmts_ports": int(total_cmts_ports),
        "total_active_modems": int(total_active_modems),
        "headend_health": headend_health,
        "cmts_health": cmts_health,
        "by_region": by_region,
    }


@router.get("/core-network/headends")
def get_headends(
    region: Optional[str] = Query(None, description="Filter by region"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """Get all headend facilities (central offices) with infrastructure details"""

    query = db.query(HeadendModel)
    if region:
        query = query.filter(HeadendModel.region == region)

    total = query.count()
    headends = query.order_by(HeadendModel.name).offset(skip).limit(limit).all()

    result = []
    for h in headends:
        port_utilization = 0
        if (h.total_cmts_ports or 0) > 0:
            port_utilization = round(((h.active_cmts_ports or 0) / h.total_cmts_ports) * 100, 1)

        result.append({
            "headend_id": h.headend_id,
            "name": h.name,
            "region": h.region,
            "service_area": h.service_area,
            "city": h.city,
            "state": h.state,
            "latitude": h.latitude,
            "longitude": h.longitude,
            "cmts_count": h.cmts_count or 0,
            "total_cmts_ports": h.total_cmts_ports or 0,
            "active_cmts_ports": h.active_cmts_ports or 0,
            "port_utilization_percent": port_utilization,
            "video_server_count": h.video_server_count or 0,
            "core_router_count": h.core_router_count or 0,
            "peering_capacity_gbps": h.peering_capacity_gbps or 0,
            "total_rack_units": h.total_rack_units or 0,
            "power_capacity_mw": h.power_capacity_mw or 0,
            "total_homes_served": h.total_homes_served or 0,
            "total_active_subscribers": h.total_active_subscribers or 0,
            "status": h.status or "unknown",
        })

    return {
        "total": total,
        "headends": result,
    }


@router.get("/core-network/equipment")
def get_equipment(
    region: Optional[str] = Query(None, description="Filter by region"),
    headend_id: Optional[str] = Query(None, description="Filter by headend"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """Get CMTS equipment with utilization metrics"""

    query = db.query(CMTSModel)

    if headend_id:
        query = query.filter(CMTSModel.headend_id == headend_id)
    elif region:
        # Use subquery instead of loading IDs into Python
        headend_subq = select(HeadendModel.headend_id).where(
            HeadendModel.region == region
        ).scalar_subquery()
        query = query.filter(CMTSModel.headend_id.in_(headend_subq))

    total = query.count()
    devices = query.order_by(CMTSModel.headend_id, CMTSModel.cmts_id).offset(skip).limit(limit).all()

    result = []
    for c in devices:
        modem_utilization = 0
        if (c.max_modems_capacity or 0) > 0:
            modem_utilization = round(((c.active_modems or 0) / c.max_modems_capacity) * 100, 1)

        result.append({
            "cmts_id": c.cmts_id,
            "headend_id": c.headend_id,
            "manufacturer": c.manufacturer,
            "model": c.model,
            "firmware_version": c.firmware_version,
            "total_ds_ports": c.total_ds_ports or 0,
            "total_us_ports": c.total_us_ports or 0,
            "active_modems": c.active_modems or 0,
            "registered_modems": c.registered_modems or 0,
            "offline_modems": c.offline_modems or 0,
            "max_modems_capacity": c.max_modems_capacity or 0,
            "modem_utilization_percent": modem_utilization,
            "avg_ds_utilization": round(c.avg_ds_utilization or 0, 1),
            "avg_us_utilization": round(c.avg_us_utilization or 0, 1),
            "ranging_success_rate": round(c.ranging_success_rate or 0, 1),
            "t3_timeouts_24h": c.t3_timeouts_24h or 0,
            "t4_timeouts_24h": c.t4_timeouts_24h or 0,
            "cpu_utilization": round(c.cpu_utilization or 0, 1),
            "memory_utilization": round(c.memory_utilization or 0, 1),
            "temperature_celsius": round(c.temperature_celsius or 0, 1),
            "uplink_capacity_gbps": round(c.uplink_capacity_gbps or 0, 1),
            "status": c.status or "unknown",
        })

    return {
        "total": total,
        "equipment": result,
    }


@router.get("/core-network/customers/summary")
def get_customers_summary(
    region: Optional[str] = Query(None, description="Filter by region"),
    db: Session = Depends(get_db),
):
    """Get customer summary by service tier, modem status, and connection quality"""

    # Use subquery for region filtering instead of loading node_ids into Python
    base_filter = []
    if region:
        node_subq = select(FiberNodeModel.node_id).where(
            FiberNodeModel.region == region
        ).scalar_subquery()
        base_filter.append(CustomerAccountModel.node_id.in_(node_subq))

    # === Consolidated query 1: Counts by service_plan and account_status (replaces 2 Python loops) ===
    plan_q = db.query(
        CustomerAccountModel.service_plan,
        CustomerAccountModel.account_status,
        sql_func.count(CustomerAccountModel.id).label('cnt'),
    )
    for f in base_filter:
        plan_q = plan_q.filter(f)
    plan_rows = plan_q.group_by(
        CustomerAccountModel.service_plan,
        CustomerAccountModel.account_status,
    ).all()

    by_plan = {}
    total_customers = 0
    total_active = 0
    for row in plan_rows:
        plan = row.service_plan or "Unknown"
        if plan not in by_plan:
            by_plan[plan] = {"total": 0, "active": 0, "suspended": 0}
        by_plan[plan]["total"] += row.cnt
        total_customers += row.cnt
        status = (row.account_status or "").lower()
        if status == "active":
            by_plan[plan]["active"] += row.cnt
            total_active += row.cnt
        elif status == "suspended":
            by_plan[plan]["suspended"] += row.cnt

    # === Consolidated query 2: Counts by DOCSIS version ===
    docsis_q = db.query(
        sql_func.coalesce(CustomerAccountModel.docsis_version, 'Unknown').label('version'),
        sql_func.count(CustomerAccountModel.id).label('cnt'),
    )
    for f in base_filter:
        docsis_q = docsis_q.filter(f)
    docsis_rows = docsis_q.group_by('version').all()
    by_docsis = {row.version: row.cnt for row in docsis_rows}

    # === Consolidated query 3: Connection quality metrics ===
    quality_q = db.query(
        sql_func.sum(case((CustomerAccountModel.connection_drops_24h > 5, 1), else_=0)).label('high_drops'),
        sql_func.sum(case(
            (
                (CustomerAccountModel.actual_download_mbps != None) &
                (CustomerAccountModel.provisioned_download_mbps != None) &
                (CustomerAccountModel.actual_download_mbps >= CustomerAccountModel.provisioned_download_mbps * 0.8),
                1
            ),
            else_=0
        )).label('meeting'),
        sql_func.sum(case(
            (
                (CustomerAccountModel.actual_download_mbps != None) &
                (CustomerAccountModel.provisioned_download_mbps != None) &
                (CustomerAccountModel.actual_download_mbps < CustomerAccountModel.provisioned_download_mbps * 0.8),
                1
            ),
            else_=0
        )).label('below'),
    )
    for f in base_filter:
        quality_q = quality_q.filter(f)
    quality = quality_q.one()

    return {
        "total_customers": total_customers,
        "total_active": total_active,
        "by_service_plan": by_plan,
        "by_docsis_version": by_docsis,
        "connection_quality": {
            "high_drop_customers": int(quality.high_drops or 0),
            "meeting_speed_threshold": int(quality.meeting or 0),
            "below_speed_threshold": int(quality.below or 0),
        },
    }


@router.get("/core-network/hubs")
def get_hubs(
    region: Optional[str] = Query(None, description="Filter by region"),
    headend_id: Optional[str] = Query(None, description="Filter by headend"),
    skip: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """Get all hub sites with capacity and status details"""

    query = db.query(HubModel)

    if headend_id:
        query = query.filter(HubModel.headend_id == headend_id)
    elif region:
        # Use subquery instead of loading IDs into Python
        headend_subq = select(HeadendModel.headend_id).where(
            HeadendModel.region == region
        ).scalar_subquery()
        query = query.filter(HubModel.headend_id.in_(headend_subq))

    total = query.count()
    hubs = query.order_by(HubModel.name).offset(skip).limit(limit).all()

    result = []
    for h in hubs:
        utilization = 0
        if (h.fiber_capacity_gbps or 0) > 0:
            utilization = round(((h.current_throughput_gbps or 0) / h.fiber_capacity_gbps) * 100, 1)

        result.append({
            "hub_id": h.hub_id,
            "headend_id": h.headend_id,
            "name": h.name,
            "city": h.city,
            "state": h.state,
            "latitude": h.latitude,
            "longitude": h.longitude,
            "fiber_nodes_served": h.fiber_nodes_served or 0,
            "total_homes_served": h.total_homes_served or 0,
            "fiber_capacity_gbps": round(h.fiber_capacity_gbps or 0, 1),
            "current_throughput_gbps": round(h.current_throughput_gbps or 0, 1),
            "utilization_percent": utilization,
            "power_status": h.power_status or "normal",
            "battery_backup_hours": round(h.battery_backup_hours or 0, 1),
            "status": h.status or "unknown",
        })

    return {
        "total": total,
        "hubs": result,
    }


@router.get("/core-network/amplifiers")
def get_amplifiers(
    node_id: Optional[str] = Query(None, description="Filter by fiber node"),
    region: Optional[str] = Query(None, description="Filter by region"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """Get amplifiers with RF level and status details"""

    query = db.query(AmplifierModel)

    if node_id:
        query = query.filter(AmplifierModel.node_id == node_id)
    elif region:
        node_subq = select(FiberNodeModel.node_id).where(
            FiberNodeModel.region == region
        ).scalar_subquery()
        query = query.filter(AmplifierModel.node_id.in_(node_subq))

    total = query.count()
    amps = query.order_by(AmplifierModel.node_id, AmplifierModel.amp_id).offset(skip).limit(limit).all()

    result = []
    for a in amps:
        result.append({
            "amp_id": a.amp_id,
            "node_id": a.node_id,
            "manufacturer": a.manufacturer,
            "model": a.model,
            "amp_type": a.amp_type,
            "cascade_position": a.cascade_position,
            "location_type": a.location_type,
            "ds_input_level": round(a.ds_input_level or 0, 1),
            "ds_output_level": round(a.ds_output_level or 0, 1),
            "us_input_level": round(a.us_input_level or 0, 1),
            "us_output_level": round(a.us_output_level or 0, 1),
            "ds_snr": round(a.ds_snr or 0, 1),
            "us_snr": round(a.us_snr or 0, 1),
            "temperature_celsius": round(a.temperature_celsius or 0, 1),
            "power_consumption_watts": round(a.power_consumption_watts or 0, 1),
            "power_supply_status": a.power_supply_status or "unknown",
            "status": a.status or "unknown",
        })

    return {"total": total, "amplifiers": result}


@router.get("/core-network/network-devices")
def get_network_devices(
    device_type: Optional[str] = Query(None, description="Filter by type: firewall, switch, router"),
    headend_id: Optional[str] = Query(None),
    hub_id: Optional[str] = Query(None),
    region: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """Get network devices (firewalls, switches, routers) with status and utilization"""

    query = db.query(NetworkDeviceModel)

    if device_type:
        query = query.filter(NetworkDeviceModel.device_type == device_type)
    if headend_id:
        query = query.filter(NetworkDeviceModel.headend_id == headend_id)
    if hub_id:
        query = query.filter(NetworkDeviceModel.hub_id == hub_id)
    if region:
        query = query.filter(NetworkDeviceModel.region == region)

    total = query.count()
    devices = query.order_by(NetworkDeviceModel.device_type, NetworkDeviceModel.hostname).offset(skip).limit(limit).all()

    result = []
    for d in devices:
        result.append({
            "device_id": d.device_id,
            "device_type": d.device_type,
            "device_role": d.device_role,
            "hostname": d.hostname,
            "headend_id": d.headend_id,
            "hub_id": d.hub_id,
            "region": d.region,
            "manufacturer": d.manufacturer,
            "hardware_model": d.hardware_model,
            "firmware_version": d.firmware_version,
            "management_ip": d.management_ip,
            "uplink_speed_gbps": round(d.uplink_speed_gbps or 0, 1),
            "status": d.status or "unknown",
            "compliance_status": d.compliance_status or "unknown",
            "cpu_utilization": round(d.cpu_utilization or 0, 1),
            "memory_utilization": round(d.memory_utilization or 0, 1),
            "temperature_celsius": round(d.temperature_celsius or 0, 1),
        })

    return {"total": total, "devices": result}


@router.get("/core-network/all")
def get_all_core_network(
    region: Optional[str] = Query(None, description="Filter by region"),
    db: Session = Depends(get_db),
):
    """Get all core network data in one call"""
    return {
        "summary": get_core_network_summary(region, db=db),
        "headends": get_headends(region, db=db),
        "hubs": get_hubs(region, db=db),
        "equipment": get_equipment(region, db=db),
        "customers": get_customers_summary(region, db=db),
    }
