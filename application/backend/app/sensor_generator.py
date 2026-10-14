"""
Sensor Data Generator - Creates realistic RF plant, modem, and environmental sensor data
for Cable Network ISP Data Lakehouse.
Ported from TypeScript sensorDataGenerator.ts for backend autonomous AI analysis.
"""

import random
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from enum import Enum


class NodeStatus(str, Enum):
    OPERATIONAL = "operational"
    DEGRADED = "degraded"
    FAILED = "failed"
    MAINTENANCE = "maintenance"


class NetworkElementStatus(str, Enum):
    OPERATIONAL = "operational"
    DEGRADED = "degraded"
    FAILED = "failed"
    MAINTENANCE = "maintenance"


# Helper functions
def generate_id(prefix: str) -> str:
    """Generate a unique ID with prefix"""
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def random_in_range(min_val: float, max_val: float) -> float:
    """Generate random float in range"""
    return random.uniform(min_val, max_val)


def random_int(min_val: int, max_val: int) -> int:
    """Generate random integer in range (inclusive)"""
    return random.randint(min_val, max_val)


def random_choice(options: List[Any]) -> Any:
    """Random choice from list"""
    return random.choice(options)


# ============================================
# RF Plant Sensor Data
# ============================================

def generate_rf_plant_sensor_data(
    node: Dict[str, Any],
    timestamp: Optional[datetime] = None
) -> Dict[str, Any]:
    """Generate RF plant sensor data for a fiber node (SNR, power levels, FEC, etc.)"""
    if timestamp is None:
        timestamp = datetime.now()

    node_status = node.get('status', 'operational')
    docsis_version = node.get('docsis_version', '3.1')

    # Determine degradation based on node status
    is_failed = node_status in [NodeStatus.FAILED, 'failed']
    is_degraded = node_status in [NodeStatus.DEGRADED, 'degraded']
    has_rf_issue = is_failed or (is_degraded and random.random() < 0.6)

    # Downstream power level (nominal: -7 to +7 dBmV, out of spec: beyond +/- 10)
    if has_rf_issue:
        ds_power = random_in_range(-15, -10) if random.random() < 0.5 else random_in_range(10, 17)
    else:
        ds_power = random_in_range(-5, 7)

    # Upstream power level (nominal: 35-49 dBmV, high is bad)
    if has_rf_issue:
        us_power = random_in_range(50, 58)
    else:
        us_power = random_in_range(35, 49)

    # Downstream SNR (good: > 33 dB, marginal: 30-33, bad: < 30)
    if is_failed:
        ds_snr = random_in_range(18, 28)
    elif has_rf_issue:
        ds_snr = random_in_range(28, 33)
    else:
        ds_snr = random_in_range(35, 42)

    # Upstream SNR (good: > 25 dB, marginal: 22-25, bad: < 22)
    if is_failed:
        us_snr = random_in_range(14, 20)
    elif has_rf_issue:
        us_snr = random_in_range(20, 25)
    else:
        us_snr = random_in_range(27, 35)

    # MER (Modulation Error Ratio) - DOCSIS 3.1/4.0
    ds_mer = ds_snr + random_in_range(-2, 2)
    us_mer = us_snr + random_in_range(-2, 2)

    # FEC (Forward Error Correction) codewords
    if is_failed:
        fec_corrected = random_int(5000, 50000)
        fec_uncorrected = random_int(500, 5000)
    elif has_rf_issue:
        fec_corrected = random_int(1000, 10000)
        fec_uncorrected = random_int(50, 500)
    else:
        fec_corrected = random_int(0, 500)
        fec_uncorrected = random_int(0, 10)

    # T3/T4 timeouts (ranging timeouts - indicator of upstream issues)
    if is_failed:
        t3_timeouts = random_int(50, 500)
        t4_timeouts = random_int(10, 100)
    elif has_rf_issue:
        t3_timeouts = random_int(10, 50)
        t4_timeouts = random_int(1, 10)
    else:
        t3_timeouts = random_int(0, 5)
        t4_timeouts = random_int(0, 2)

    # Channel utilization
    ds_channels = node.get('downstream_channels', 32)
    us_channels = node.get('upstream_channels', 4)
    ofdm_channels = node.get('ofdm_channels', 2)

    return {
        'sensor_id': generate_id('rf-plant'),
        'node_id': node.get('node_id', ''),
        'timestamp': timestamp.isoformat(),
        # Power levels
        'ds_power_level_dbmv': round(ds_power, 2),
        'us_power_level_dbmv': round(us_power, 2),
        # Signal quality
        'ds_snr_db': round(ds_snr, 2),
        'us_snr_db': round(us_snr, 2),
        'ds_mer_db': round(ds_mer, 2),
        'us_mer_db': round(us_mer, 2),
        # FEC
        'fec_corrected_codewords': fec_corrected,
        'fec_uncorrected_codewords': fec_uncorrected,
        # Timeouts
        't3_timeouts': t3_timeouts,
        't4_timeouts': t4_timeouts,
        # Channel info
        'ds_channel_count': ds_channels,
        'us_channel_count': us_channels,
        'ofdm_channel_count': ofdm_channels,
        'ds_channel_utilization_percent': round(random_in_range(70, 95) if has_rf_issue else random_in_range(30, 70), 2),
        'us_channel_utilization_percent': round(random_in_range(60, 90) if has_rf_issue else random_in_range(20, 60), 2),
        'ofdm_utilization_percent': round(random_in_range(50, 85) if has_rf_issue else random_in_range(15, 50), 2),
        # Frequency plan
        'docsis_version': docsis_version,
    }


# ============================================
# Modem Telemetry Data
# ============================================

def generate_modem_telemetry(
    node: Dict[str, Any],
    timestamp: Optional[datetime] = None
) -> Dict[str, Any]:
    """Generate modem telemetry data for a node - aggregate modem health"""
    if timestamp is None:
        timestamp = datetime.now()

    node_status = node.get('status', 'operational')
    homes_active = node.get('homes_active', 200)
    is_failed = node_status in [NodeStatus.FAILED, 'failed']
    is_degraded = node_status in [NodeStatus.DEGRADED, 'degraded']

    # Modem counts
    total_modems = int(homes_active * random_in_range(0.85, 0.95))

    if is_failed:
        offline_modems = int(total_modems * random_in_range(0.3, 0.8))
        flapping_modems = int(total_modems * random_in_range(0.1, 0.3))
    elif is_degraded:
        offline_modems = int(total_modems * random_in_range(0.05, 0.15))
        flapping_modems = int(total_modems * random_in_range(0.05, 0.15))
    else:
        offline_modems = int(total_modems * random_in_range(0.01, 0.04))
        flapping_modems = int(total_modems * random_in_range(0.005, 0.03))

    registered_modems = total_modems - offline_modems
    active_modems = int(registered_modems * random_in_range(0.7, 0.95))

    # DOCSIS version distribution
    d30_pct = random_in_range(0.10, 0.25)
    d31_pct = random_in_range(0.50, 0.70)
    d40_pct = 1.0 - d30_pct - d31_pct

    # Modem manufacturer distribution
    manufacturers = {
        'ARRIS/CommScope': round(random_in_range(0.3, 0.45), 3),
        'Motorola': round(random_in_range(0.15, 0.25), 3),
        'Netgear': round(random_in_range(0.10, 0.20), 3),
        'Hitron': round(random_in_range(0.05, 0.15), 3),
        'Other': 0,
    }
    manufacturers['Other'] = round(1.0 - sum(manufacturers.values()), 3)

    return {
        'sensor_id': generate_id('modem-telemetry'),
        'node_id': node.get('node_id', ''),
        'timestamp': timestamp.isoformat(),
        # Modem counts
        'total_modems': total_modems,
        'active_modems': active_modems,
        'registered_modems': registered_modems,
        'offline_modems': offline_modems,
        'flapping_modems': flapping_modems,
        # Ranging stats
        'ranging_success_rate': round(random_in_range(85, 95) if is_degraded else random_in_range(96, 99.5), 2),
        'partial_service_modems': random_int(1, 10) if is_degraded else random_int(0, 2),
        # Version distribution
        'docsis_30_percent': round(d30_pct * 100, 1),
        'docsis_31_percent': round(d31_pct * 100, 1),
        'docsis_40_percent': round(d40_pct * 100, 1),
        # Manufacturer distribution
        'manufacturer_distribution': manufacturers,
        # Average modem metrics
        'avg_modem_uptime_hours': round(random_in_range(100, 2000), 1),
        'avg_modem_reboots_24h': round(random_in_range(0.5, 3.0) if is_degraded else random_in_range(0, 0.3), 2),
        'modems_needing_firmware_update': random_int(5, 50),
    }


# ============================================
# Weather Data (Cable Plant Impact)
# ============================================

def generate_weather_data(
    node: Dict[str, Any],
    timestamp: Optional[datetime] = None
) -> Dict[str, Any]:
    """Generate weather data for a node's location with cable plant impact assessment"""
    if timestamp is None:
        timestamp = datetime.now()

    latitude = node.get('latitude', 35.0)
    state = node.get('state', 'NC')

    # US-focused seasonal patterns
    is_winter = timestamp.month in [11, 12, 1, 2, 3]
    is_summer = timestamp.month in [6, 7, 8]
    is_hurricane_season = timestamp.month in [6, 7, 8, 9, 10]

    # Determine weather conditions
    weather_roll = random.random()
    precipitation = 0.0
    visibility = random_in_range(8, 15)

    if weather_roll < 0.55:
        conditions = 'clear'
        precipitation = 0
    elif weather_roll < 0.75:
        conditions = 'cloudy'
        precipitation = 0
    elif weather_roll < 0.88:
        if is_winter and latitude > 37:
            conditions = 'snow'
            precipitation = random_in_range(2, 20)
        else:
            conditions = 'rain'
            precipitation = random_in_range(1, 15)
        visibility = random_in_range(2, 8)
    elif weather_roll < 0.94:
        conditions = 'fog'
        precipitation = 0
        visibility = random_in_range(0.5, 3)
    elif weather_roll < 0.98:
        conditions = 'storm'
        precipitation = random_in_range(10, 40)
        visibility = random_in_range(1, 5)
    else:
        if is_hurricane_season and latitude < 35:
            conditions = 'hurricane_warning'
        else:
            conditions = 'extreme'
        precipitation = random_in_range(30, 80)
        visibility = random_in_range(0.2, 2)

    # Temperature based on US region and season
    if latitude > 42:  # Northern (NYC, Chicago, Seattle)
        base_temp = random_in_range(-10, 5) if is_winter else random_in_range(20, 32)
    elif latitude > 35:  # Mid-Atlantic (Charlotte, Columbus, Denver)
        base_temp = random_in_range(-2, 12) if is_winter else random_in_range(25, 36)
    else:  # Southern (Tampa, Dallas, LA, Atlanta)
        base_temp = random_in_range(5, 18) if is_winter else random_in_range(28, 40)

    temperature = base_temp + random_in_range(-3, 3)

    # Wind speed
    extreme_weather = conditions in ['storm', 'extreme', 'hurricane_warning']
    wind_speed = random_in_range(50, 130) if extreme_weather else random_in_range(5, 35)
    lightning_detected = extreme_weather and random.random() < 0.35

    # Cable plant specific weather impacts
    plant_impact = _assess_cable_plant_weather_impact(
        conditions, wind_speed, temperature, precipitation, lightning_detected,
        node.get('node_type', 'N+1')
    )

    return {
        'weather_id': generate_id('weather'),
        'node_id': node.get('node_id', ''),
        'timestamp': timestamp.isoformat(),
        'temperature_celsius': round(temperature, 1),
        'humidity_percent': round(
            random_in_range(70, 95) if conditions in ['rain', 'fog', 'snow'] else random_in_range(30, 70), 1
        ),
        'wind_speed_kmh': round(wind_speed, 1),
        'wind_direction': random_int(0, 359),
        'precipitation_mm': round(precipitation, 1),
        'atmospheric_pressure_hpa': round(random_in_range(980, 1030), 1),
        'visibility_km': round(visibility, 1),
        'conditions': conditions,
        'lightning_detected': lightning_detected,
        # Cable plant specific
        'plant_impact': plant_impact,
    }


def _assess_cable_plant_weather_impact(
    conditions: str, wind_speed: float, temperature: float,
    precipitation: float, lightning: bool, node_type: str
) -> Dict[str, Any]:
    """Assess weather impact on cable plant infrastructure"""
    impact_score = 0.0
    risks = []

    # Wind impact on aerial plant
    if wind_speed > 80:
        impact_score += 0.4
        risks.append('high_wind_aerial_damage')
    elif wind_speed > 50:
        impact_score += 0.15
        risks.append('moderate_wind_risk')

    # Ice/snow loading on aerial cable
    if conditions == 'snow' and temperature < 0:
        impact_score += 0.3
        risks.append('ice_loading_aerial_cable')

    # Lightning surge risk
    if lightning:
        impact_score += 0.35
        risks.append('lightning_surge_risk')

    # Flooding impact on pedestal/underground equipment
    if precipitation > 25:
        impact_score += 0.25
        risks.append('flooding_pedestal_risk')
    elif precipitation > 10:
        impact_score += 0.1
        risks.append('moisture_ingress_risk')

    # Temperature extremes
    if temperature > 38:
        impact_score += 0.15
        risks.append('heat_amplifier_stress')
    elif temperature < -10:
        impact_score += 0.2
        risks.append('cold_connector_contraction')

    # N+0 nodes are more resilient (fiber deep, fewer amplifiers)
    if node_type == 'N+0':
        impact_score *= 0.5
    elif node_type == 'N+3':
        impact_score *= 1.3  # Longer cascade = more vulnerable

    return {
        'impact_score': round(min(impact_score, 1.0), 3),
        'risks': risks,
        'aerial_plant_risk': 'high' if wind_speed > 80 or (conditions == 'snow' and temperature < 0) else 'low',
        'pedestal_risk': 'high' if precipitation > 25 else 'low',
        'amplifier_risk': 'high' if temperature > 40 or lightning else 'moderate' if temperature > 35 else 'low',
        'recommended_actions': _weather_recommended_actions(risks),
    }


def _weather_recommended_actions(risks: List[str]) -> List[str]:
    """Generate recommended actions based on weather risks"""
    actions = []
    if 'high_wind_aerial_damage' in risks:
        actions.append('Dispatch aerial crew for post-storm plant inspection')
        actions.append('Pre-position spare cable and hardware')
    if 'ice_loading_aerial_cable' in risks:
        actions.append('Monitor for span failures from ice loading')
        actions.append('Prepare de-icing crews')
    if 'lightning_surge_risk' in risks:
        actions.append('Verify surge protector status on amplifiers and nodes')
        actions.append('Monitor power supply voltages post-lightning')
    if 'flooding_pedestal_risk' in risks:
        actions.append('Check pedestal seals and drainage')
        actions.append('Prepare submersible splice kits')
    if 'heat_amplifier_stress' in risks:
        actions.append('Monitor amplifier temperatures and auto-gain')
    if 'cold_connector_contraction' in risks:
        actions.append('Check for signal level changes from connector contraction')
    return actions


# ============================================
# Environmental Sensor Data
# ============================================

def generate_environmental_sensor(
    node: Dict[str, Any],
    timestamp: Optional[datetime] = None
) -> Dict[str, Any]:
    """Generate environmental sensor data for node housing/cabinet"""
    if timestamp is None:
        timestamp = datetime.now()

    node_status = node.get('status', 'operational')
    has_power_issue = (node_status in [NodeStatus.FAILED, 'failed']) and random.random() < 0.3
    has_ingress_issue = (node_status in [NodeStatus.DEGRADED, 'degraded']) and random.random() < 0.4

    # Power supply monitoring
    power_supply_count = node.get('power_supply_count', 2)
    ps_status = node.get('power_supply_status', 'all_ok')

    # Node housing status
    housing_roll = random.random()
    if housing_roll < 0.97:
        housing_status = 'sealed'
    elif housing_roll < 0.99:
        housing_status = 'open'
    else:
        housing_status = 'tampered'

    return {
        'sensor_id': generate_id('env-sensor'),
        'node_id': node.get('node_id', ''),
        'timestamp': timestamp.isoformat(),
        # Power monitoring
        'power_supply_voltage': round(random_in_range(50, 65) if has_power_issue else random_in_range(87, 93), 2),
        'power_quality_percent': round(random_in_range(40, 75) if has_power_issue else random_in_range(90, 100), 2),
        'power_fluctuations_count': random_int(10, 50) if has_power_issue else random_int(0, 3),
        'battery_backup_voltage': round(random_in_range(20, 36) if has_power_issue else random_in_range(46, 52), 2),
        'battery_backup_percent': round(random_in_range(20, 60) if has_power_issue else random_in_range(80, 100), 1),
        # RF ingress monitoring
        'ingress_level_dbmv': round(random_in_range(-30, -15) if has_ingress_issue else random_in_range(-55, -35), 2),
        'noise_floor_dbmv': round(random_in_range(-25, -15) if has_ingress_issue else random_in_range(-45, -30), 2),
        'return_path_noise_db': round(random_in_range(15, 25) if has_ingress_issue else random_in_range(0, 10), 2),
        # Physical
        'cabinet_temperature_celsius': round(random_in_range(35, 55) if has_power_issue else random_in_range(20, 35), 1),
        'cabinet_humidity_percent': round(random_in_range(50, 80) if housing_status != 'sealed' else random_in_range(20, 45), 1),
        'housing_status': housing_status,
        # Ground
        'ground_resistance_ohms': round(random_in_range(10, 50) if has_power_issue else random_in_range(2, 10), 2),
        # Power supply details
        'power_supply_count': power_supply_count,
        'power_supply_status': ps_status,
    }


# ============================================
# Equipment Sensor Data (CMTS / Node Hardware)
# ============================================

NODE_MANUFACTURERS = ['Cisco', 'CommScope/ARRIS', 'Harmonic', 'Technetix', 'ATX Networks']
CMTS_MODELS = {
    'Cisco': ['cBR-8 Sup250', 'cBR-8 Sup160'],
    'Casa': ['C100G', 'C10G'],
    'Harmonic': ['CableOS 2.0', 'CableOS 1.5'],
}

HVAC_MANUFACTURERS = ['Emerson', 'Vertiv', 'Schneider', 'Delta', 'Stulz']
HVAC_MODELS = {
    'Emerson': ['NetSure 7100', 'NetSure 5100', 'Liebert CRV'],
    'Vertiv': ['Smartcool DSE', 'Smartcool ACU', 'Liebert HPM'],
    'Schneider': ['InRow RD', 'InRow RC', 'Uniflair LE'],
    'Delta': ['DPH Series', 'DPH Ultra', 'RT Series'],
    'Stulz': ['CyberAir 3', 'MiniSpace', 'Compact DX'],
}


def generate_equipment_sensor_data(
    node: Dict[str, Any],
    timestamp: Optional[datetime] = None
) -> Dict[str, Any]:
    """Generate equipment sensor data for cable network node components"""
    if timestamp is None:
        timestamp = datetime.now()

    node_status = node.get('status', 'operational')
    has_equipment_issue = node_status in [NodeStatus.FAILED, 'failed', NodeStatus.DEGRADED, 'degraded']

    # Generate component health for cable network components
    component_health = []

    components = [
        {
            'component_name': 'Optical Receiver',
            'component_type': 'optical_rx',
            'degraded_chance': 0.25,
            'manufacturers': ['Cisco', 'Harmonic', 'CommScope/ARRIS'],
            'serial_prefix': 'ORX',
            'life_range': (730, 3650),
        },
        {
            'component_name': 'RF Amplifier Module',
            'component_type': 'rf_amplifier',
            'degraded_chance': 0.35,
            'manufacturers': ['Technetix', 'ATX Networks', 'CommScope/ARRIS'],
            'serial_prefix': 'AMP',
            'life_range': (365, 2555),
        },
        {
            'component_name': 'Return Path Transmitter',
            'component_type': 'return_tx',
            'degraded_chance': 0.30,
            'manufacturers': ['Cisco', 'Harmonic', 'Teleste'],
            'serial_prefix': 'RTX',
            'life_range': (730, 2555),
        },
        {
            'component_name': 'Power Supply Unit',
            'component_type': 'power_supply',
            'degraded_chance': 0.20,
            'manufacturers': ['Alpha Technologies', 'Emerson', 'Delta'],
            'serial_prefix': 'PSU',
            'life_range': (365, 2190),
        },
        {
            'component_name': 'Battery Backup',
            'component_type': 'battery',
            'degraded_chance': 0.15,
            'manufacturers': ['Alpha Technologies', 'Emerson'],
            'serial_prefix': 'BAT',
            'life_range': (365, 1825),
        },
    ]

    for comp in components:
        is_degraded = has_equipment_issue and random.random() < comp['degraded_chance']

        days_since_maintenance = random_int(60, 365)
        last_maintenance = timestamp - timedelta(days=days_since_maintenance)

        component_health.append({
            'component_name': comp['component_name'],
            'component_type': comp['component_type'],
            'health_score': round(random_in_range(50, 80) if is_degraded else random_in_range(85, 100), 1),
            'status': 'degraded' if is_degraded else 'healthy',
            'last_maintenance': last_maintenance.isoformat(),
            'estimated_remaining_life_days': random_int(*comp['life_range']),
            'manufacturer': random_choice(comp['manufacturers']),
            'serial_number': f"{comp['serial_prefix']}-{random_int(100000, 999999)}",
        })

    # Mark a component as failed if node is in outage
    if node_status in [NodeStatus.FAILED, 'failed'] and random.random() < 0.5:
        failed_idx = random_int(0, len(component_health) - 1)
        component_health[failed_idx]['status'] = 'failed'
        component_health[failed_idx]['health_score'] = round(random_in_range(0, 30), 1)

    hours_since_reboot = random_int(1, 720)
    last_reboot = timestamp - timedelta(hours=hours_since_reboot)

    return {
        'sensor_id': generate_id('equipment-sensor'),
        'node_id': node.get('node_id', ''),
        'timestamp': timestamp.isoformat(),
        'component_health': component_health,
        'firmware_version': node.get('firmware_version', f"v{random_int(2, 5)}.{random_int(0, 20)}.{random_int(0, 100)}"),
        'last_reboot': last_reboot.isoformat(),
        'uptime_hours': round(random_in_range(1, 4380), 1),  # Up to ~6 months
        'error_log_count': random_int(10, 100) if has_equipment_issue else random_int(0, 5),
        'warning_log_count': random_int(20, 150) if has_equipment_issue else random_int(0, 15),
        'node_cpu_utilization': round(random_in_range(60, 95) if has_equipment_issue else random_in_range(15, 50), 2),
        'node_memory_utilization': round(random_in_range(70, 95) if has_equipment_issue else random_in_range(20, 60), 2),
        'node_temperature_celsius': round(random_in_range(55, 75) if has_equipment_issue else random_in_range(30, 50), 1),
        'power_consumption_watts': round(random_in_range(80, 250), 1),
    }


# ============================================
# HVAC Unit Generator (for Headends/Hubs)
# ============================================

def generate_hvac_unit(facility: Dict[str, Any]) -> Dict[str, Any]:
    """Generate HVAC Unit for a headend or hub facility"""
    manufacturer = random_choice(HVAC_MANUFACTURERS)
    models = HVAC_MODELS[manufacturer]

    has_hvac_issue = random.random() < 0.05
    status = NetworkElementStatus.OPERATIONAL
    compressor_status = 'running' if random.random() < 0.7 else 'idle'
    filter_condition = 'good'

    if has_hvac_issue:
        status = random_choice([NetworkElementStatus.DEGRADED, NetworkElementStatus.FAILED])
        compressor_status = 'fault' if random.random() < 0.5 else 'running'
        filter_condition = random_choice(['replace_soon', 'replace_now'])
    elif random.random() < 0.2:
        filter_condition = 'replace_soon'

    setpoint = random_in_range(18, 22)
    current_temp = random_in_range(28, 42) if has_hvac_issue else random_in_range(setpoint - 2, setpoint + 2)

    if current_temp > setpoint:
        mode = 'cooling'
    else:
        mode = 'auto'

    installed_days_ago = random_int(365, 2555)
    maintenance_days_ago = random_int(30, 180)
    filter_change_days_ago = random_int(30, 365)

    facility_id = facility.get('headend_id', facility.get('hub_id', ''))

    return {
        'hvac_id': generate_id('HVAC'),
        'facility_id': facility_id,
        'manufacturer': manufacturer,
        'model': random_choice(models),
        'serial_number': f"HVAC-{random_int(100000, 999999)}",
        'status': status.value,
        # Operational parameters
        'cooling_capacity_kw': round(random_in_range(10, 50), 1),
        'heating_capacity_kw': round(random_in_range(5, 20), 1),
        'current_mode': mode,
        'setpoint_celsius': round(setpoint, 1),
        'current_temp_celsius': round(current_temp, 1),
        'humidity_percent': round(random_in_range(30, 60), 1),
        # Performance
        'power_consumption_watts': round(random_in_range(2000, 8000), 1),
        'compressor_status': compressor_status,
        'filter_condition': filter_condition,
        'refrigerant_level_percent': round(random_in_range(60, 85) if has_hvac_issue else random_in_range(90, 100), 1),
        # Alarms
        'high_temp_alarm': current_temp > 38,
        'low_temp_alarm': current_temp < 10,
        'compressor_fault': compressor_status == 'fault',
        # Timestamps
        'installed_date': (datetime.now() - timedelta(days=installed_days_ago)).isoformat(),
        'last_maintenance': (datetime.now() - timedelta(days=maintenance_days_ago)).isoformat(),
        'last_filter_change': (datetime.now() - timedelta(days=filter_change_days_ago)).isoformat(),
    }


# ============================================
# Amplifier Sensor Data
# ============================================

def generate_amplifier_sensor_data(
    amplifier: Dict[str, Any],
    timestamp: Optional[datetime] = None
) -> Dict[str, Any]:
    """Generate sensor data for an RF amplifier in the HFC plant"""
    if timestamp is None:
        timestamp = datetime.now()

    amp_status = amplifier.get('status', 'operational')
    amp_type = amplifier.get('amp_type', 'trunk')
    location_type = amplifier.get('location_type', 'aerial')
    is_degraded = amp_status in ['degraded', 'failed']

    # RF levels vary by amp type
    if amp_type == 'trunk':
        ds_input = random_in_range(10, 18) if not is_degraded else random_in_range(5, 10)
        ds_output = random_in_range(32, 40) if not is_degraded else random_in_range(25, 32)
    elif amp_type == 'bridger':
        ds_input = random_in_range(15, 22) if not is_degraded else random_in_range(8, 15)
        ds_output = random_in_range(38, 46) if not is_degraded else random_in_range(30, 38)
    else:  # line_extender, distribution
        ds_input = random_in_range(8, 15) if not is_degraded else random_in_range(3, 8)
        ds_output = random_in_range(28, 36) if not is_degraded else random_in_range(20, 28)

    us_input = random_in_range(15, 25) if not is_degraded else random_in_range(8, 15)
    us_output = random_in_range(30, 42) if not is_degraded else random_in_range(20, 30)

    return {
        'sensor_id': generate_id('amp-sensor'),
        'amp_id': amplifier.get('amp_id', ''),
        'node_id': amplifier.get('node_id', ''),
        'timestamp': timestamp.isoformat(),
        'amp_type': amp_type,
        'location_type': location_type,
        'cascade_position': amplifier.get('cascade_position', 0),
        # RF levels
        'ds_input_level_dbmv': round(ds_input, 2),
        'ds_output_level_dbmv': round(ds_output, 2),
        'us_input_level_dbmv': round(us_input, 2),
        'us_output_level_dbmv': round(us_output, 2),
        # Signal quality
        'ds_snr_db': round(random_in_range(28, 35) if is_degraded else random_in_range(36, 44), 2),
        'us_snr_db': round(random_in_range(18, 24) if is_degraded else random_in_range(26, 35), 2),
        # Equipment
        'temperature_celsius': round(random_in_range(50, 70) if is_degraded else random_in_range(25, 45), 1),
        'power_consumption_watts': round(random_in_range(20, 80), 1),
        'power_supply_status': 'degraded' if (is_degraded and random.random() < 0.3) else 'normal',
        'auto_gain_active': random.random() < 0.3,
        'gain_db': round(random_in_range(18, 30), 1),
    }


# ============================================
# Aggregate Functions
# ============================================

def generate_all_sensor_data(
    node: Dict[str, Any],
    timestamp: Optional[datetime] = None
) -> Dict[str, Any]:
    """Generate all sensor data for a fiber node"""
    if timestamp is None:
        timestamp = datetime.now()

    return {
        'rf_plant': generate_rf_plant_sensor_data(node, timestamp),
        'modem_telemetry': generate_modem_telemetry(node, timestamp),
        'weather': generate_weather_data(node, timestamp),
        'environmental': generate_environmental_sensor(node, timestamp),
        'equipment': generate_equipment_sensor_data(node, timestamp),
    }


def generate_sensor_data_batch(
    nodes: List[Dict[str, Any]],
    timestamp: Optional[datetime] = None
) -> Dict[str, List[Dict[str, Any]]]:
    """Batch generate sensor data for multiple nodes"""
    if timestamp is None:
        timestamp = datetime.now()

    return {
        'rf_plant_sensors': [generate_rf_plant_sensor_data(node, timestamp) for node in nodes],
        'modem_telemetry': [generate_modem_telemetry(node, timestamp) for node in nodes],
        'weather_data': [generate_weather_data(node, timestamp) for node in nodes],
        'environmental_sensors': [generate_environmental_sensor(node, timestamp) for node in nodes],
        'equipment_sensors': [generate_equipment_sensor_data(node, timestamp) for node in nodes],
    }


def generate_network_elements(node: Dict[str, Any]) -> Dict[str, Any]:
    """Generate all network element sensor data for a node"""
    return {
        'rf_plant': generate_rf_plant_sensor_data(node),
        'modem_telemetry': generate_modem_telemetry(node),
        'hvac': generate_hvac_unit(node),
    }
