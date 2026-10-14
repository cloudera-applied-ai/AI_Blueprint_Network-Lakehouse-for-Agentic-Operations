/**
 * Sensor Data Generator - Creates realistic environmental and sensor data
 * Also generates network elements: AAU, HVAC, SMSC, HLR
 */

import {
  FiberNode,
  AntennaSensorData,
  WeatherData,
  EnvironmentalSensor,
  EquipmentSensorData,
  ComponentHealth,
  NodeStatus,
  AAU,
  HVACUnit,
  SMSC,
  HLR,
  NetworkElementStatus,
  GeographicRegion,
} from '@/types';
import { generateId, randomInRange, randomInt, randomChoice } from '@/utils/helpers';

/**
 * Generate antenna sensor data for a node
 */
export const generateAntennaSensorData = (
  node: FiberNode,
  timestamp: Date = new Date()
): AntennaSensorData => {
  // Determine if antenna has drift issues (more likely for degraded/outage nodes)
  const hasDriftIssue = node.status === NodeStatus.OUTAGE
    ? Math.random() < 0.7  // 70% chance if outage
    : node.status === NodeStatus.DEGRADED
      ? Math.random() < 0.4  // 40% chance if degraded
      : Math.random() < 0.05; // 5% chance if healthy

  // Normal antenna angles (most common configurations)
  const baseAzimuth = randomInt(0, 359);
  const baseTilt = randomInRange(-12, -2); // Most antennas have downtilt

  return {
    sensor_id: generateId('antenna-sensor'),
    node_id: node.node_id,
    timestamp,
    azimuth_angle: baseAzimuth + (hasDriftIssue ? randomInRange(-15, 15) : randomInRange(-2, 2)),
    tilt_angle: baseTilt + (hasDriftIssue ? randomInRange(-5, 5) : randomInRange(-0.5, 0.5)),
    azimuth_drift: hasDriftIssue ? randomInRange(3, 20) : randomInRange(0, 2),
    tilt_drift: hasDriftIssue ? randomInRange(2, 8) : randomInRange(0, 1),
    last_calibration: new Date(
      timestamp.getTime() - randomInt(30, 365) * 24 * 60 * 60 * 1000
    ),
    mechanical_health: hasDriftIssue ? randomInRange(40, 75) : randomInRange(85, 100),
    motor_status: hasDriftIssue
      ? randomChoice(['degraded', 'degraded', 'failed'] as const)
      : 'operational',
    vibration_level: hasDriftIssue ? randomInRange(40, 80) : randomInRange(5, 25),
  };
};

/**
 * Generate weather data for a node's location
 */
export const generateWeatherData = (
  node: FiberNode,
  timestamp: Date = new Date()
): WeatherData => {
  // Simulate regional weather patterns
  const isWinterHemisphere = node.latitude > 0
    ? timestamp.getMonth() >= 10 || timestamp.getMonth() <= 2
    : timestamp.getMonth() >= 4 && timestamp.getMonth() <= 8;

  // Determine weather conditions
  const weatherRoll = Math.random();
  let conditions: WeatherData['conditions'];
  let precipitation = 0;
  let visibility = randomInRange(8, 15);

  if (weatherRoll < 0.6) {
    conditions = 'clear';
    precipitation = 0;
  } else if (weatherRoll < 0.8) {
    conditions = 'cloudy';
    precipitation = 0;
  } else if (weatherRoll < 0.92) {
    conditions = isWinterHemisphere && node.latitude > 40 ? 'snow' : 'rain';
    precipitation = randomInRange(1, 15);
    visibility = randomInRange(2, 8);
  } else if (weatherRoll < 0.97) {
    conditions = 'fog';
    precipitation = 0;
    visibility = randomInRange(0.5, 3);
  } else if (weatherRoll < 0.99) {
    conditions = 'storm';
    precipitation = randomInRange(10, 40);
    visibility = randomInRange(1, 5);
  } else {
    conditions = 'extreme';
    precipitation = randomInRange(30, 80);
    visibility = randomInRange(0.2, 2);
  }

  // Temperature based on region and season
  let baseTemp = 20; // Default moderate
  if (node.latitude > 50 || node.latitude < -40) {
    baseTemp = isWinterHemisphere ? randomInRange(-15, 5) : randomInRange(10, 25);
  } else if (Math.abs(node.latitude) < 30) {
    baseTemp = randomInRange(22, 35); // Tropical
  } else {
    baseTemp = isWinterHemisphere ? randomInRange(-5, 15) : randomInRange(15, 30);
  }

  // Weather affects node performance
  const extremeWeather = conditions === 'storm' || conditions === 'extreme';
  const lightningDetected = extremeWeather && Math.random() < 0.3;

  return {
    weather_id: generateId('weather'),
    node_id: node.node_id,
    timestamp,
    temperature_celsius: baseTemp + randomInRange(-5, 5),
    humidity_percent: conditions === 'rain' || conditions === 'fog'
      ? randomInRange(70, 95)
      : randomInRange(30, 70),
    wind_speed_kmh: extremeWeather ? randomInRange(40, 120) : randomInRange(5, 30),
    wind_direction: randomInt(0, 359),
    precipitation_mm: precipitation,
    atmospheric_pressure_hpa: randomInRange(980, 1030),
    visibility_km: visibility,
    conditions,
    lightning_detected: lightningDetected,
  };
};

/**
 * Generate environmental sensor data
 */
export const generateEnvironmentalSensor = (
  node: FiberNode,
  timestamp: Date = new Date()
): EnvironmentalSensor => {
  const hasPowerIssue = node.status === NodeStatus.OUTAGE && Math.random() < 0.3;
  const hasInterferenceIssue = node.status === NodeStatus.DEGRADED && Math.random() < 0.4;

  return {
    sensor_id: generateId('env-sensor'),
    node_id: node.node_id,
    timestamp,
    power_quality: hasPowerIssue ? randomInRange(40, 75) : randomInRange(90, 100),
    power_fluctuations: hasPowerIssue ? randomInt(10, 50) : randomInt(0, 3),
    backup_battery_level: hasPowerIssue ? randomInRange(20, 60) : randomInRange(80, 100),
    interference_level: hasInterferenceIssue ? randomInRange(-70, -50) : randomInRange(-110, -85),
    noise_floor: hasInterferenceIssue ? randomInRange(-95, -80) : randomInRange(-120, -100),
    ground_resistance: randomInRange(5, 25),
    cabinet_temperature: randomInRange(20, 45),
    cabinet_humidity: randomInRange(20, 60),
    equipment_vibration: randomInRange(5, 30),
    door_status: Math.random() < 0.99 ? 'closed' : Math.random() < 0.8 ? 'open' : 'tampered',
  };
};

/**
 * Generate equipment sensor data with component health
 */
export const generateEquipmentSensorData = (
  node: FiberNode,
  timestamp: Date = new Date()
): EquipmentSensorData => {
  const hasEquipmentIssue = node.status === NodeStatus.OUTAGE || node.status === NodeStatus.DEGRADED;

  // Generate component health for all major components
  const componentHealth: ComponentHealth[] = [
    {
      component_name: 'Baseband Unit',
      component_type: 'baseband',
      health_score: hasEquipmentIssue ? randomInRange(50, 80) : randomInRange(85, 100),
      status: hasEquipmentIssue && Math.random() < 0.3 ? 'degraded' : 'healthy',
      last_maintenance: new Date(timestamp.getTime() - randomInt(60, 365) * 24 * 60 * 60 * 1000),
      estimated_remaining_life_days: randomInt(365, 1825),
      manufacturer: randomChoice(['Ericsson', 'Nokia', 'Huawei', 'Samsung']),
      serial_number: `BBU-${randomInt(100000, 999999)}`,
    },
    {
      component_name: 'RF Unit',
      component_type: 'rf_unit',
      health_score: hasEquipmentIssue ? randomInRange(45, 75) : randomInRange(85, 100),
      status: hasEquipmentIssue && Math.random() < 0.4 ? 'degraded' : 'healthy',
      last_maintenance: new Date(timestamp.getTime() - randomInt(60, 365) * 24 * 60 * 60 * 1000),
      estimated_remaining_life_days: randomInt(365, 1825),
      manufacturer: randomChoice(['Ericsson', 'Nokia', 'Huawei', 'Samsung']),
      serial_number: `RFU-${randomInt(100000, 999999)}`,
    },
    {
      component_name: 'Antenna Array',
      component_type: 'antenna',
      health_score: hasEquipmentIssue ? randomInRange(55, 85) : randomInRange(90, 100),
      status: hasEquipmentIssue && Math.random() < 0.2 ? 'degraded' : 'healthy',
      last_maintenance: new Date(timestamp.getTime() - randomInt(180, 730) * 24 * 60 * 60 * 1000),
      estimated_remaining_life_days: randomInt(730, 3650),
      manufacturer: randomChoice(['Kathrein', 'CommScope', 'RFS']),
      serial_number: `ANT-${randomInt(100000, 999999)}`,
    },
    {
      component_name: 'Power Supply',
      component_type: 'power_supply',
      health_score: hasEquipmentIssue ? randomInRange(60, 80) : randomInRange(85, 100),
      status: hasEquipmentIssue && Math.random() < 0.25 ? 'degraded' : 'healthy',
      last_maintenance: new Date(timestamp.getTime() - randomInt(90, 365) * 24 * 60 * 60 * 1000),
      estimated_remaining_life_days: randomInt(365, 2190),
      manufacturer: randomChoice(['Emerson', 'Eltek', 'Delta']),
      serial_number: `PSU-${randomInt(100000, 999999)}`,
    },
    {
      component_name: 'Cooling System',
      component_type: 'cooling',
      health_score: randomInRange(80, 100),
      status: 'healthy',
      last_maintenance: new Date(timestamp.getTime() - randomInt(30, 180) * 24 * 60 * 60 * 1000),
      estimated_remaining_life_days: randomInt(365, 1825),
      manufacturer: randomChoice(['Pfannenberg', 'Rittal']),
      serial_number: `COOL-${randomInt(100000, 999999)}`,
    },
  ];

  // Mark components as failed if node is in outage
  if (node.status === NodeStatus.OUTAGE && Math.random() < 0.5) {
    const failedComponent = componentHealth[randomInt(0, componentHealth.length - 1)];
    failedComponent.status = 'failed';
    failedComponent.health_score = randomInRange(0, 30);
  }

  return {
    sensor_id: generateId('equipment-sensor'),
    node_id: node.node_id,
    timestamp,
    component_health: componentHealth,
    firmware_version: `v${randomInt(2, 5)}.${randomInt(0, 20)}.${randomInt(0, 100)}`,
    last_reboot: new Date(timestamp.getTime() - randomInt(1, 72) * 60 * 60 * 1000),
    uptime_hours: randomInRange(1, 720),
    error_log_count: hasEquipmentIssue ? randomInt(10, 100) : randomInt(0, 5),
    warning_log_count: hasEquipmentIssue ? randomInt(20, 150) : randomInt(0, 15),
    fan_speed_rpm: randomInt(2000, 4500),
    power_consumption_watts: randomInRange(800, 2500),
    signal_quality_db: hasEquipmentIssue ? randomInRange(-15, -8) : randomInRange(-8, -3),
  };
};

/**
 * Generate all sensor data for a node
 */
export const generateAllSensorData = (node: FiberNode, timestamp: Date = new Date()) => {
  return {
    antenna: generateAntennaSensorData(node, timestamp),
    weather: generateWeatherData(node, timestamp),
    environmental: generateEnvironmentalSensor(node, timestamp),
    equipment: generateEquipmentSensorData(node, timestamp),
  };
};

/**
 * Batch generate sensor data for multiple nodes
 */
export const generateSensorDataBatch = (nodes: FiberNode[], timestamp: Date = new Date()) => {
  return {
    antennaSensors: nodes.map(node => generateAntennaSensorData(node, timestamp)),
    weatherData: nodes.map(node => generateWeatherData(node, timestamp)),
    environmentalSensors: nodes.map(node => generateEnvironmentalSensor(node, timestamp)),
    equipmentSensors: nodes.map(node => generateEquipmentSensorData(node, timestamp)),
  };
};

// ============================================
// Network Element Generators (AAU, HVAC, SMSC, HLR)
// ============================================

const AAU_MANUFACTURERS = ['Ericsson', 'Nokia', 'Huawei', 'Samsung', 'ZTE'];
const AAU_MODELS: Record<string, string[]> = {
  'Ericsson': ['AIR 6449', 'AIR 3246', 'AIR 6419', 'AIR 1281'],
  'Nokia': ['AirScale AWHQA', 'AirScale AWHQB', 'AAKAA', 'AAKAB'],
  'Huawei': ['AAU5613', 'AAU5614', 'AAU5639', 'AAU5640'],
  'Samsung': ['MT6401', 'MT6405', 'MT6410'],
  'ZTE': ['AAU6620', 'AAU6625', 'AAU6630'],
};
const FREQUENCY_BANDS = ['700 MHz', '800 MHz', '1800 MHz', '1900 MHz', '2100 MHz', '2600 MHz', '3500 MHz', '3700 MHz'];
const MIMO_CONFIGS = ['2T2R', '4T4R', '8T8R', '32T32R', '64T64R', '128T128R'];

const HVAC_MANUFACTURERS = ['Emerson', 'Vertiv', 'Schneider', 'Delta', 'Stulz'];
const HVAC_MODELS: Record<string, string[]> = {
  'Emerson': ['NetSure 7100', 'NetSure 5100', 'Liebert CRV'],
  'Vertiv': ['Smartcool DSE', 'Smartcool ACU', 'Liebert HPM'],
  'Schneider': ['InRow RD', 'InRow RC', 'Uniflair LE'],
  'Delta': ['DPH Series', 'DPH Ultra', 'RT Series'],
  'Stulz': ['CyberAir 3', 'MiniSpace', 'Compact DX'],
};

/**
 * Generate AAU (Active Antenna Unit) for a node sector
 */
export const generateAAU = (
  node: FiberNode,
  sectorIndex: number = 0
): AAU => {
  const manufacturer = randomChoice(AAU_MANUFACTURERS);
  const models = AAU_MODELS[manufacturer];
  const hasNodeIssue = node.status === NodeStatus.OUTAGE || node.status === NodeStatus.DEGRADED;

  // Determine AAU status based on node status
  let status: NetworkElementStatus = NetworkElementStatus.OPERATIONAL;
  if (node.status === NodeStatus.OUTAGE && Math.random() < 0.5) {
    status = randomChoice([NetworkElementStatus.FAILED, NetworkElementStatus.DEGRADED]);
  } else if (node.status === NodeStatus.DEGRADED && Math.random() < 0.3) {
    status = NetworkElementStatus.DEGRADED;
  } else if (node.status === NodeStatus.MAINTENANCE) {
    status = NetworkElementStatus.MAINTENANCE;
  }

  // Select 2-4 frequency bands based on node channels
  const numChannels = (node.downstream_channels || 4);
  const numBands = numChannels >= 16 ? randomInt(2, 4) : randomInt(1, 3);
  const selectedBands: string[] = [];
  for (let i = 0; i < numBands; i++) {
    const band = randomChoice(FREQUENCY_BANDS);
    if (!selectedBands.includes(band)) {
      selectedBands.push(band);
    }
  }

  const maxTxPower = randomInRange(200, 400);
  const currentTxPower = status === NetworkElementStatus.OPERATIONAL
    ? maxTxPower * randomInRange(0.7, 0.95)
    : maxTxPower * randomInRange(0.3, 0.7);

  return {
    aau_id: generateId('AAU'),
    node_id: node.node_id,
    sector_id: `${node.node_id}-RF${sectorIndex + 1}`,
    manufacturer,
    model: randomChoice(models),
    serial_number: `SN-${manufacturer.substring(0, 3).toUpperCase()}-${randomInt(100000, 999999)}`,
    firmware_version: `v${randomInt(2, 8)}.${randomInt(0, 20)}.${randomInt(0, 99)}`,
    status,

    // RF characteristics
    frequency_bands: selectedBands,
    max_tx_power_watts: maxTxPower,
    current_tx_power_watts: currentTxPower,
    antenna_ports: randomChoice([4, 8, 32, 64, 128]),
    mimo_config: randomChoice(MIMO_CONFIGS),
    beamforming_enabled: Math.random() < 0.7,

    // Performance metrics
    temperature_celsius: hasNodeIssue ? randomInRange(55, 75) : randomInRange(35, 55),
    power_consumption_watts: randomInRange(800, 1500),
    vswr: hasNodeIssue ? randomInRange(1.8, 3.0) : randomInRange(1.1, 1.5),
    efficiency_percent: hasNodeIssue ? randomInRange(60, 80) : randomInRange(85, 95),

    // Timestamps
    installed_date: new Date(Date.now() - randomInt(180, 1825) * 24 * 60 * 60 * 1000),
    last_maintenance: new Date(Date.now() - randomInt(30, 180) * 24 * 60 * 60 * 1000),
    last_calibration: new Date(Date.now() - randomInt(7, 90) * 24 * 60 * 60 * 1000),
  };
};

/**
 * Generate HVAC Unit for a node
 */
export const generateHVACUnit = (
  node: FiberNode
): HVACUnit => {
  const manufacturer = randomChoice(HVAC_MANUFACTURERS);
  const models = HVAC_MODELS[manufacturer];

  // HVAC status - usually operational unless there are environmental issues
  const hasHvacIssue = Math.random() < 0.05; // 5% chance of HVAC issue
  let status: NetworkElementStatus = NetworkElementStatus.OPERATIONAL;
  let compressorStatus: 'running' | 'idle' | 'fault' = Math.random() < 0.7 ? 'running' : 'idle';
  let filterCondition: 'good' | 'replace_soon' | 'replace_now' = 'good';

  if (hasHvacIssue) {
    status = randomChoice([NetworkElementStatus.DEGRADED, NetworkElementStatus.FAILED]);
    compressorStatus = Math.random() < 0.5 ? 'fault' : 'running';
    filterCondition = randomChoice(['replace_soon', 'replace_now']);
  } else if (Math.random() < 0.2) {
    filterCondition = 'replace_soon';
  }

  // Temperature based on node location and weather
  const ambientTemp = Math.abs(node.latitude) < 30 ? randomInRange(25, 40) : randomInRange(15, 30);
  const setpoint = randomInRange(20, 25);
  const currentTemp = hasHvacIssue ? randomInRange(30, 45) : randomInRange(setpoint - 2, setpoint + 2);

  return {
    hvac_id: generateId('HVAC'),
    node_id: node.node_id,
    manufacturer,
    model: randomChoice(models),
    serial_number: `HVAC-${randomInt(100000, 999999)}`,
    status,

    // Operational parameters
    cooling_capacity_kw: randomInRange(5, 20),
    heating_capacity_kw: randomInRange(3, 10),
    current_mode: currentTemp > setpoint ? 'cooling' : ambientTemp < setpoint - 5 ? 'heating' : 'auto',
    setpoint_celsius: setpoint,
    current_temp_celsius: currentTemp,
    humidity_percent: randomInRange(30, 60),

    // Performance
    power_consumption_watts: randomInRange(500, 2000),
    compressor_status: compressorStatus,
    filter_condition: filterCondition,
    refrigerant_level_percent: hasHvacIssue ? randomInRange(60, 85) : randomInRange(90, 100),

    // Alarms
    high_temp_alarm: currentTemp > 40,
    low_temp_alarm: currentTemp < 10,
    compressor_fault: compressorStatus === 'fault',

    // Timestamps
    installed_date: new Date(Date.now() - randomInt(365, 2555) * 24 * 60 * 60 * 1000),
    last_maintenance: new Date(Date.now() - randomInt(30, 180) * 24 * 60 * 60 * 1000),
    last_filter_change: new Date(Date.now() - randomInt(30, 365) * 24 * 60 * 60 * 1000),
  };
};

/**
 * Generate SMSC (SMS Center) for a region
 */
export const generateSMSC = (
  region: GeographicRegion,
  provider: string
): SMSC => {
  const hasIssue = Math.random() < 0.03; // 3% chance of SMSC issue
  let status: NetworkElementStatus = NetworkElementStatus.OPERATIONAL;

  if (hasIssue) {
    status = randomChoice([NetworkElementStatus.DEGRADED, NetworkElementStatus.FAILED]);
  }

  const maxTps = randomInt(5000, 50000);
  const currentTps = status === NetworkElementStatus.OPERATIONAL
    ? randomInt(Math.floor(maxTps * 0.3), Math.floor(maxTps * 0.8))
    : randomInt(Math.floor(maxTps * 0.1), Math.floor(maxTps * 0.5));

  const maxQueueDepth = randomInt(10000, 100000);
  const queueDepth = hasIssue
    ? randomInt(Math.floor(maxQueueDepth * 0.6), maxQueueDepth)
    : randomInt(100, Math.floor(maxQueueDepth * 0.3));

  return {
    smsc_id: generateId('SMSC'),
    region,
    provider,
    name: `${provider} SMSC ${region}`,
    status,

    // Capacity and load
    max_tps: maxTps,
    current_tps: currentTps,
    queue_depth: queueDepth,
    max_queue_depth: maxQueueDepth,

    // Performance metrics
    delivery_success_rate: hasIssue ? randomInRange(85, 95) : randomInRange(98, 99.9),
    avg_delivery_time_ms: hasIssue ? randomInt(500, 3000) : randomInt(50, 300),
    pending_messages: queueDepth,
    failed_messages_24h: hasIssue ? randomInt(1000, 10000) : randomInt(10, 500),

    // Connectivity
    connected_hlrs: [`HLR-${region}-1`, `HLR-${region}-2`],
    connected_gateways: [`GW-${region}-1`, `GW-${region}-2`, `GW-${region}-3`],
    primary_ip: `10.${randomInt(1, 254)}.${randomInt(1, 254)}.${randomInt(1, 254)}`,
    backup_ip: `10.${randomInt(1, 254)}.${randomInt(1, 254)}.${randomInt(1, 254)}`,

    // Hardware
    cpu_utilization: hasIssue ? randomInRange(80, 95) : randomInRange(30, 70),
    memory_utilization: hasIssue ? randomInRange(75, 90) : randomInRange(40, 65),
    storage_utilization: randomInRange(30, 70),

    // Timestamps
    last_restart: new Date(Date.now() - randomInt(7, 90) * 24 * 60 * 60 * 1000),
    last_health_check: new Date(Date.now() - randomInt(1, 60) * 60 * 1000),
  };
};

/**
 * Generate HLR (Home Location Register) for a region
 */
export const generateHLR = (
  region: GeographicRegion,
  provider: string
): HLR => {
  const hasIssue = Math.random() < 0.02; // 2% chance of HLR issue
  let status: NetworkElementStatus = NetworkElementStatus.OPERATIONAL;
  let replicationStatus: 'synced' | 'syncing' | 'out_of_sync' | 'error' = 'synced';

  if (hasIssue) {
    status = randomChoice([NetworkElementStatus.DEGRADED, NetworkElementStatus.FAILED]);
    replicationStatus = randomChoice(['syncing', 'out_of_sync', 'error']);
  } else if (Math.random() < 0.1) {
    replicationStatus = 'syncing';
  }

  const maxSubscribers = randomInt(1000000, 10000000);
  const activeSubscribers = randomInt(Math.floor(maxSubscribers * 0.5), Math.floor(maxSubscribers * 0.9));

  return {
    hlr_id: generateId('HLR'),
    region,
    provider,
    name: `${provider} HLR ${region}`,
    status,

    // Capacity
    max_subscribers: maxSubscribers,
    active_subscribers: activeSubscribers,
    subscriber_utilization: (activeSubscribers / maxSubscribers) * 100,

    // Performance
    query_rate_per_second: hasIssue ? randomInt(500, 2000) : randomInt(2000, 10000),
    avg_response_time_ms: hasIssue ? randomInt(50, 200) : randomInt(5, 30),
    failed_queries_24h: hasIssue ? randomInt(500, 5000) : randomInt(10, 200),
    location_update_rate: randomInt(100, 1000),

    // Connectivity
    connected_mscs: [`MSC-${region}-1`, `MSC-${region}-2`],
    connected_sgsns: [`SGSN-${region}-1`],
    connected_mmes: [`MME-${region}-1`, `MME-${region}-2`],

    // Replication
    replication_status: replicationStatus,
    replica_lag_ms: replicationStatus === 'synced' ? randomInt(0, 100) : randomInt(1000, 30000),
    backup_hlr_id: `HLR-${region}-BACKUP`,

    // Hardware
    cpu_utilization: hasIssue ? randomInRange(85, 98) : randomInRange(40, 70),
    memory_utilization: hasIssue ? randomInRange(80, 95) : randomInRange(50, 75),
    disk_utilization: randomInRange(40, 70),

    // Timestamps
    last_backup: new Date(Date.now() - randomInt(1, 24) * 60 * 60 * 1000),
    last_sync: replicationStatus === 'synced'
      ? new Date(Date.now() - randomInt(1, 60) * 1000)
      : new Date(Date.now() - randomInt(5, 60) * 60 * 1000),
  };
};

/**
 * Generate all network elements for a node
 */
export const generateNetworkElements = (node: FiberNode) => {
  // Generate AAUs for downstream/upstream RF sections
  const rfSections = Math.max(1, Math.min(3, Math.ceil((node.downstream_channels || 4) / 8)));
  const aaus: AAU[] = Array.from({ length: rfSections }, (_, index) => generateAAU(node, index));

  // Generate single HVAC unit per node
  const hvac: HVACUnit = generateHVACUnit(node);

  return {
    aaus,
    hvac,
  };
};

/**
 * Generate SMSC and HLR instances for all regions
 */
export const generateCoreNetworkElements = (regions: GeographicRegion[], providers: string[]) => {
  const smscs: SMSC[] = [];
  const hlrs: HLR[] = [];

  for (const region of regions) {
    for (const provider of providers.slice(0, 2)) { // 2 providers per region
      smscs.push(generateSMSC(region, provider));
      hlrs.push(generateHLR(region, provider));
    }
  }

  return { smscs, hlrs };
};
