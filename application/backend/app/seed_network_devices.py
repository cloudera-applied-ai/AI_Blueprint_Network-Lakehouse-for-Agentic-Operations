"""Seed network devices (firewalls, switches, routers) linked to headends and hubs."""
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func

from .models import (
    NetworkDeviceModel, ConfigurationTemplateModel,
    HeadendModel, HubModel,
)
from .generator import generate_network_device, generate_config_template

logger = logging.getLogger(__name__)


def seed_network_devices(db: Session) -> int:
    """
    Seed network devices if the table is empty.
    Distribution: per headend (2 firewalls + 4 switches + 2 routers = 8),
                  per hub (2 switches + 1 router = 3).
    Returns the count of devices created.
    """
    existing = db.query(func.count(NetworkDeviceModel.id)).scalar()
    if existing > 0:
        return 0

    logger.info("Seeding network devices...")
    headends = db.query(HeadendModel).all()
    hubs = db.query(HubModel).all()

    if not headends:
        logger.warning("No headends found - skipping network device seeding")
        return 0

    devices = []
    idx = 0

    # Per headend: 2 firewalls + 4 switches + 2 routers
    for he in headends:
        region = he.region or he.service_area or "default"
        for _ in range(2):
            d = generate_network_device("firewall", idx, headend_id=he.headend_id, region=region)
            devices.append(d)
            idx += 1
        for _ in range(4):
            d = generate_network_device("switch", idx, headend_id=he.headend_id, region=region)
            devices.append(d)
            idx += 1
        for _ in range(2):
            d = generate_network_device("router", idx, headend_id=he.headend_id, region=region)
            devices.append(d)
            idx += 1

    # Per hub: 2 switches + 1 router
    for hub in hubs:
        # Find parent headend region
        he = next((h for h in headends if h.headend_id == hub.headend_id), None)
        region = (he.region if he else None) or "default"
        for _ in range(2):
            d = generate_network_device("switch", idx, hub_id=hub.hub_id, region=region)
            devices.append(d)
            idx += 1
        d = generate_network_device("router", idx, hub_id=hub.hub_id, region=region)
        devices.append(d)
        idx += 1

    now = datetime.utcnow()
    for d in devices:
        model = NetworkDeviceModel(
            device_id=d["device_id"],
            device_type=d["device_type"],
            device_role=d["device_role"],
            hostname=d["hostname"],
            description=d["description"],
            headend_id=d.get("headend_id"),
            hub_id=d.get("hub_id"),
            region=d.get("region"),
            manufacturer=d["manufacturer"],
            hardware_model=d["hardware_model"],
            serial_number=d["serial_number"],
            firmware_version=d["firmware_version"],
            os_version=d["os_version"],
            management_ip=d["management_ip"],
            interfaces=d["interfaces"],
            uplink_speed_gbps=d["uplink_speed_gbps"],
            status=d["status"],
            last_seen=now,
            uptime_seconds=d["uptime_seconds"],
            running_config=d["running_config"],
            startup_config=d["startup_config"],
            config_hash=d["config_hash"],
            compliance_status=d["compliance_status"],
            cpu_utilization=d["cpu_utilization"],
            memory_utilization=d["memory_utilization"],
            temperature_celsius=d["temperature_celsius"],
        )
        db.add(model)

    db.flush()
    logger.info(f"Seeded {len(devices)} network devices")

    # Seed config templates
    _seed_config_templates(db)

    db.commit()
    return len(devices)


def _seed_config_templates(db: Session):
    """Seed baseline configuration templates if empty."""
    existing = db.query(func.count(ConfigurationTemplateModel.id)).scalar()
    if existing > 0:
        return

    templates_spec = [
        ("firewall", "perimeter"), ("firewall", "internal"),
        ("switch", "core"), ("switch", "distribution"), ("switch", "access"),
        ("router", "core"), ("router", "edge"),
        ("modem", "access"),
    ]
    for device_type, role in templates_spec:
        t = generate_config_template(device_type, role)
        db.add(ConfigurationTemplateModel(
            template_id=t["template_id"],
            name=t["name"],
            description=t["description"],
            device_type=t["device_type"],
            device_role=t["device_role"],
            config_template=t["config_template"],
            version=t["version"],
            is_active=t["is_active"],
            created_by=t["created_by"],
        ))

    db.flush()
    logger.info(f"Seeded {len(templates_spec)} configuration templates")
