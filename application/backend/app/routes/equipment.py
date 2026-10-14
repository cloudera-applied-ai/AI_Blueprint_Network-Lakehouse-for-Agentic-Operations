"""Fiber node equipment endpoints - AAU, HVAC, Power, BBU equipment data"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from typing import Optional
from datetime import datetime, timedelta
from ..config import settings
from ..database import get_db
from ..models import FiberNodeModel, KPIMetricsModel, HVACUnitModel, ComponentMetricsHistoryModel
from . import safe_error_response, logger

router = APIRouter(prefix=settings.API_V1_STR, tags=["equipment"])


@router.get("/nodes/{node_id}/equipment")
def get_node_equipment(node_id: str, db: Session = Depends(get_db)):
    """Get all equipment for a specific node (AAU, HVAC, Power info)"""
    import random
    from datetime import datetime, timedelta

    # Check if node exists
    node_query = select(FiberNodeModel).where(FiberNodeModel.node_id == node_id)
    node = db.execute(node_query).scalar_one_or_none()
    if not node:
        raise HTTPException(status_code=404, detail=f"Node {node_id} not found")

    # Generate deterministic but realistic equipment data based on node_id
    # Use node_id hash for consistent random values
    seed = sum(ord(c) for c in node_id)
    random.seed(seed)

    now = datetime.now()

    # Generate AAU data (1-3 AAUs per node based on sectors)
    num_sectors = len(node.sectors) if node.sectors else 2
    aau_units = []
    for i in range(num_sectors):
        sector = node.sectors[i] if node.sectors and i < len(node.sectors) else {}
        status_choices = ['operational'] * 8 + ['degraded'] + ['maintenance']
        aau_units.append({
            "aau_id": f"AAU-{node_id}-{i:02d}",
            "sector_id": sector.get('cell_id', f"{node_id}-S{i:02d}"),
            "manufacturer": random.choice(['Cisco', 'CommScope/Arris', 'Casa Systems', 'Harmonic', 'Vecima Networks']),
            "model": random.choice(['CBR-8', 'E6000', 'C100G', 'CableOS', 'EXS2200']),
            "serial_number": f"SN-{random.randint(100000, 999999)}",
            "firmware_version": f"v{random.randint(2,5)}.{random.randint(0,9)}.{random.randint(0,99)}",
            "status": random.choice(status_choices),
            "frequency_bands": sector.get('frequency_band', '1800 MHz'),
            "max_tx_power_watts": random.uniform(40, 80),
            "current_tx_power_watts": random.uniform(20, 60),
            "antenna_ports": random.choice([4, 8, 16, 32, 64]),
            "mimo_config": random.choice(['2T2R', '4T4R', '8T8R', '32T32R', '64T64R']),
            "beamforming_enabled": random.choice([True, True, True, False]),
            "temperature_celsius": random.uniform(25, 55),
            "power_consumption_watts": random.uniform(200, 800),
            "vswr": random.uniform(1.1, 1.8),
            "efficiency_percent": random.uniform(75, 98),
            "installed_date": (now - timedelta(days=random.randint(180, 1800))).isoformat(),
            "last_maintenance": (now - timedelta(days=random.randint(7, 90))).isoformat(),
            "last_calibration": (now - timedelta(days=random.randint(1, 30))).isoformat(),
        })

    # Generate HVAC data (1 unit per node)
    hvac_status_choices = ['operational'] * 8 + ['degraded'] + ['maintenance']
    hvac_unit = {
        "hvac_id": f"HVAC-{node_id}",
        "manufacturer": random.choice(['Vertiv', 'Emerson', 'Schneider', 'Stulz', 'Rittal']),
        "model": random.choice(['Liebert DS', 'NetSure', 'InRow RC', 'CyberAir', 'LCP DX']),
        "serial_number": f"HVAC-SN-{random.randint(100000, 999999)}",
        "status": random.choice(hvac_status_choices),
        "cooling_capacity_kw": random.uniform(3, 15),
        "heating_capacity_kw": random.uniform(2, 8),
        "current_mode": random.choice(['cooling', 'cooling', 'cooling', 'heating', 'auto', 'fan_only']),
        "setpoint_celsius": random.uniform(20, 25),
        "current_temp_celsius": random.uniform(18, 30),
        "humidity_percent": random.uniform(30, 60),
        "power_consumption_watts": random.uniform(500, 2000),
        "compressor_status": random.choice(['running', 'running', 'running', 'idle', 'idle']),
        "filter_condition": random.choice(['good', 'good', 'good', 'replace_soon', 'replace_now']),
        "refrigerant_level_percent": random.uniform(85, 100),
        "high_temp_alarm": random.random() < 0.05,
        "low_temp_alarm": random.random() < 0.02,
        "compressor_fault": random.random() < 0.03,
        "installed_date": (now - timedelta(days=random.randint(365, 2500))).isoformat(),
        "last_maintenance": (now - timedelta(days=random.randint(14, 180))).isoformat(),
        "last_filter_change": (now - timedelta(days=random.randint(30, 365))).isoformat(),
    }

    # Generate Power System data
    power_status_choices = ['operational'] * 9 + ['degraded']
    has_generator = (node.power_supply_count or 1) > 1
    avg_power_kw = 2.5  # Default average power for fiber nodes
    power_system = {
        "power_id": f"PWR-{node_id}",
        "primary_source": node.power_supply_status or "Grid",
        "backup_type": "Battery + Generator" if has_generator else "Battery Only",
        "battery_backup_hours": node.battery_backup_hours or random.uniform(4, 24),
        "battery_capacity_ah": random.uniform(100, 500),
        "battery_voltage": random.choice([48, 48, 48, 24]),
        "battery_health_percent": random.uniform(80, 100),
        "battery_temperature_celsius": random.uniform(20, 35),
        "current_load_kw": random.uniform(0.5, avg_power_kw * 1.2),
        "max_load_kw": avg_power_kw * 1.5,
        "grid_status": random.choice(['connected', 'connected', 'connected', 'connected', 'unstable']),
        "grid_voltage": random.uniform(220, 240),
        "grid_frequency_hz": random.uniform(49.8, 50.2),
        "generator_status": "standby" if has_generator else "not_installed",
        "generator_type": "Diesel" if has_generator else "N/A",
        "generator_fuel_level_percent": random.uniform(60, 100) if has_generator else None,
        "generator_runtime_hours": random.randint(50, 2000) if has_generator else None,
        "generator_last_test": (now - timedelta(days=random.randint(7, 30))).isoformat() if has_generator else None,
        "ups_status": random.choice(['online', 'online', 'online', 'online', 'bypass']),
        "surge_protection_status": random.choice(['active', 'active', 'active', 'triggered']),
        "power_efficiency_percent": random.uniform(88, 98),
        "last_outage": (now - timedelta(days=random.randint(30, 365))).isoformat(),
        "total_outages_ytd": random.randint(0, 5),
    }

    # Generate BBU (Baseband Unit) data
    bbu_status_choices = ['operational'] * 8 + ['degraded'] + ['maintenance']
    bbu_unit = {
        "bbu_id": f"BBU-{node_id}",
        "manufacturer": node.manufacturer or random.choice(['Cisco', 'CommScope/Arris', 'Casa Systems', 'Harmonic']),
        "model": random.choice(['CBR-8 SUP', 'E6000 CCAP', 'C100G CCAP', 'CableOS Node']),
        "serial_number": f"BBU-SN-{random.randint(100000, 999999)}",
        "firmware_version": node.firmware_version or f"v{random.randint(3,6)}.{random.randint(0,9)}.{random.randint(0,99)}",
        "baseband_version": f"BB-{random.randint(5,12)}.{random.randint(0,9)}",
        "status": random.choice(bbu_status_choices),
        "cpu_utilization_percent": random.uniform(20, 80),
        "memory_utilization_percent": random.uniform(30, 75),
        "temperature_celsius": random.uniform(30, 55),
        "active_connections": random.randint(50, node.homes_active if node.homes_active else 500),
        "max_connections": node.homes_active or 1000,
        "processing_capacity_gbps": random.uniform(5, 25),
        "current_throughput_gbps": random.uniform(1, 15),
        "technologies_supported": node.node_type or ['4G', '5G'],
        "sectors_connected": num_sectors,
        "fronthaul_status": random.choice(['connected', 'connected', 'connected', 'degraded']),
        "backhaul_status": random.choice(['connected', 'connected', 'connected', 'degraded']),
        "backhaul_type": "Fiber",
        "backhaul_capacity_mbps": 1000,
        "last_reboot": (now - timedelta(days=random.randint(1, 90))).isoformat(),
        "uptime_hours": random.randint(24, 2160),
        "last_config_change": (now - timedelta(days=random.randint(1, 30))).isoformat(),
    }

    return {
        "node_id": node_id,
        "aau_units": aau_units,
        "bbu": bbu_unit,
        "hvac": hvac_unit,
        "power": power_system,
        "summary": {
            "total_aau": len(aau_units),
            "aau_status": "healthy" if all(a['status'] == 'operational' for a in aau_units) else "degraded",
            "bbu_status": bbu_unit['status'],
            "hvac_status": hvac_unit['status'],
            "power_status": power_system['grid_status'],
            "overall_health": "healthy" if (
                all(a['status'] == 'operational' for a in aau_units) and
                bbu_unit['status'] == 'operational' and
                hvac_unit['status'] == 'operational' and
                power_system['grid_status'] == 'connected'
            ) else "degraded"
        }
    }


@router.get("/nodes/{node_id}/equipment/history")
def get_node_equipment_history(
    node_id: str,
    days: int = Query(7, ge=1, le=30, description="Number of days of history"),
    db: Session = Depends(get_db)
):
    """Get 7-day historical equipment metrics for a node (AAU, BBU, HVAC, Power trends)"""
    import random
    import math
    from datetime import datetime, timedelta

    # Check if node exists
    node_query = select(FiberNodeModel).where(FiberNodeModel.node_id == node_id)
    node = db.execute(node_query).scalar_one_or_none()
    if not node:
        raise HTTPException(status_code=404, detail=f"Node {node_id} not found")

    # Use node_id hash for consistent base random values
    seed = sum(ord(c) for c in node_id)
    random.seed(seed)

    # Base values for this node (consistent)
    base_aau_temp = random.uniform(30, 45)
    base_aau_efficiency = random.uniform(82, 95)
    base_bbu_cpu = random.uniform(35, 60)
    base_bbu_memory = random.uniform(40, 65)
    base_bbu_temp = random.uniform(35, 48)
    base_hvac_temp = random.uniform(20, 24)
    base_hvac_setpoint = random.uniform(21, 24)
    base_power_load = random.uniform(1.5, 3.5)
    base_power_max = base_power_load * random.uniform(1.3, 1.8)
    base_battery_health = random.uniform(82, 98)

    now = datetime.now()
    history = []

    # Generate hourly data points for the requested days
    # Use 4-hour intervals to keep data manageable (6 points per day)
    interval_hours = 4
    num_points = (days * 24) // interval_hours

    for i in range(num_points):
        hours_ago = i * interval_hours
        timestamp = now - timedelta(hours=hours_ago)

        # Add realistic time-based variations
        hour_of_day = timestamp.hour
        day_of_week = timestamp.weekday()

        # Daily cycle: higher load during business hours (8-18)
        daily_factor = 1.0 + 0.15 * math.sin((hour_of_day - 6) * math.pi / 12) if 6 <= hour_of_day <= 18 else 0.85

        # Weekly cycle: slightly lower on weekends
        weekly_factor = 0.9 if day_of_week >= 5 else 1.0

        # Add some random noise (seeded by timestamp for consistency)
        random.seed(seed + int(timestamp.timestamp()))
        noise = random.uniform(-0.1, 0.1)

        # Calculate values with variations
        load_factor = daily_factor * weekly_factor * (1 + noise)
        temp_factor = 1 + (load_factor - 1) * 0.3  # Temperature correlates with load

        # AAU metrics (average across units)
        aau_temp = base_aau_temp * temp_factor + random.uniform(-3, 3)
        aau_efficiency = base_aau_efficiency - (aau_temp - base_aau_temp) * 0.3 + random.uniform(-2, 2)
        aau_efficiency = max(70, min(99, aau_efficiency))

        # BBU metrics
        bbu_cpu = base_bbu_cpu * load_factor + random.uniform(-5, 5)
        bbu_cpu = max(15, min(95, bbu_cpu))
        bbu_memory = base_bbu_memory * (1 + noise * 0.5) + random.uniform(-3, 3)
        bbu_memory = max(25, min(90, bbu_memory))
        bbu_temp = base_bbu_temp * temp_factor + random.uniform(-2, 2)

        # HVAC metrics
        hvac_current_temp = base_hvac_temp + (load_factor - 1) * 8 + random.uniform(-1, 1)
        hvac_humidity = 40 + random.uniform(-8, 8)
        hvac_power = 800 * load_factor + random.uniform(-100, 100)

        # Power metrics
        power_load = base_power_load * load_factor + random.uniform(-0.2, 0.2)
        power_load = max(0.5, power_load)
        grid_voltage = 230 + random.uniform(-5, 5)
        battery_health = base_battery_health - (i * 0.002) + random.uniform(-0.5, 0.5)  # Slight degradation over time
        battery_health = max(70, min(100, battery_health))

        history.append({
            "timestamp": timestamp.isoformat(),
            "aau": {
                "avg_temperature_celsius": round(aau_temp, 1),
                "avg_efficiency_percent": round(aau_efficiency, 1),
                "units_operational": random.choice([3, 3, 3, 3, 2]) if random.random() > 0.1 else 2,
                "total_units": 3,
            },
            "bbu": {
                "cpu_utilization_percent": round(bbu_cpu, 1),
                "memory_utilization_percent": round(bbu_memory, 1),
                "temperature_celsius": round(bbu_temp, 1),
                "throughput_gbps": round(random.uniform(2, 12) * load_factor, 2),
            },
            "hvac": {
                "current_temp_celsius": round(hvac_current_temp, 1),
                "setpoint_celsius": round(base_hvac_setpoint, 1),
                "humidity_percent": round(hvac_humidity, 1),
                "power_consumption_watts": round(hvac_power, 0),
                "compressor_running": random.random() > 0.2,
            },
            "power": {
                "current_load_kw": round(power_load, 2),
                "max_load_kw": round(base_power_max, 2),
                "load_percent": round((power_load / base_power_max) * 100, 1),
                "grid_voltage": round(grid_voltage, 1),
                "battery_health_percent": round(battery_health, 1),
                "ups_on_battery": random.random() < 0.02,  # Rare
            },
        })

    # Calculate statistics for the period
    aau_temps = [h['aau']['avg_temperature_celsius'] for h in history]
    aau_effs = [h['aau']['avg_efficiency_percent'] for h in history]
    bbu_cpus = [h['bbu']['cpu_utilization_percent'] for h in history]
    bbu_mems = [h['bbu']['memory_utilization_percent'] for h in history]
    bbu_temps = [h['bbu']['temperature_celsius'] for h in history]
    hvac_temps = [h['hvac']['current_temp_celsius'] for h in history]
    power_loads = [h['power']['current_load_kw'] for h in history]
    battery_healths = [h['power']['battery_health_percent'] for h in history]

    def calc_stats(values):
        return {
            "min": round(min(values), 1),
            "max": round(max(values), 1),
            "avg": round(sum(values) / len(values), 1),
            "current": round(values[0], 1),  # Most recent
        }

    def calc_trend(values):
        """Calculate if trending up, down, or stable"""
        if len(values) < 2:
            return "stable"
        recent_avg = sum(values[:len(values)//4]) / (len(values)//4) if len(values) >= 4 else values[0]
        older_avg = sum(values[-(len(values)//4):]) / (len(values)//4) if len(values) >= 4 else values[-1]
        diff_percent = ((recent_avg - older_avg) / older_avg) * 100 if older_avg != 0 else 0
        if diff_percent > 5:
            return "increasing"
        elif diff_percent < -5:
            return "decreasing"
        return "stable"

    return {
        "node_id": node_id,
        "period_days": days,
        "data_points": len(history),
        "interval_hours": interval_hours,
        "generated_at": now.isoformat(),
        "history": history[::-1],  # Oldest first for charting
        "statistics": {
            "aau": {
                "temperature": {**calc_stats(aau_temps), "trend": calc_trend(aau_temps), "unit": "\u00b0C"},
                "efficiency": {**calc_stats(aau_effs), "trend": calc_trend(aau_effs), "unit": "%"},
            },
            "bbu": {
                "cpu_utilization": {**calc_stats(bbu_cpus), "trend": calc_trend(bbu_cpus), "unit": "%"},
                "memory_utilization": {**calc_stats(bbu_mems), "trend": calc_trend(bbu_mems), "unit": "%"},
                "temperature": {**calc_stats(bbu_temps), "trend": calc_trend(bbu_temps), "unit": "\u00b0C"},
            },
            "hvac": {
                "temperature": {**calc_stats(hvac_temps), "trend": calc_trend(hvac_temps), "unit": "\u00b0C"},
            },
            "power": {
                "load": {**calc_stats(power_loads), "trend": calc_trend(power_loads), "unit": "kW"},
                "battery_health": {**calc_stats(battery_healths), "trend": calc_trend(battery_healths), "unit": "%"},
            },
        },
    }
