import {
  FiberNode,
  KPIMetrics,
  Alert,
  SelfHealingAction,
  NodeStatus,
  TechnologyType,
  AlertType,
  AlertSeverity,
  AlertStatus,
  ActionType,
  ActionStatus,
  Region,
  SiteType,
} from '@/types';
import {
  NODES_PER_REGION,
  MANUFACTURERS,
  HARDWARE_MODELS,
  FIRMWARE_VERSIONS,
  SITE_TYPE_DISTRIBUTION,
  CITIES_BY_REGION,
  TECHNOLOGY_ADOPTION,
  KPI_THRESHOLDS,
  FAILURE_PROBABILITIES,
  ACTION_EFFECTIVENESS,
} from '@/constants';
import {
  generateNodeId,
  generateId,
  randomInRange,
  randomInt,
  randomChoice,
  weightedRandomChoice,
  getHourlyTrafficMultiplier,
  getDayOfWeekMultiplier,
} from '@/utils/helpers';

// City coordinates for clustering nodes (guarantees land placement)
// Expanded with more cities for better distribution
const CITY_COORDS: Record<string, [number, number]> = {
  // North America (expanded)
  'New York': [40.7128, -74.0060],
  'Los Angeles': [34.0522, -118.2437],
  'Chicago': [41.8781, -87.6298],
  'Toronto': [43.6532, -79.3832],
  'Mexico City': [19.4326, -99.1332],
  'Houston': [29.7604, -95.3698],
  'Phoenix': [33.4484, -112.0740],
  'Philadelphia': [39.9526, -75.1652],
  'San Antonio': [29.4241, -98.4936],
  'Dallas': [32.7767, -96.7970],
  'Denver': [39.7392, -104.9903],
  'Seattle': [47.6062, -122.3321],
  'Miami': [25.7617, -80.1918],
  'Atlanta': [33.7490, -84.3880],
  'Boston': [42.3601, -71.0589],
  'Vancouver': [49.2827, -123.1207],
  'Montreal': [45.5017, -73.5673],
  'Calgary': [51.0447, -114.0719],
  // South America (expanded)
  'São Paulo': [-23.5505, -46.6333],
  'Buenos Aires': [-34.6037, -58.3816],
  'Rio de Janeiro': [-22.9068, -43.1729],
  'Lima': [-12.0464, -77.0428],
  'Bogotá': [4.7110, -74.0721],
  'Santiago': [-33.4489, -70.6693],
  'Caracas': [10.4806, -66.9036],
  'Brasília': [-15.8267, -47.9218],
  // Europe (expanded)
  'London': [51.5074, -0.1278],
  'Paris': [48.8566, 2.3522],
  'Berlin': [52.5200, 13.4050],
  'Madrid': [40.4168, -3.7038],
  'Rome': [41.9028, 12.4964],
  'Amsterdam': [52.3676, 4.9041],
  'Vienna': [48.2082, 16.3738],
  'Barcelona': [41.3851, 2.1734],
  'Munich': [48.1351, 11.5820],
  'Milan': [45.4642, 9.1900],
  'Warsaw': [52.2297, 21.0122],
  'Budapest': [47.4979, 19.0402],
  // Africa (expanded)
  'Cairo': [30.0444, 31.2357],
  'Lagos': [6.5244, 3.3792],
  'Johannesburg': [-26.2041, 28.0473],
  'Nairobi': [-1.2864, 36.8172],
  'Casablanca': [33.5731, -7.5898],
  'Kinshasa': [-4.4419, 15.2663],
  'Luanda': [-8.8383, 13.2344],
  'Addis Ababa': [9.0320, 38.7469],
  // Asia (expanded)
  'Tokyo': [35.6762, 139.6503],
  'Shanghai': [31.2304, 121.4737],
  'Mumbai': [19.0760, 72.8777],
  'Seoul': [37.5665, 126.9780],
  'Singapore': [1.3521, 103.8198],
  'Bangkok': [13.7563, 100.5018],
  'Beijing': [39.9042, 116.4074],
  'Delhi': [28.7041, 77.1025],
  'Jakarta': [-6.2088, 106.8456],
  'Manila': [14.5995, 120.9842],
  'Hong Kong': [22.3193, 114.1694],
  'Kuala Lumpur': [3.1390, 101.6869],
  // Oceania (expanded)
  'Sydney': [-33.8688, 151.2093],
  'Melbourne': [-37.8136, 144.9631],
  'Auckland': [-36.8485, 174.7633],
  'Brisbane': [-27.4698, 153.0251],
  'Perth': [-31.9505, 115.8605],
  'Adelaide': [-34.9285, 138.6007],
  'Wellington': [-41.2865, 174.7762],
  'Geelong': [-38.1499, 144.3617],
  'Dandenong': [-37.9871, 145.2149],
  // Africa (new cities not already in dict)
  'Lagos Island': [6.4541, 3.3947],
  'Ikeja': [6.6018, 3.3515],
  'Pretoria': [-25.7479, 28.2293],
  'Sandton': [-26.1076, 28.0567],
  'Soweto': [-26.2678, 27.8585],
  'Nairobi CBD': [-1.2864, 36.8172],
  'Thika': [-1.0396, 37.0900],
  // Additional new cities
  'Surrey': [49.1913, -122.8490],
  'La Plata': [-34.9205, -57.9536],
  'Quilmes': [-34.7203, -58.2524],
  'Versailles': [48.8014, 2.1301],
  'Saint-Denis': [48.9362, 2.3574],
  'Incheon': [37.4563, 126.7052],
  'Bekasi': [-6.2383, 106.9756],
  'Giza': [30.0131, 31.2089],
};

/**
 * Select site type based on probability distribution
 */
const selectSiteType = (): SiteType => {
  const roll = Math.random();
  let cumulative = 0;

  for (const [type, probability] of Object.entries(SITE_TYPE_DISTRIBUTION)) {
    cumulative += probability;
    if (roll <= cumulative) {
      return type as SiteType;
    }
  }

  return SiteType.MACRO; // Fallback
};

/**
 * Generates initial fiber node data with realistic geographic distribution
 * Clusters nodes around cities to guarantee land placement
 */
export const generateFiberNodes = (): FiberNode[] => {
  const nodes: FiberNode[] = [];
  const regions = Object.values(Region);
  let regionIndex = 0;

  for (const region of regions) {
    const count = NODES_PER_REGION[region];
    const cities = CITIES_BY_REGION[region];
    const nodesPerCity = Math.ceil(count / cities.length);

    let nodeIndex = 0;

    // Generate all nodes clustered around cities (100% city-based)
    for (const city of cities) {
      const cityCoord = CITY_COORDS[city];
      if (!cityCoord) continue;

      const cityNodeCount = Math.min(nodesPerCity, count - nodeIndex);

      for (let i = 0; i < cityNodeCount; i++) {
        // Variable radius: 70% within 100km, 30% within 300km (suburban/rural)
        const maxRadius = Math.random() < 0.7 ? 1.0 : 3.0; // degrees (~100km or ~300km)

        const latOffset = randomInRange(-maxRadius, maxRadius);
        const lngOffset = randomInRange(-maxRadius, maxRadius);

        // Equipment info
        const manufacturer = randomChoice(MANUFACTURERS);
        const hardwareModel = randomChoice(HARDWARE_MODELS[manufacturer]);
        const firmwareVersionInfo = FIRMWARE_VERSIONS[manufacturer];
        const firmwareVersion = `${randomInt(firmwareVersionInfo.major[0], firmwareVersionInfo.major[1])}.${randomInt(firmwareVersionInfo.minor[0], firmwareVersionInfo.minor[1])}.${randomInt(0, 99)}`;

        // Site type determines node classification and capacity
        const siteType = selectSiteType();

        // Technology & capacity
        const technology = generateTechnologyStack();
        const capacity = siteType === SiteType.MACRO ? randomInt(1000, 5000) :
                        siteType === SiteType.MICRO ? randomInt(200, 1000) :
                        randomInt(50, 200);

        // Node ID
        const nodeId = generateNodeId(regionIndex, nodeIndex);

        // Power
        const batteryBackup = randomInRange(4, 24); // Hours

        // Dates
        const commissionedDate = generateCommissionDate();
        const lastMaintenance = generateMaintenanceDate();

        // Map site types to cable node types
        const nodeType = siteType === SiteType.MACRO ? 'N+3' :
                        siteType === SiteType.MICRO ? 'N+1' : 'N+0';
        const homesPassed = capacity;
        const homesActive = Math.floor(capacity * randomInRange(0.5, 0.85));
        const docsisVersion = technology.includes(TechnologyType.FTTH) ? '4.0' :
                             technology.includes(TechnologyType.DOCSIS_40) ? '4.0' :
                             technology.includes(TechnologyType.DOCSIS_31) ? '3.1' : '3.0';

        const node: FiberNode = {
          node_id: nodeId,
          headend_id: `HE-${region.substring(0, 2).toUpperCase()}-${Math.floor(nodeIndex / 200) + 1}`,
          hub_id: `HUB-${region.substring(0, 2).toUpperCase()}-${Math.floor(nodeIndex / 20) + 1}`,
          service_area: `SA-${region.substring(0, 2).toUpperCase()}-${Math.floor(nodeIndex / 10) + 1}`,
          latitude: cityCoord[0] + latOffset,
          longitude: cityCoord[1] + lngOffset,
          region,
          city,

          // Node Classification
          node_type: nodeType,
          homes_passed: homesPassed,
          homes_active: homesActive,
          docsis_version: docsisVersion,

          // RF Configuration
          downstream_channels: docsisVersion === '4.0' ? 32 : docsisVersion === '3.1' ? 24 : 16,
          upstream_channels: docsisVersion === '4.0' ? 8 : docsisVersion === '3.1' ? 4 : 4,
          ofdm_channels: docsisVersion >= '3.1' ? randomInt(1, 4) : 0,
          ofdma_channels: docsisVersion >= '3.1' ? randomInt(1, 2) : 0,

          // Equipment
          manufacturer,
          hardware_model: hardwareModel,
          firmware_version: firmwareVersion,

          // Power
          power_supply_count: randomInt(1, 2),
          power_supply_status: Math.random() < 0.95 ? 'all_ok' : (Math.random() < 0.7 ? 'partial_failure' : 'critical'),
          battery_backup_hours: batteryBackup,

          // Plant Details
          amplifier_cascade: nodeType === 'N+3' ? 3 : nodeType === 'N+1' ? 1 : 0,
          coax_plant_miles: randomInRange(1, 15),
          fiber_miles: randomInRange(0.5, 8),

          // Status & Maintenance
          status: NodeStatus.HEALTHY,
          commissioned_date: commissionedDate,
          last_maintenance: lastMaintenance,

          // Relationships
          neighbor_nodes: [],
        };

        nodes.push(node);
        nodeIndex++;
      }
    }

    regionIndex++;
  }

  // Populate neighbor nodes efficiently (find closest nodes)
  populateNeighborNodes(nodes);

  return nodes;
};

/**
 * Generate technology stack based on adoption rates
 */
const generateTechnologyStack = (): TechnologyType[] => {
  const technologies = Object.keys(TECHNOLOGY_ADOPTION) as TechnologyType[];
  const weights = Object.values(TECHNOLOGY_ADOPTION);

  // Weighted selection of primary technology
  const primary = weightedRandomChoice(technologies, weights);
  const stack: TechnologyType[] = [primary];

  // Add legacy technologies with decreasing probability
  if (primary === TechnologyType.FTTH && Math.random() < 0.8) {
    stack.push(TechnologyType.DOCSIS_40);
  }
  if (stack.includes(TechnologyType.DOCSIS_40) && Math.random() < 0.5) {
    stack.push(TechnologyType.DOCSIS_31);
  }

  return stack;
};

const generateCommissionDate = (): Date => {
  const yearsAgo = randomInt(0, 10);
  const date = new Date();
  date.setFullYear(date.getFullYear() - yearsAgo);
  return date;
};

const generateMaintenanceDate = (): Date => {
  const daysAgo = randomInt(1, 90);
  const date = new Date();
  date.setDate(date.getDate() - daysAgo);
  return date;
};

/**
 * Efficiently find and populate neighbor nodes
 * Uses spatial partitioning for O(n) instead of O(n²)
 */
const populateNeighborNodes = (nodes: FiberNode[]): void => {
  const NEIGHBOR_RADIUS = 2; // degrees (roughly 200km)
  const MAX_NEIGHBORS = 6;

  nodes.forEach((node) => {
    const neighbors = nodes
      .filter((other) => {
        if (other.node_id === node.node_id) return false;
        const latDiff = Math.abs(node.latitude - other.latitude);
        const lngDiff = Math.abs(node.longitude - other.longitude);
        return latDiff <= NEIGHBOR_RADIUS && lngDiff <= NEIGHBOR_RADIUS;
      })
      .sort((a, b) => {
        const distA = Math.hypot(
          node.latitude - a.latitude,
          node.longitude - a.longitude
        );
        const distB = Math.hypot(
          node.latitude - b.latitude,
          node.longitude - b.longitude
        );
        return distA - distB;
      })
      .slice(0, MAX_NEIGHBORS)
      .map((t) => t.node_id);

    node.neighbor_nodes = neighbors;
  });
};

/**
 * Generate realistic KPI metrics for a node
 * Uses time-based patterns for realism
 */
export const generateKPIMetrics = (
  node: FiberNode,
  timestamp: Date = new Date()
): KPIMetrics => {
  const hour = timestamp.getHours();
  const dayOfWeek = timestamp.getDay();
  const trafficMultiplier = getHourlyTrafficMultiplier(hour) * getDayOfWeekMultiplier(dayOfWeek);

  // Base metrics with realistic patterns
  const baseActiveUsers = Math.floor((node.homes_active || 350) * 0.3 * trafficMultiplier);

  // Adjust metrics based on node status
  const statusMultipliers = getStatusMultipliers(node.status);

  const metrics: KPIMetrics = {
    metric_id: generateId('KPI'),
    node_id: node.node_id,
    timestamp,
    // RF Signal Levels (DOCSIS)
    ds_power_level_dbmv: randomInRange(-10, 10) * statusMultipliers.success,
    us_power_level_dbmv: randomInRange(35, 50) * statusMultipliers.success,
    ds_snr_db: Math.min(45, randomInRange(33, 42) * statusMultipliers.success),
    us_snr_db: Math.min(35, randomInRange(25, 33) * statusMultipliers.success),
    ds_mer_db: randomInRange(33, 42) * statusMultipliers.success,
    us_mer_db: randomInRange(25, 33) * statusMultipliers.success,
    // Forward Error Correction
    fec_corrected_codewords: Math.floor(randomInRange(0, 100) * statusMultipliers.failure),
    fec_uncorrected_codewords: Math.floor(randomInRange(0, 10) * statusMultipliers.failure),
    // DOCSIS Timeouts
    t3_timeouts: Math.floor(randomInRange(0, 5) * statusMultipliers.failure),
    t4_timeouts: Math.floor(randomInRange(0, 2) * statusMultipliers.failure),
    // Throughput
    downstream_throughput_mbps: randomInRange(80, 250) * trafficMultiplier * statusMultipliers.success,
    upstream_throughput_mbps: randomInRange(20, 60) * trafficMultiplier * statusMultipliers.success,
    // Network Performance
    latency_ms: randomInRange(8, 25) * statusMultipliers.latency,
    packet_loss_percent: Math.max(0, randomInRange(0.05, 0.8) * statusMultipliers.failure),
    jitter_ms: randomInRange(1, 10) * statusMultipliers.latency,
    // Channel Utilization
    ds_channel_utilization_percent: randomInRange(20, 70) + (trafficMultiplier - 1) * 15,
    us_channel_utilization_percent: randomInRange(15, 55) + (trafficMultiplier - 1) * 12,
    ofdm_utilization_percent: randomInRange(10, 50) + (trafficMultiplier - 1) * 10,
    // Modem Counts
    active_modems: baseActiveUsers,
    registered_modems: Math.floor(baseActiveUsers * 1.15),
    offline_modems: Math.floor(baseActiveUsers * 0.02 * statusMultipliers.failure),
    modems_with_flaps: Math.floor(randomInRange(0, 5) * statusMultipliers.failure),
    // Equipment Health
    node_temperature: randomInRange(40, 55),
    node_cpu_utilization: randomInRange(25, 60) + (trafficMultiplier - 1) * 15,
    node_memory_utilization: randomInRange(35, 55) + (trafficMultiplier - 1) * 12,
    power_supply_voltage: randomInRange(11.5, 12.5),
  };

  return metrics;
};

/**
 * Get multipliers based on node status for realistic degradation
 * Adds variation so different nodes degrade in different ways
 */
const getStatusMultipliers = (status: NodeStatus) => {
  switch (status) {
    case NodeStatus.HEALTHY:
      return { success: 1.0, failure: 1.0, latency: 1.0 };
    case NodeStatus.DEGRADED:
      return {
        success: 0.88 + Math.random() * 0.08, // 0.88-0.96
        failure: 3.0 + Math.random() * 3.0,    // 3.0-6.0
        latency: 1.5 + Math.random() * 1.5     // 1.5-3.0
      };
    case NodeStatus.OUTAGE:
      return {
        success: 0.75 + Math.random() * 0.10,  // 0.75-0.85
        failure: 12.0 + Math.random() * 8.0,   // 12.0-20.0
        latency: 6.0 + Math.random() * 6.0     // 6.0-12.0
      };
    case NodeStatus.MAINTENANCE:
      return { success: 0.96, failure: 1.5, latency: 1.3 };
    default:
      return { success: 1.0, failure: 1.0, latency: 1.0 };
  }
};

/**
 * Detect anomalies in KPI metrics and generate alerts
 * Efficient threshold-based detection
 */
export const detectAnomalies = (
  metrics: KPIMetrics,
  node: FiberNode
): Alert | null => {
  const violations: { kpi: string; severity: AlertSeverity }[] = [];

  // Check each KPI against thresholds
  if (metrics.ds_snr_db < KPI_THRESHOLDS.ds_snr_db.critical) {
    violations.push({ kpi: 'ds_snr_db', severity: AlertSeverity.CRITICAL });
  } else if (metrics.ds_snr_db < KPI_THRESHOLDS.ds_snr_db.warning) {
    violations.push({ kpi: 'ds_snr_db', severity: AlertSeverity.WARNING });
  }

  if (metrics.packet_loss_percent > KPI_THRESHOLDS.packet_loss_percent.critical) {
    violations.push({ kpi: 'packet_loss_percent', severity: AlertSeverity.CRITICAL });
  } else if (metrics.packet_loss_percent > KPI_THRESHOLDS.packet_loss_percent.warning) {
    violations.push({ kpi: 'packet_loss_percent', severity: AlertSeverity.WARNING });
  }

  if (metrics.us_snr_db < KPI_THRESHOLDS.us_snr_db.critical) {
    violations.push({ kpi: 'us_snr_db', severity: AlertSeverity.CRITICAL });
  }

  if (metrics.latency_ms > KPI_THRESHOLDS.latency_ms.critical) {
    violations.push({ kpi: 'latency_ms', severity: AlertSeverity.CRITICAL });
  }

  if (metrics.node_cpu_utilization > KPI_THRESHOLDS.node_cpu_utilization.critical) {
    violations.push({ kpi: 'node_cpu_utilization', severity: AlertSeverity.WARNING });
  }

  if (metrics.node_memory_utilization > KPI_THRESHOLDS.node_memory_utilization.critical) {
    violations.push({ kpi: 'node_memory_utilization', severity: AlertSeverity.WARNING });
  }

  if (metrics.node_temperature > KPI_THRESHOLDS.node_temperature.critical) {
    violations.push({ kpi: 'node_temperature', severity: AlertSeverity.WARNING });
  }

  // No violations, no alert
  if (violations.length === 0) return null;

  // Determine alert type and severity
  const maxSeverity = violations.some((v) => v.severity === AlertSeverity.CRITICAL)
    ? AlertSeverity.CRITICAL
    : AlertSeverity.WARNING;

  const alertType = determineAlertType(violations.map((v) => v.kpi));

  const alert: Alert = {
    alert_id: generateId('ALERT'),
    node_id: node.node_id,
    timestamp: metrics.timestamp,
    alert_type: alertType,
    severity: maxSeverity,
    description: generateAlertDescription(alertType, node.node_id),
    affected_kpis: violations.map((v) => v.kpi),
    ai_confidence: randomInRange(75, 98),
    model_name: 'Threshold-Based Detector v1.0',
    status: AlertStatus.ACTIVE,
  };

  return alert;
};

const determineAlertType = (affectedKPIs: string[]): AlertType => {
  // Check for multiple critical issues = outage
  if (affectedKPIs.length >= 4) {
    return AlertType.NODE_OUTAGE;
  }

  // Equipment/environmental issues
  if (affectedKPIs.includes('node_temperature')) {
    return AlertType.EQUIPMENT_FAILURE;
  }

  // Specific patterns for different issue types
  if (affectedKPIs.includes('node_cpu_utilization') || affectedKPIs.includes('node_memory_utilization')) {
    // High resource usage = congestion or equipment issues
    return Math.random() < 0.7 ? AlertType.CONGESTION : AlertType.EQUIPMENT_FAILURE;
  }

  if (affectedKPIs.includes('us_snr_db')) {
    return AlertType.SIGNAL_DEGRADATION;
  }

  if (affectedKPIs.includes('packet_loss_percent')) {
    // High packet loss could be signal or equipment issue
    return Math.random() < 0.8 ? AlertType.HIGH_PACKET_LOSS : AlertType.EQUIPMENT_FAILURE;
  }

  if (affectedKPIs.includes('ds_snr_db')) {
    return AlertType.DEGRADED_SERVICE;
  }

  if (affectedKPIs.includes('latency_ms')) {
    return AlertType.CONGESTION;
  }

  // Default fallback
  return AlertType.DEGRADED_SERVICE;
};

const generateAlertDescription = (alertType: AlertType, nodeId: string): string => {
  const descriptions: Record<AlertType, string> = {
    [AlertType.NODE_OUTAGE]: `Complete service outage detected at ${nodeId}`,
    [AlertType.DEGRADED_SERVICE]: `Service degradation detected at ${nodeId}`,
    [AlertType.HIGH_PACKET_LOSS]: `Abnormally high packet loss at ${nodeId}`,
    [AlertType.CONGESTION]: `Network congestion detected at ${nodeId}`,
    [AlertType.EQUIPMENT_FAILURE]: `Equipment failure detected at ${nodeId}`,
    [AlertType.SIGNAL_DEGRADATION]: `Signal degradation detected at ${nodeId}`,
  };
  return descriptions[alertType];
};

/**
 * Generate self-healing action for an alert
 */
export const generateSelfHealingAction = (alert: Alert): SelfHealingAction => {
  const actionType = determineActionType(alert.alert_type);

  // Map action type to the constant key
  const actionKey = actionType.toUpperCase() as keyof typeof ACTION_EFFECTIVENESS;
  const effectiveness = randomInRange(
    ACTION_EFFECTIVENESS[actionKey].min,
    ACTION_EFFECTIVENESS[actionKey].max
  );

  const action: SelfHealingAction = {
    action_id: generateId('ACTION'),
    alert_id: alert.alert_id,
    node_id: alert.node_id,
    timestamp: new Date(),
    action_type: actionType,
    action_details: generateActionDetails(actionType),
    status: ActionStatus.PENDING,
    effectiveness_score: effectiveness,
    rollback_available: actionType !== ActionType.TICKET_CREATION,
    automated: alert.severity !== AlertSeverity.CRITICAL, // Critical requires manual approval
  };

  return action;
};

const determineActionType = (alertType: AlertType): ActionType => {
  const mapping: Record<AlertType, ActionType> = {
    [AlertType.NODE_OUTAGE]: ActionType.NODE_REBOOT,
    [AlertType.DEGRADED_SERVICE]: ActionType.PARAMETER_OPTIMIZATION,
    [AlertType.HIGH_PACKET_LOSS]: ActionType.RF_ADJUSTMENT,
    [AlertType.CONGESTION]: ActionType.LOAD_BALANCE,
    [AlertType.EQUIPMENT_FAILURE]: ActionType.TICKET_CREATION,
    [AlertType.SIGNAL_DEGRADATION]: ActionType.CAPACITY_EXPANSION,
  };
  return mapping[alertType] || ActionType.PARAMETER_OPTIMIZATION;
};

const generateActionDetails = (actionType: ActionType): Record<string, unknown> => {
  switch (actionType) {
    case ActionType.LOAD_BALANCE:
      return { target_cells: randomInt(2, 5), traffic_percentage: randomInt(20, 40) };
    case ActionType.PARAMETER_OPTIMIZATION:
      return { parameters: ['antenna_tilt', 'tx_power'], adjustment: 'automatic' };
    case ActionType.NODE_REBOOT:
      return { reboot_type: 'soft', estimated_downtime: '2 minutes' };
    case ActionType.TRAFFIC_REROUTING:
      return { alternate_routes: randomInt(2, 4), expected_improvement: '25%' };
    case ActionType.RF_ADJUSTMENT:
      return { ds_power_adjustment: `${randomInt(-2, 2)} dBmV`, us_power_adjustment: `${randomInt(-2, 2)} dBmV` };
    case ActionType.TICKET_CREATION:
      return { priority: 'high', assigned_to: 'NOC Team', sla: '4 hours' };
    case ActionType.CAPACITY_EXPANSION:
      return { additional_channels: randomInt(2, 4), target_utilization: '70%' };
    default:
      return {};
  }
};

/**
 * Inject realistic failure scenarios
 * IMPORTANT: Maintains at least 60% healthy nodes to prevent runaway failures
 */
export const injectFailureScenario = (nodes: FiberNode[]): void => {
  const totalNodes = nodes.length;
  if (totalNodes === 0) return;

  // Safety check: Ensure at least 60% of nodes remain healthy
  const MIN_HEALTHY_RATIO = 0.60;
  const healthyCount = nodes.filter(t => t.status === NodeStatus.HEALTHY).length;
  const currentHealthyRatio = healthyCount / totalNodes;

  if (currentHealthyRatio <= MIN_HEALTHY_RATIO) {
    // Too many failures already - skip injection
    return;
  }

  // Calculate max new failures allowed
  const maxAllowedUnhealthy = Math.floor(totalNodes * (1 - MIN_HEALTHY_RATIO));
  const currentUnhealthy = totalNodes - healthyCount;
  let roomForFailures = maxAllowedUnhealthy - currentUnhealthy;

  nodes.forEach((node) => {
    // Stop if we've used up our failure budget
    if (roomForFailures <= 0) return;
    // Only healthy nodes can fail
    if (node.status !== NodeStatus.HEALTHY) return;

    Object.entries(FAILURE_PROBABILITIES).forEach(([type, probability]) => {
      if (roomForFailures <= 0) return;
      if (Math.random() < probability / 3600) { // Per-second probability
        applyFailureScenario(node, type as keyof typeof FAILURE_PROBABILITIES);
        if (node.status !== NodeStatus.HEALTHY) {
          roomForFailures--;
        }
      }
    });
  });
};

const applyFailureScenario = (node: FiberNode, scenarioType: string): void => {
  switch (scenarioType) {
    case 'NODE_OUTAGE':
      node.status = NodeStatus.OUTAGE;
      break;
    case 'DEGRADED_SERVICE':
    case 'HIGH_PACKET_LOSS':
    case 'SIGNAL_DEGRADATION':
      node.status = NodeStatus.DEGRADED;
      break;
    case 'CONGESTION':
      // Status remains healthy, but KPIs will show congestion
      break;
  }
};
