"""Data generator for Cable Network ISP simulation"""
import math
import random
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from . import constants as const
from .config import settings


def random_int(min_val: int, max_val: int) -> int:
    return random.randint(min_val, max_val)


def random_float(min_val: float, max_val: float, decimals: int = 2) -> float:
    return round(random.uniform(min_val, max_val), decimals)


def random_choice(choices: list):
    return random.choice(choices)


def weighted_choice(choices: Dict[str, float]) -> str:
    population = list(choices.keys())
    weights = list(choices.values())
    return random.choices(population, weights=weights, k=1)[0]


# ============================================
# Infrastructure Generators
# ============================================

def _area_offset(config: Dict, spread: float) -> Tuple[float, float]:
    """Generate a random offset scaled to a fraction of the service area bounds."""
    lat_bounds = config.get("lat_bounds", [0, 0])
    lng_bounds = config.get("lng_bounds", [0, 0])
    lat_range = (lat_bounds[1] - lat_bounds[0]) * spread
    lng_range = (lng_bounds[1] - lng_bounds[0]) * spread
    return (random.uniform(-lat_range, lat_range),
            random.uniform(-lng_range, lng_range))


def _clamp_to_bounds(lat: float, lng: float, config: Dict) -> Tuple[float, float]:
    """Clamp coordinates to stay within service area bounds."""
    lat_bounds = config.get("lat_bounds")
    lng_bounds = config.get("lng_bounds")
    if lat_bounds:
        lat = max(lat_bounds[0], min(lat_bounds[1], lat))
    if lng_bounds:
        lng = max(lng_bounds[0], min(lng_bounds[1], lng))
    return lat, lng


def generate_headend(headend_index: int, service_area: str, config: Dict) -> Dict:
    """Generate a headend facility"""
    headend_id = f"HE-{service_area[:3].upper()}-{headend_index:02d}"
    # Cycle through cities so multiple headends aren't stacked on the same spot
    city = config["cities"][headend_index % len(config["cities"])]
    coords = const.CITY_COORDINATES.get(city, (0, 0))
    cmts_count = random_int(8, 20)
    homes = random_int(40000, 120000)
    dlat, dlng = _area_offset(config, 0.05)
    lat, lng = _clamp_to_bounds(coords[0] + dlat, coords[1] + dlng, config)
    return {
        "headend_id": headend_id,
        "name": f"{city} Headend {headend_index + 1}",
        "region": service_area,
        "service_area": service_area,
        "city": city,
        "state": config["state"],
        "latitude": round(lat, 6),
        "longitude": round(lng, 6),
        "cmts_count": cmts_count,
        "total_cmts_ports": cmts_count * random_int(48, 96),
        "active_cmts_ports": cmts_count * random_int(30, 80),
        "video_server_count": random_int(4, 12),
        "core_router_count": random_int(2, 6),
        "peering_capacity_gbps": random_float(100, 400, 0),
        "total_rack_units": random_int(200, 600),
        "power_capacity_mw": random_float(0.5, 2.0, 1),
        "total_homes_served": homes,
        "total_active_subscribers": int(homes * random.uniform(0.55, 0.75)),
        "status": "operational",
    }


def generate_hub(hub_index: int, headend_id: str, service_area: str, config: Dict) -> Dict:
    """Generate a hub site"""
    hub_id = f"HUB-{service_area[:3].upper()}-{hub_index:02d}"
    # Distribute hubs across cities evenly
    city = config["cities"][hub_index % len(config["cities"])]
    coords = const.CITY_COORDINATES.get(city, (0, 0))
    nodes = settings.NODES_PER_HUB or config.get("nodes_per_hub", 40)
    homes = nodes * random_int(200, 400)
    dlat, dlng = _area_offset(config, 0.15)
    lat, lng = _clamp_to_bounds(coords[0] + dlat, coords[1] + dlng, config)
    return {
        "hub_id": hub_id,
        "headend_id": headend_id,
        "name": f"{city} Hub {hub_index + 1}",
        "city": city,
        "state": config["state"],
        "latitude": round(lat, 6),
        "longitude": round(lng, 6),
        "fiber_nodes_served": nodes,
        "total_homes_served": homes,
        "fiber_capacity_gbps": random_float(40, 100, 0),
        "current_throughput_gbps": random_float(15, 60, 1),
        "power_status": weighted_choice({"normal": 0.90, "battery": 0.05, "generator": 0.05}),
        "battery_backup_hours": random_float(4, 12, 1),
        "status": weighted_choice({"operational": 0.92, "degraded": 0.06, "maintenance": 0.02}),
    }


def generate_cmts(cmts_index: int, headend_id: str) -> Dict:
    """Generate a CMTS device"""
    cmts_id = f"CMTS-{headend_id.split('-')[1]}-{cmts_index:02d}"
    mfr = weighted_choice({"Cisco": 0.50, "Casa": 0.30, "Harmonic": 0.20})
    model = random_choice(const.CMTS_MANUFACTURERS[mfr])
    max_modems = random_int(8000, 16000)
    active = int(max_modems * random.uniform(0.5, 0.85))
    offline = int(active * random.uniform(0.01, 0.05))
    return {
        "cmts_id": cmts_id,
        "headend_id": headend_id,
        "manufacturer": mfr,
        "model": model,
        "firmware_version": f"{random_int(1, 5)}.{random_int(0, 20)}.{random_int(0, 99)}",
        "total_ds_ports": random_int(48, 96),
        "total_us_ports": random_int(24, 48),
        "active_modems": active,
        "registered_modems": active + random_int(100, 500),
        "offline_modems": offline,
        "max_modems_capacity": max_modems,
        "avg_ds_utilization": random_float(30, 75, 1),
        "avg_us_utilization": random_float(20, 65, 1),
        "ranging_success_rate": random_float(95, 99.9, 2),
        "t3_timeouts_24h": random_int(0, 200),
        "t4_timeouts_24h": random_int(0, 50),
        "cpu_utilization": random_float(20, 70, 1),
        "memory_utilization": random_float(30, 75, 1),
        "temperature_celsius": random_float(30, 55, 1),
        "uplink_capacity_gbps": random_float(10, 100, 0),
        "status": weighted_choice({"operational": 0.92, "degraded": 0.06, "maintenance": 0.02}),
    }


def generate_fiber_node(node_index: int, service_area: str, headend_id: str, hub_id: str,
                        cmts_id: str, config: Dict) -> Dict:
    """Generate a fiber node"""
    area_code = service_area[:3].upper()
    node_id = f"NODE-{area_code}-{node_index:04d}"
    node_type = weighted_choice(const.NODE_TYPE_DISTRIBUTION)
    type_cfg = const.NODE_TYPE_CONFIG[node_type]
    hp_range = type_cfg["homes_passed_range"]
    homes_passed = random_int(hp_range[0], hp_range[1])
    homes_active = int(homes_passed * random.uniform(0.60, 0.90))
    docsis = weighted_choice(const.DOCSIS_VERSION_DISTRIBUTION)
    ch_cfg = const.DOCSIS_CHANNEL_CONFIGS[docsis]
    city = random_choice(config["cities"])
    coords = const.CITY_COORDINATES.get(city, (0, 0))
    mfr = random_choice(list(const.NODE_MANUFACTURERS.keys()))
    model = random_choice(const.NODE_MANUFACTURERS[mfr])

    # Two-tier spread: 70% urban (±20% of area), 30% suburban/rural (±45% of area)
    spread = 0.20 if random.random() < 0.7 else 0.45
    dlat, dlng = _area_offset(config, spread)
    lat, lng = _clamp_to_bounds(coords[0] + dlat, coords[1] + dlng, config)

    return {
        "node_id": node_id,
        "headend_id": headend_id,
        "hub_id": hub_id,
        "service_area": service_area,
        "region": service_area,
        "city": city,
        "state": config["state"],
        "latitude": round(lat, 6),
        "longitude": round(lng, 6),
        "node_type": node_type,
        "homes_passed": homes_passed,
        "homes_active": homes_active,
        "docsis_version": docsis,
        "downstream_channels": random_int(ch_cfg["ds_channels"][0], ch_cfg["ds_channels"][1]),
        "upstream_channels": random_int(ch_cfg["us_channels"][0], ch_cfg["us_channels"][1]),
        "ofdm_channels": random_int(ch_cfg["ofdm_channels"][0], ch_cfg["ofdm_channels"][1]),
        "ofdma_channels": random_int(ch_cfg["ofdma_channels"][0], ch_cfg["ofdma_channels"][1]),
        "manufacturer": mfr,
        "hardware_model": model,
        "firmware_version": f"{random_int(1, 5)}.{random_int(0, 20)}.{random_int(0, 99)}",
        "power_supply_count": random_choice([1, 2]),
        "power_supply_status": weighted_choice({"all_ok": 0.90, "partial_failure": 0.08, "critical": 0.02}),
        "battery_backup_hours": random_float(4, 12, 1),
        "amplifier_cascade": type_cfg["amplifier_cascade"],
        "coax_plant_miles": random_float(1, 15, 1),
        "fiber_miles": random_float(1, 10, 1),
        "tap_count": random_int(20, 200),
        "status": weighted_choice(const.DEFAULT_NODE_STATUS_DISTRIBUTION),
        "upstream_cmts_id": cmts_id,
        "neighbor_nodes": [],
    }


def generate_amplifier(amp_index: int, node_id: str, cascade_position: int) -> Dict:
    """Generate an RF amplifier"""
    amp_id = f"AMP-{node_id.split('-', 1)[1]}-{amp_index:02d}"
    mfr = random_choice(list(const.AMPLIFIER_MANUFACTURERS.keys()))
    model = random_choice(const.AMPLIFIER_MANUFACTURERS[mfr])
    return {
        "amp_id": amp_id,
        "node_id": node_id,
        "manufacturer": mfr,
        "model": model,
        "amp_type": weighted_choice(const.AMPLIFIER_TYPE_DISTRIBUTION),
        "cascade_position": cascade_position,
        "location_type": weighted_choice(const.AMPLIFIER_LOCATION_DISTRIBUTION),
        "ds_input_level": random_float(8, 15, 1),
        "ds_output_level": random_float(38, 46, 1),
        "us_input_level": random_float(10, 20, 1),
        "us_output_level": random_float(38, 44, 1),
        "ds_snr": random_float(33, 42, 1),
        "us_snr": random_float(25, 35, 1),
        "temperature_celsius": random_float(25, 60, 1),
        "power_consumption_watts": random_float(30, 90, 1),
        "power_supply_status": weighted_choice({"normal": 0.90, "degraded": 0.08, "failed": 0.02}),
        "status": weighted_choice({"operational": 0.90, "degraded": 0.08, "failed": 0.02}),
    }


def generate_all_infrastructure() -> Dict:
    """Generate all cable plant infrastructure in hierarchy"""
    headends, hubs, cmts_devices, fiber_nodes, amplifiers = [], [], [], [], []
    node_global_idx = 0
    amp_global_idx = 0

    for sa_name, sa_config in const.SERVICE_AREA_CONFIG.items():
        # Headends
        sa_headends = []
        for hi in range(sa_config["headend_count"]):
            he = generate_headend(len(headends), sa_name, sa_config)
            headends.append(he)
            sa_headends.append(he)

            # CMTS per headend
            for ci in range(he["cmts_count"]):
                cmts = generate_cmts(len(cmts_devices), he["headend_id"])
                cmts_devices.append(cmts)

        # Hubs
        for hi in range(sa_config["hub_count"]):
            he = random_choice(sa_headends)
            hub = generate_hub(len(hubs), he["headend_id"], sa_name, sa_config)
            hubs.append(hub)

            # Nodes per hub - assign to a CMTS from the headend
            he_cmts_list = [c for c in cmts_devices if c["headend_id"] == he["headend_id"]]
            nodes_per_hub = settings.NODES_PER_HUB or sa_config.get("nodes_per_hub", 40)
            for ni in range(nodes_per_hub):
                cmts = he_cmts_list[ni % len(he_cmts_list)] if he_cmts_list else cmts_devices[0]
                node = generate_fiber_node(
                    node_global_idx, sa_name, he["headend_id"], hub["hub_id"],
                    cmts["cmts_id"], sa_config
                )
                fiber_nodes.append(node)
                node_global_idx += 1

                # Amplifiers per node based on cascade depth
                cascade = node["amplifier_cascade"]
                for ai in range(cascade):
                    amp = generate_amplifier(amp_global_idx, node["node_id"], ai + 1)
                    amplifiers.append(amp)
                    amp_global_idx += 1

    # Assign neighbor nodes (3-5 random from same service area)
    sa_node_map: Dict[str, List[str]] = {}
    for n in fiber_nodes:
        sa_node_map.setdefault(n["service_area"], []).append(n["node_id"])

    for n in fiber_nodes:
        sa_nodes = sa_node_map.get(n["service_area"], [])
        num_neighbors = min(random_int(3, 5), len(sa_nodes) - 1)
        candidates = [nid for nid in sa_nodes if nid != n["node_id"]]
        n["neighbor_nodes"] = random.sample(candidates, min(num_neighbors, len(candidates)))

    return {
        "headends": headends,
        "hubs": hubs,
        "cmts_devices": cmts_devices,
        "fiber_nodes": fiber_nodes,
        "amplifiers": amplifiers,
    }


# ============================================
# KPI Metrics Generator
# ============================================

def generate_node_kpi_metrics(node_id: str, timestamp: Optional[datetime] = None,
                               weather_conditions: Optional[Dict] = None) -> Dict:
    """Generate cable RF KPI metrics for a fiber node"""
    if timestamp is None:
        timestamp = datetime.now()

    metric_id = f"KPI-{node_id}-{int(timestamp.timestamp())}"

    # Base cable RF metrics
    ds_power = random_float(-6, 6, 1)
    us_power = random_float(40, 48, 1)
    ds_snr = random_float(33, 42, 1)
    us_snr = random_float(25, 35, 1)
    ds_mer = random_float(33, 45, 1)
    us_mer = random_float(25, 38, 1)
    fec_corrected = random_int(0, 5000)
    fec_uncorrected = random_int(0, 50)
    t3 = random_int(0, 10)
    t4 = random_int(0, 5)
    ds_throughput = random_float(200, 1200, 1)
    us_throughput = random_float(10, 50, 1)
    latency = random_float(8, 40, 1)
    packet_loss = random_float(0, 1.5, 3)
    jitter = random_float(1, 10, 1)
    ds_util = random_float(20, 85, 1)
    us_util = random_float(15, 75, 1)
    ofdm_util = random_float(10, 70, 1)
    active_modems = random_int(50, 250)
    registered_modems = active_modems + random_int(10, 30)
    offline_modems = random_int(0, 15)
    modems_flaps = random_int(0, 10)
    node_temp = random_float(25, 65, 1)
    cpu = random_float(20, 80, 1)
    memory = random_float(30, 75, 1)
    voltage = random_float(55, 65, 1)

    kpi = {
        "metric_id": metric_id, "node_id": node_id, "timestamp": timestamp,
        "ds_power_level_dbmv": ds_power, "us_power_level_dbmv": us_power,
        "ds_snr_db": ds_snr, "us_snr_db": us_snr, "ds_mer_db": ds_mer, "us_mer_db": us_mer,
        "fec_corrected_codewords": fec_corrected, "fec_uncorrected_codewords": fec_uncorrected,
        "t3_timeouts": t3, "t4_timeouts": t4,
        "downstream_throughput_mbps": ds_throughput, "upstream_throughput_mbps": us_throughput,
        "latency_ms": latency, "packet_loss_percent": packet_loss, "jitter_ms": jitter,
        "ds_channel_utilization_percent": ds_util, "us_channel_utilization_percent": us_util,
        "ofdm_utilization_percent": ofdm_util,
        "active_modems": active_modems, "registered_modems": registered_modems,
        "offline_modems": offline_modems, "modems_with_flaps": modems_flaps,
        "node_temperature": node_temp, "node_cpu_utilization": cpu,
        "node_memory_utilization": memory, "power_supply_voltage": voltage,
        "weather_conditions": None, "weather_impact": None,
        "temperature_outdoor": None, "precipitation_mm": None, "wind_speed_kmh": None,
    }

    if weather_conditions:
        rain = weather_conditions.get("rain_impact", 0)
        temp_impact = weather_conditions.get("temp_impact", 0)
        wind = weather_conditions.get("wind_impact", 0)
        overall = weather_conditions.get("weather_impact", 0)

        if rain > 0:
            kpi["ds_snr_db"] = round(ds_snr - rain * 8, 1)
            kpi["us_snr_db"] = round(us_snr - rain * 6, 1)
            kpi["packet_loss_percent"] = round(min(10, packet_loss + rain * 3), 3)
            kpi["downstream_throughput_mbps"] = round(max(50, ds_throughput * (1 - rain * 0.3)), 1)
            kpi["fec_uncorrected_codewords"] = min(500, fec_uncorrected + int(rain * 200))

        if temp_impact > 0:
            kpi["node_cpu_utilization"] = round(min(100, cpu + temp_impact * 20), 1)
            kpi["node_temperature"] = round(node_temp + temp_impact * 15, 1)

        if wind > 0:
            kpi["ds_power_level_dbmv"] = round(ds_power + wind * random.choice([-1, 1]) * 3, 1)
            kpi["offline_modems"] = min(100, offline_modems + int(wind * 20))

        if overall > 0:
            kpi["latency_ms"] = round(latency * (1 + overall * 0.4), 1)
            kpi["t3_timeouts"] = min(100, t3 + int(overall * 20))

        kpi["weather_conditions"] = weather_conditions.get("weather_desc")
        kpi["weather_impact"] = round(overall, 3) if overall else None
        kpi["temperature_outdoor"] = weather_conditions.get("temperature_outdoor")
        kpi["precipitation_mm"] = weather_conditions.get("precipitation_mm")
        kpi["wind_speed_kmh"] = weather_conditions.get("wind_speed_kmh")

    return kpi


# ============================================
# Alert & Action Generators
# ============================================

def generate_cable_alert(node_id: str) -> Dict:
    """Generate a cable network alert"""
    alert_id = f"ALT-{uuid.uuid4().hex[:12].upper()}"
    alert_type = random_choice(const.ALERT_TYPES)
    severity = weighted_choice({"CRITICAL": 0.20, "WARNING": 0.50, "INFO": 0.30})
    status = weighted_choice({"ACTIVE": 0.70, "ACKNOWLEDGED": 0.20, "RESOLVED": 0.10})
    title, description = const.ALERT_DESCRIPTIONS.get(alert_type, ("Alert", "Network issue detected"))
    timestamp = datetime.now() - timedelta(minutes=random_int(0, 1440))
    resolved_at = timestamp + timedelta(minutes=random_int(30, 180)) if status == "RESOLVED" else None

    return {
        "alert_id": alert_id, "node_id": node_id, "type": alert_type,
        "severity": severity, "status": status, "title": title, "description": description,
        "timestamp": timestamp, "resolved_at": resolved_at,
        "impacted_users": random_int(10, 2000),
        "root_cause": f"Analysis pending for {alert_type}" if status == "ACTIVE" else None,
        "affected_customers": random_int(50, 500),
        "affected_modems": random_int(20, 250),
    }


def generate_auto_resolution_action(node_id: str, alert_id: Optional[str] = None) -> Dict:
    """Generate an auto-resolution action for cable network"""
    action_id = f"ACT-{uuid.uuid4().hex[:12].upper()}"
    action_type = random_choice(const.ACTION_TYPES)
    status = weighted_choice({"PENDING": 0.20, "IN_PROGRESS": 0.30, "COMPLETED": 0.40, "FAILED": 0.10})
    description = const.ACTION_DESCRIPTIONS.get(action_type, "Automated remediation action")
    start_time = datetime.now() - timedelta(minutes=random_int(0, 60))
    end_time = start_time + timedelta(minutes=random_int(5, 30)) if status in ["COMPLETED", "FAILED"] else None
    eff_range = const.ACTION_EFFECTIVENESS.get(action_type, (50, 90))
    effectiveness = random_float(eff_range[0], eff_range[1], 1) if status == "COMPLETED" else None

    result = {
        "action_id": action_id, "alert_id": alert_id, "node_id": node_id,
        "action_type": action_type, "status": status, "description": description,
        "start_time": start_time, "end_time": end_time,
        "effectiveness_score": effectiveness, "automated": True,
        "executed_by": "Auto-Resolution Engine",
        "ticket_id": None, "escalation_reason": None,
    }

    if status == "FAILED":
        result["ticket_id"] = f"TKT-{uuid.uuid4().hex[:12].upper()}"
        result["escalation_reason"] = random_choice([
            "Auto-resolution unsuccessful after 3 attempts",
            "Issue requires physical plant inspection",
            "Customer impact exceeds autonomous threshold",
            "Equipment replacement needed",
        ])

    return result


# ============================================
# Customer & Sentiment Generators
# ============================================

def generate_customer_account(account_index: int, node_id: str, city: str, state: str) -> Dict:
    """Generate a customer account"""
    account_id = f"ACCT-{account_index:07d}"
    first = random_choice(const.CUSTOMER_FIRST_NAMES)
    last = random_choice(const.CUSTOMER_LAST_NAMES)
    street_num = random_int(100, 9999)
    street = random_choice(const.STREET_NAMES)
    plan_name = weighted_choice(const.SERVICE_PLAN_DISTRIBUTION)
    plan = const.SERVICE_PLANS[plan_name]
    dl = plan["download_mbps"]
    ul = plan["upload_mbps"]
    modem_mfr = random_choice(list(const.MODEM_MANUFACTURERS.keys()))
    modem_model = random_choice(const.MODEM_MANUFACTURERS[modem_mfr])
    mac = ":".join([f"{random_int(0,255):02X}" for _ in range(6)])

    return {
        "account_id": account_id, "name": f"{first} {last}",
        "address": f"{street_num} {street}", "city": city, "state": state,
        "zip_code": f"{random_int(10000, 99999)}", "latitude": 0, "longitude": 0,
        "node_id": node_id, "tap_id": f"TAP-{node_id}-{random_int(1, 200):03d}",
        "drop_length_ft": random_float(20, 200, 0),
        "drop_quality": weighted_choice({"good": 0.70, "fair": 0.20, "poor": 0.10}),
        "service_plan": plan_name,
        "provisioned_download_mbps": dl, "provisioned_upload_mbps": ul,
        "monthly_rate": plan["monthly_rate"],
        "contract_status": weighted_choice({"active": 0.50, "month_to_month": 0.40, "expired": 0.10}),
        "tenure_months": random_int(1, 120),
        "modem_mac": mac, "modem_model": modem_model, "modem_manufacturer": modem_mfr,
        "docsis_version": weighted_choice(const.DOCSIS_VERSION_DISTRIBUTION),
        "modem_firmware": f"{random_int(1, 5)}.{random_int(0, 20)}.{random_int(0, 99)}",
        "actual_download_mbps": round(dl * random.uniform(0.80, 1.05), 1),
        "actual_upload_mbps": round(ul * random.uniform(0.80, 1.05), 1),
        "connection_drops_24h": random_int(0, 5),
        "last_speed_test": datetime.now() - timedelta(days=random_int(0, 30)),
        "last_reboot": datetime.now() - timedelta(days=random_int(0, 90)),
        "uptime_hours": random_float(0, 2160, 0),
        "account_status": weighted_choice({"active": 0.90, "suspended": 0.05, "closed": 0.05}),
    }


def generate_customer_sentiment(account_id: str) -> Dict:
    """Generate customer sentiment record"""
    sentiment_id = f"SENT-{uuid.uuid4().hex[:12].upper()}"
    source = weighted_choice(const.SENTIMENT_SOURCE_DISTRIBUTION)
    score = round(random.gauss(0.3, 0.4), 2)
    score = max(-1.0, min(1.0, score))

    if score > 0.3:
        label = "positive"
    elif score > -0.1:
        label = "neutral"
    elif score > -0.5:
        label = "negative"
    else:
        label = "very_negative"

    topics = random.sample(const.SENTIMENT_TOPICS, random_int(1, 3))
    summaries = {
        "positive": f"Customer satisfied with {topics[0].replace('_', ' ')}",
        "neutral": f"Customer has mixed feelings about {topics[0].replace('_', ' ')}",
        "negative": f"Customer frustrated with {topics[0].replace('_', ' ')}",
        "very_negative": f"Customer extremely dissatisfied with {topics[0].replace('_', ' ')}",
    }

    return {
        "sentiment_id": sentiment_id, "account_id": account_id, "source": source,
        "sentiment_score": score, "sentiment_label": label, "topics": topics,
        "summary": summaries[label], "raw_text": None,
        "nps_score": random_int(0, 10) if source == "nps_survey" else None,
        "resolution_status": weighted_choice({"resolved": 0.50, "unresolved": 0.30, "escalated": 0.20}),
        "timestamp": datetime.now() - timedelta(hours=random_int(0, 720)),
    }


def generate_trouble_ticket(node_id: str, account_id: Optional[str] = None,
                            from_failed_action: bool = False) -> Dict:
    """Generate a trouble ticket"""
    ticket_id = f"TKT-{uuid.uuid4().hex[:12].upper()}"
    category = weighted_choice(const.TICKET_CATEGORY_DISTRIBUTION)
    priority_map = {"service_outage": "P1", "slow_speed": "P3", "intermittent": "P2",
                    "plant_damage": "P1", "noise_ingress": "P2"}
    priority = priority_map.get(category, "P3")
    status = weighted_choice({"open": 0.30, "assigned": 0.20, "in_progress": 0.25,
                              "resolved": 0.15, "closed": 0.10})
    equipment = const.EQUIPMENT_FOR_TICKET.get(category, [])
    needs_truck = category in ["service_outage", "plant_damage", "noise_ingress"]
    tech_map = {"P1": "L3", "P2": "L2", "P3": "L1", "P4": "L1"}

    return {
        "ticket_id": ticket_id, "account_id": account_id, "node_id": node_id,
        "category": category, "priority": priority, "status": status,
        "title": f"{category.replace('_', ' ').title()} - {node_id}",
        "description": f"Customer reported {category.replace('_', ' ')} issue",
        "auto_resolution_attempted": from_failed_action,
        "auto_resolution_actions": None, "auto_resolution_success": None,
        "truck_roll_needed": needs_truck,
        "tech_skill_level": tech_map.get(priority, "L1"),
        "equipment_needed": equipment,
        "estimated_resolution_hours": random_float(1, 8, 1),
        "assigned_tech": None,
        "created_at": datetime.now(), "acknowledged_at": None, "dispatched_at": None,
        "resolved_at": None, "closed_at": None, "resolution_notes": None,
        "created_by": weighted_choice({"auto_detection": 0.30, "customer_call": 0.35,
                                       "proactive_monitoring": 0.25, "field_tech": 0.10}),
        "related_alert_ids": None,
    }


# ============================================
# Maintenance & Gating Generators
# ============================================

def generate_maintenance_window(node_id: Optional[str] = None, headend_id: Optional[str] = None,
                                 service_area: Optional[str] = None) -> Dict:
    """Generate a maintenance window with buffers"""
    window_id = f"MW-{uuid.uuid4().hex[:12].upper()}"
    window_type = random_choice(const.MAINTENANCE_WINDOW_TYPES)
    start = datetime.now() + timedelta(hours=random_int(1, 168))
    duration_hours = random_float(1, 8, 1)
    end = start + timedelta(hours=duration_hours)

    return {
        "window_id": window_id, "node_id": node_id, "headend_id": headend_id,
        "service_area": service_area,
        "window_type": window_type,
        "status": weighted_choice({"scheduled": 0.40, "approved": 0.30, "in_progress": 0.15,
                                   "completed": 0.10, "cancelled": 0.05}),
        "priority": random_choice(const.TICKET_PRIORITIES),
        "scheduled_start": start, "scheduled_end": end,
        "actual_start": None, "actual_end": None,
        "buffer_before_minutes": const.GATING_THRESHOLDS["default_buffer_before_minutes"],
        "buffer_after_minutes": const.GATING_THRESHOLDS["default_buffer_after_minutes"],
        "affected_homes": random_int(100, 2000),
        "affected_customers": random_int(50, 1000),
        "customer_notification_sent": False, "notification_sent_at": None,
        "reason": random_choice(const.MAINTENANCE_REASONS),
        "work_description": f"Scheduled {window_type.replace('_', ' ')}",
        "assigned_crew_id": f"CREW-{random_int(100, 999)}",
        "assigned_crew_name": f"Crew {random_int(1, 50)}",
        "reschedule_count": 0, "original_window_id": None, "rescheduled_reason": None,
        "created_by": random_choice(const.OPERATOR_NAMES),
        "approved_by": None,
    }


def generate_gating_signals(window_id: str) -> List[Dict]:
    """Generate gating signal evaluations for a maintenance window"""
    signals = []
    for sig_type in const.GATING_SIGNAL_TYPES:
        signal_id = f"GATE-{uuid.uuid4().hex[:12].upper()}"
        passed = random.random() < 0.80  # 80% pass rate
        is_blocking = sig_type not in ["resource_availability"]
        signals.append({
            "signal_id": signal_id, "maintenance_window_id": window_id,
            "signal_type": sig_type,
            "signal_status": "passed" if passed else "failed",
            "is_blocking": is_blocking,
            "evaluated_at": datetime.now(),
            "evaluation_result": {"check": sig_type, "passed": passed},
            "threshold_value": None, "actual_value": None,
            "override_by": None, "override_reason": None,
            "description": f"Gate check: {sig_type.replace('_', ' ')}",
        })
    return signals


def generate_ecaf(window_id: str) -> Dict:
    """Generate an electronic change authorization form"""
    ecaf_id = f"ECAF-{uuid.uuid4().hex[:12].upper()}"
    change_type = random_choice(const.ECAF_CHANGE_TYPES)
    return {
        "ecaf_id": ecaf_id, "maintenance_window_id": window_id,
        "change_type": change_type,
        "title": f"{change_type.replace('_', ' ').title()} Change",
        "description": f"Authorized change: {change_type.replace('_', ' ')}",
        "risk_level": weighted_choice({"low": 0.40, "medium": 0.35, "high": 0.20, "critical": 0.05}),
        "impact_assessment": {"homes_affected": random_int(50, 1000), "expected_downtime_minutes": random_int(15, 120)},
        "rollback_plan": [{"step": 1, "action": "Revert configuration"}, {"step": 2, "action": "Verify service restoration"}],
        "rollback_timeout_minutes": random_int(30, 120),
        "pre_change_checks": [{"check": "Verify current config"}, {"check": "Confirm backup"}],
        "post_change_checks": [{"check": "Verify service"}, {"check": "Check KPIs"}],
        "status": weighted_choice({"draft": 0.20, "pending_review": 0.20, "approved": 0.30,
                                   "executing": 0.10, "completed": 0.15, "rolled_back": 0.05}),
        "requested_by": random_choice(const.OPERATOR_NAMES),
        "reviewed_by": None, "approved_by": None, "approved_at": None,
        "execution_started_at": None, "execution_completed_at": None,
        "rollback_initiated_at": None, "rollback_completed_at": None, "notes": None,
    }


def detect_maintenance_conflicts(windows: List[Dict]) -> List[Dict]:
    """Detect conflicts between maintenance windows"""
    conflicts = []
    for i, wa in enumerate(windows):
        for wb in windows[i + 1:]:
            # Check time overlap
            if wa["scheduled_start"] < wb["scheduled_end"] and wb["scheduled_start"] < wa["scheduled_end"]:
                conflict_id = f"CONF-{uuid.uuid4().hex[:12].upper()}"
                conflicts.append({
                    "conflict_id": conflict_id,
                    "window_a_id": wa["window_id"], "window_b_id": wb["window_id"],
                    "conflict_type": "overlapping_time",
                    "severity": "high" if wa.get("node_id") == wb.get("node_id") else "medium",
                    "description": f"Overlapping time between {wa['window_id']} and {wb['window_id']}",
                    "resolution_status": "detected",
                    "resolved_by": None, "resolution_notes": None,
                    "detected_at": datetime.now(), "resolved_at": None,
                })
    return conflicts


def generate_rollback_event(ecaf_id: str, window_id: str) -> Dict:
    """Generate a rollback event"""
    rollback_id = f"RB-{uuid.uuid4().hex[:12].upper()}"
    return {
        "rollback_id": rollback_id, "ecaf_id": ecaf_id, "maintenance_window_id": window_id,
        "trigger_type": weighted_choice({"automatic": 0.50, "manual": 0.30, "timeout": 0.20}),
        "trigger_reason": random_choice([
            "Post-change verification failed", "KPI degradation detected",
            "Rollback timeout exceeded", "Operator initiated rollback",
        ]),
        "rollback_steps_executed": [{"step": 1, "status": "completed"}, {"step": 2, "status": "completed"}],
        "rollback_status": weighted_choice({"completed": 0.80, "failed": 0.10, "in_progress": 0.10}),
        "initiated_by": random_choice(const.OPERATOR_NAMES + ["AutoRollback Engine"]),
        "initiated_at": datetime.now(),
        "completed_at": datetime.now() + timedelta(minutes=random_int(5, 30)),
        "pre_rollback_metrics": {"ds_snr_db": random_float(28, 35, 1), "latency_ms": random_float(20, 80, 1)},
        "post_rollback_metrics": {"ds_snr_db": random_float(33, 42, 1), "latency_ms": random_float(10, 30, 1)},
        "success": random.random() < 0.85, "notes": None,
    }


# ============================================
# Dark NOC & Predictive Generators
# ============================================

def generate_predictive_results(node_ids: List[str]) -> List[Dict]:
    """Generate predictive model results for nodes"""
    results = []
    for node_id in random.sample(node_ids, min(20, len(node_ids))):
        model_type = random_choice(const.PREDICTIVE_MODEL_TYPES)
        prediction_id = f"PRED-{uuid.uuid4().hex[:12].upper()}"
        prob = random_float(0.1, 0.95, 3)
        results.append({
            "prediction_id": prediction_id, "model_type": model_type,
            "target_entity_type": "node", "target_entity_id": node_id,
            "prediction_horizon_hours": random_choice([1, 6, 12, 24, 48, 72]),
            "predicted_event": f"{model_type} event for {node_id}",
            "probability": prob,
            "confidence_interval_low": round(max(0, prob - 0.15), 3),
            "confidence_interval_high": round(min(1, prob + 0.15), 3),
            "contributing_factors": [
                {"factor": "temperature_trend", "importance": random_float(0, 1, 2)},
                {"factor": "fec_error_rate", "importance": random_float(0, 1, 2)},
                {"factor": "equipment_age", "importance": random_float(0, 1, 2)},
            ],
            "recommended_preemptive_action": "Schedule preventive maintenance",
            "action_taken": False, "action_result": None,
            "predicted_at": datetime.now(),
            "prediction_window_start": datetime.now(),
            "prediction_window_end": datetime.now() + timedelta(hours=24),
            "actual_outcome": None, "accuracy_score": None, "model_version": "v1.0",
        })
    return results


def generate_impact_model(trigger_entity_id: str, scenario_type: str) -> Dict:
    """Generate cascading impact analysis"""
    impact_id = f"IMP-{uuid.uuid4().hex[:12].upper()}"
    affected_customers = random_int(100, 5000)
    return {
        "impact_id": impact_id, "scenario_type": scenario_type,
        "trigger_entity_id": trigger_entity_id,
        "trigger_description": f"{scenario_type.replace('_', ' ')} at {trigger_entity_id}",
        "cascading_impacts": [
            {"order": 1, "effect": "Primary equipment failure", "delay_minutes": 0},
            {"order": 2, "effect": "Downstream service degradation", "delay_minutes": 5},
            {"order": 3, "effect": "Customer impact detected", "delay_minutes": 10},
        ],
        "affected_nodes": [trigger_entity_id],
        "affected_customers_total": affected_customers,
        "affected_homes_total": int(affected_customers * 1.3),
        "estimated_revenue_impact": round(affected_customers * 0.15 * random_float(1, 8, 1), 2),
        "estimated_duration_hours": random_float(0.5, 8, 1),
        "service_degradation_percent": random_float(10, 80, 1),
        "customer_experience_score_impact": random_float(-0.5, -0.05, 2),
        "churn_risk_increase_percent": random_float(0.5, 5, 1),
        "sla_breach_probability": random_float(0.1, 0.8, 2),
        "recommended_mitigations": [
            {"action": "Reroute traffic", "impact_reduction_percent": 40},
            {"action": "Deploy backup equipment", "impact_reduction_percent": 60},
        ],
        "model_confidence": random_float(0.6, 0.95, 2),
        "computed_at": datetime.now(),
    }


def generate_event_correlations(alert_ids: List[str]) -> List[Dict]:
    """Generate event correlations from alert clusters"""
    correlations = []
    if len(alert_ids) < 3:
        return correlations

    # Create 1-3 clusters
    for _ in range(random_int(1, min(3, len(alert_ids) // 2))):
        cluster_size = random_int(2, min(5, len(alert_ids)))
        cluster = random.sample(alert_ids, cluster_size)
        correlation_id = f"CORR-{uuid.uuid4().hex[:12].upper()}"
        correlations.append({
            "correlation_id": correlation_id,
            "correlation_type": random_choice(["temporal", "spatial", "causal", "topological"]),
            "source_alert_ids": cluster,
            "root_cause_alert_id": cluster[0],
            "correlated_alert_count": len(cluster),
            "suppressed_alert_count": len(cluster) - 1,
            "correlation_confidence": random_float(0.6, 0.98, 2),
            "correlation_pattern": {"type": "alert_cluster", "window_minutes": 5},
            "affected_nodes": [], "affected_customers_total": random_int(50, 500),
            "auto_generated": True, "validated_by_operator": False,
        })
    return correlations


# ============================================
# Network Device & Config Generators
# ============================================

DEVICE_MANUFACTURERS = {
    "firewall": {
        "Fortinet": ["FortiGate 600F", "FortiGate 400F", "FortiGate 200F"],
        "Palo Alto": ["PA-5250", "PA-3260", "PA-850"],
        "Cisco": ["Firepower 4120", "Firepower 2130", "ASA 5555-X"],
    },
    "switch": {
        "Cisco": ["Catalyst 9300", "Catalyst 9200", "Nexus 9332C"],
        "Arista": ["7050X3", "7280R3", "720XP"],
        "Juniper": ["EX4400", "EX3400", "QFX5120"],
    },
    "router": {
        "Cisco": ["ASR 9001", "ISR 4451", "NCS 5501"],
        "Juniper": ["MX204", "MX304", "ACX7100"],
        "Nokia": ["7750 SR-1", "7250 IXR-6", "7220 IXR-D3"],
    },
    "modem": {
        "ARRIS": ["SB8200", "S33", "TM3402"],
        "Motorola": ["MB8611", "MB7621", "MT8733"],
        "Netgear": ["CM2000", "CM1200", "CM1000"],
    },
}


def _generate_ip(prefix: str, index: int) -> str:
    """Generate a management IP from prefix and index"""
    octet3 = (index // 254) % 256
    octet4 = (index % 254) + 1
    return f"{prefix}.{octet3}.{octet4}"


def generate_network_device(device_type: str, device_index: int,
                            headend_id: str = None, hub_id: str = None,
                            region: str = None) -> Dict:
    """Generate a network device with realistic config per type"""
    mfr_map = DEVICE_MANUFACTURERS.get(device_type, {})
    mfr = random_choice(list(mfr_map.keys()))
    model = random_choice(mfr_map[mfr])
    hostname = f"{device_type}-{region[:3].lower() if region else 'net'}-{device_index:03d}"

    role_map = {
        "firewall": ["perimeter", "internal", "dmz"],
        "switch": ["core", "distribution", "access"],
        "router": ["core", "edge", "distribution"],
        "modem": ["access", "edge"],
    }
    role = random_choice(role_map.get(device_type, ["access"]))

    # Device-specific running config
    running_config = _generate_device_config(device_type, role, hostname)

    ip_prefix = {"firewall": "10.1", "switch": "10.2", "router": "10.3", "modem": "10.4"}.get(device_type, "10.5")
    device_id = f"{device_type[:2].upper()}-{uuid.uuid4().hex[:8].upper()}"

    return {
        "device_id": device_id,
        "device_type": device_type,
        "device_role": role,
        "hostname": hostname,
        "description": f"{mfr} {model} - {role} {device_type} at {headend_id or hub_id or 'unassigned'}",
        "headend_id": headend_id,
        "hub_id": hub_id,
        "region": region,
        "manufacturer": mfr,
        "hardware_model": model,
        "serial_number": f"{mfr[:3].upper()}{uuid.uuid4().hex[:10].upper()}",
        "firmware_version": f"{random_int(6, 15)}.{random_int(0, 9)}.{random_int(0, 20)}",
        "os_version": f"{mfr}OS {random_int(6, 15)}.{random_int(0, 9)}",
        "management_ip": _generate_ip(ip_prefix, device_index),
        "interfaces": _generate_interfaces(device_type),
        "uplink_speed_gbps": random_choice([1, 10, 25, 40, 100]),
        "status": weighted_choice({"operational": 0.90, "degraded": 0.07, "maintenance": 0.03}),
        "uptime_seconds": random_int(3600, 86400 * 365),
        "running_config": running_config,
        "startup_config": running_config,  # Initially in sync
        "config_hash": uuid.uuid4().hex[:16],
        "compliance_status": weighted_choice({"compliant": 0.85, "drifted": 0.10, "non_compliant": 0.05}),
        "cpu_utilization": random_float(10, 70, 1),
        "memory_utilization": random_float(20, 75, 1),
        "temperature_celsius": random_float(25, 55, 1),
    }


def _generate_interfaces(device_type: str) -> List[Dict]:
    """Generate interface list for a device"""
    count_map = {"firewall": 4, "switch": 24, "router": 8, "modem": 2}
    count = count_map.get(device_type, 4)
    prefix_map = {"firewall": "eth", "switch": "Gi0/", "router": "ge-0/0/", "modem": "cm"}
    prefix = prefix_map.get(device_type, "eth")
    interfaces = []
    for i in range(min(count, 6)):  # Store up to 6 interfaces
        interfaces.append({
            "name": f"{prefix}{i}",
            "status": weighted_choice({"up": 0.92, "down": 0.05, "admin_down": 0.03}),
            "speed_gbps": random_choice([1, 10, 25]),
        })
    return interfaces


def _generate_device_config(device_type: str, role: str, hostname: str) -> Dict:
    """Generate device-specific configuration"""
    if device_type == "firewall":
        return {
            "hostname": hostname,
            "security_zones": ["trust", "untrust", "dmz"],
            "acl_rules": [
                {"id": i, "action": random_choice(["permit", "deny"]),
                 "source": f"10.{random_int(0,255)}.0.0/16",
                 "destination": f"10.{random_int(0,255)}.0.0/16",
                 "service": random_choice(["http", "https", "ssh", "dns", "any"])}
                for i in range(random_int(5, 15))
            ],
            "nat_rules": random_int(2, 8),
            "ips_enabled": True,
            "ips_mode": random_choice(["detect", "prevent"]),
            "vpn_tunnels": random_int(0, 5),
            "logging_level": random_choice(["info", "warning", "debug"]),
        }
    elif device_type == "switch":
        vlans = [{"id": vid, "name": random_choice(["management", "data", "voice", "iot", "guest", "security"]),
                  "ports": random_int(2, 12)} for vid in random.sample(range(10, 500), random_int(3, 8))]
        return {
            "hostname": hostname,
            "vlans": vlans,
            "stp_mode": random_choice(["rapid-pvst", "mstp", "rstp"]),
            "stp_priority": random_choice([4096, 8192, 16384, 32768]),
            "port_security_enabled": random.random() < 0.7,
            "dhcp_snooping": random.random() < 0.6,
            "storm_control": random.random() < 0.5,
            "spanning_tree_guard": random_choice(["root", "loop", "bpdu", "none"]),
            "management_vlan": vlans[0]["id"] if vlans else 1,
        }
    elif device_type == "router":
        return {
            "hostname": hostname,
            "routing_protocols": {
                "ospf": {"area": "0.0.0.0", "enabled": True,
                         "neighbors": random_int(2, 8)},
                "bgp": {"asn": random_int(64512, 65534), "enabled": role == "core",
                         "peers": random_int(1, 4) if role == "core" else 0},
            },
            "static_routes": random_int(5, 25),
            "acl_count": random_int(3, 12),
            "qos_policies": [
                {"class": cls, "bandwidth_percent": bw, "priority": pri}
                for cls, bw, pri in [("voice", 20, "strict"), ("video", 30, "high"),
                                     ("data", 40, "medium"), ("best-effort", 10, "low")]
            ],
            "mpls_enabled": role == "core",
            "nat_enabled": role == "edge",
        }
    else:  # modem
        return {
            "hostname": hostname,
            "docsis_version": random_choice(["3.0", "3.1", "4.0"]),
            "downstream_channels": random_int(8, 32),
            "upstream_channels": random_int(4, 8),
            "ofdm_enabled": random.random() < 0.6,
            "max_download_mbps": random_choice([300, 600, 1000, 1200, 2000]),
            "max_upload_mbps": random_choice([10, 20, 35, 50, 100]),
            "provisioning_file": f"cm-{hostname}.cfg",
            "firmware_auto_update": True,
        }


def generate_config_template(device_type: str, role: str) -> Dict:
    """Generate a baseline configuration template for a device type/role"""
    template_id = f"TMPL-{device_type[:2].upper()}-{role[:3].upper()}-{uuid.uuid4().hex[:6].upper()}"
    return {
        "template_id": template_id,
        "name": f"{device_type.title()} {role.title()} Baseline",
        "description": f"Standard baseline configuration for {role} {device_type}s",
        "device_type": device_type,
        "device_role": role,
        "config_template": _generate_device_config(device_type, role, f"{device_type}-template"),
        "version": "1.0",
        "is_active": True,
        "created_by": "system",
    }
