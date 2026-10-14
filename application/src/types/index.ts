// Enums for type safety and efficiency
export enum NodeStatus {
  HEALTHY = 'healthy',
  DEGRADED = 'degraded',
  OUTAGE = 'outage',
  MAINTENANCE = 'maintenance',
}


export enum TechnologyType {
  DOCSIS_30 = 'DOCSIS 3.0',
  DOCSIS_31 = 'DOCSIS 3.1',
  DOCSIS_40 = 'DOCSIS 4.0',
  FTTH = 'FTTH',
}

export enum AlertType {
  NODE_OUTAGE = 'node_outage',
  DEGRADED_SERVICE = 'degraded_service',
  HIGH_PACKET_LOSS = 'high_packet_loss',
  CONGESTION = 'congestion',
  EQUIPMENT_FAILURE = 'equipment_failure',
  SIGNAL_DEGRADATION = 'signal_degradation',
}

export enum AlertSeverity {
  CRITICAL = 'critical',
  WARNING = 'warning',
  INFO = 'info',
}

export enum AlertStatus {
  ACTIVE = 'active',
  ACKNOWLEDGED = 'acknowledged',
  RESOLVED = 'resolved',
  FALSE_POSITIVE = 'false_positive',
}

export enum ActionType {
  LOAD_BALANCE = 'load_balance',
  PARAMETER_OPTIMIZATION = 'parameter_optimization',
  NODE_REBOOT = 'node_reboot',
  TRAFFIC_REROUTING = 'traffic_rerouting',
  RF_ADJUSTMENT = 'rf_adjustment',
  TICKET_CREATION = 'ticket_creation',
  CAPACITY_EXPANSION = 'capacity_expansion',
  // Backend-generated cable network action types
  MODEM_REMOTE_REBOOT = 'modem_remote_reboot',
  FIRMWARE_PUSH = 'firmware_push',
  PROVISIONING_REFRESH = 'provisioning_refresh',
  CMTS_PORT_RESET = 'cmts_port_reset',
  SIGNAL_LEVEL_ADJUSTMENT = 'signal_level_adjustment',
  TRAFFIC_REROUTE = 'traffic_reroute',
  NODE_CAPACITY_REBALANCE = 'node_capacity_rebalance',
}

export enum ActionStatus {
  PENDING = 'pending',
  IN_PROGRESS = 'in_progress',
  COMPLETED = 'completed',
  FAILED = 'failed',
  ROLLED_BACK = 'rolled_back',
}

// Detailed remediation step for tracking workflow progress
export interface RemediationStep {
  step_id: string;
  order: number;
  name: string;
  description: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed' | 'skipped';
  started_at?: Date;
  completed_at?: Date;
  duration_ms?: number;
  result?: string;
  error?: string;
}

// Standard remediation workflow steps by action type
export const REMEDIATION_WORKFLOWS: Record<ActionType, { name: string; description: string }[]> = {
  [ActionType.NODE_REBOOT]: [
    { name: 'Analyzing System State', description: 'Collecting current system metrics and state' },
    { name: 'Notifying Active Modems', description: 'Sending maintenance notifications to CPE devices' },
    { name: 'Graceful Service Shutdown', description: 'Stopping active services and connections' },
    { name: 'Initiating Soft Reboot', description: 'Sending reboot command to node controller' },
    { name: 'Hardware Self-Test', description: 'Running POST diagnostics on equipment' },
    { name: 'Service Restoration', description: 'Bringing services back online' },
    { name: 'Verifying Connectivity', description: 'Testing fiber backhaul and core network connections' },
    { name: 'KPI Validation', description: 'Confirming performance metrics are within thresholds' },
  ],
  [ActionType.LOAD_BALANCE]: [
    { name: 'Analyzing Traffic Distribution', description: 'Evaluating current load across nodes' },
    { name: 'Identifying Target Nodes', description: 'Finding neighbor nodes with available capacity' },
    { name: 'Calculating Channel Parameters', description: 'Computing optimal channel bonding groups' },
    { name: 'Updating Channel Assignments', description: 'Modifying DOCSIS channel bonding groups' },
    { name: 'Adjusting QoS Parameters', description: 'Fine-tuning service flow priorities' },
    { name: 'Initiating Modem Migration', description: 'Triggering controlled modem re-registration' },
    { name: 'Monitoring Load Balance', description: 'Verifying traffic redistribution' },
  ],
  [ActionType.PARAMETER_OPTIMIZATION]: [
    { name: 'Baseline Measurement', description: 'Recording current RF parameters and KPIs' },
    { name: 'AI Parameter Analysis', description: 'Computing optimal parameter adjustments' },
    { name: 'Safety Validation', description: 'Ensuring changes are within safe limits' },
    { name: 'Applying Power Level Adjustments', description: 'Modifying downstream/upstream power levels' },
    { name: 'Updating OFDM Parameters', description: 'Adjusting OFDM/OFDMA channel configuration' },
    { name: 'Performance Monitoring', description: 'Observing KPI improvements' },
    { name: 'Rollback Check', description: 'Verifying no negative impact on service' },
  ],
  [ActionType.TRAFFIC_REROUTING]: [
    { name: 'Analyzing Routing Paths', description: 'Mapping current traffic flows' },
    { name: 'Identifying Alternate Routes', description: 'Finding available routing paths' },
    { name: 'Capacity Verification', description: 'Ensuring alternate paths can handle load' },
    { name: 'Updating Routing Tables', description: 'Modifying network routing configuration' },
    { name: 'Traffic Migration', description: 'Gradually shifting traffic to new paths' },
    { name: 'Latency Validation', description: 'Verifying QoS requirements are met' },
  ],
  [ActionType.RF_ADJUSTMENT]: [
    { name: 'Current Signal Check', description: 'Reading current power levels and SNR values' },
    { name: 'Signal Analysis', description: 'Analyzing downstream/upstream signal quality' },
    { name: 'Calculating Optimal Levels', description: 'Computing target power and attenuation values' },
    { name: 'Checking Plant Equipment', description: 'Verifying amplifier and tap status' },
    { name: 'Applying Level Adjustment', description: 'Setting new power levels on node' },
    { name: 'MER/SNR Verification', description: 'Checking modulation error ratio and SNR' },
    { name: 'Service Validation', description: 'Confirming improved signal quality for modems' },
  ],
  [ActionType.TICKET_CREATION]: [
    { name: 'Gathering Diagnostic Data', description: 'Collecting logs and telemetry' },
    { name: 'Root Cause Documentation', description: 'Documenting identified issues' },
    { name: 'Priority Assessment', description: 'Determining ticket priority level' },
    { name: 'Creating Work Order', description: 'Generating maintenance ticket' },
    { name: 'Crew Assignment', description: 'Assigning field technician team' },
    { name: 'Notification Dispatch', description: 'Sending alerts to assigned crew' },
  ],
  [ActionType.CAPACITY_EXPANSION]: [
    { name: 'Analyzing Utilization Patterns', description: 'Reviewing channel utilization and modem counts' },
    { name: 'Identifying Expansion Options', description: 'Finding available OFDM/OFDMA channels' },
    { name: 'Interference Analysis', description: 'Checking for potential frequency conflicts' },
    { name: 'Adding Channel Capacity', description: 'Activating additional bonded channels' },
    { name: 'Configuring QoS Rules', description: 'Setting up service flow parameters' },
    { name: 'Testing Modem Connectivity', description: 'Verifying modem registration on new channels' },
  ],
  // Backend-generated cable network action types
  [ActionType.MODEM_REMOTE_REBOOT]: [
    { name: 'Identifying Affected Modems', description: 'Querying CMTS for modem registration status' },
    { name: 'Sending SNMP Reset Command', description: 'Issuing remote reboot via SNMP to CPE devices' },
    { name: 'Waiting for Re-Registration', description: 'Monitoring DOCSIS ranging and registration' },
    { name: 'Verifying Connectivity', description: 'Confirming modem online status and throughput' },
  ],
  [ActionType.FIRMWARE_PUSH]: [
    { name: 'Validating Firmware Package', description: 'Checking firmware compatibility and checksums' },
    { name: 'Staging Firmware on TFTP Server', description: 'Uploading firmware image to provisioning server' },
    { name: 'Initiating Firmware Download', description: 'Triggering DOCSIS firmware download to devices' },
    { name: 'Monitoring Download Progress', description: 'Tracking firmware transfer to affected equipment' },
    { name: 'Verifying Firmware Version', description: 'Confirming new firmware is active post-reboot' },
    { name: 'Post-Update Health Check', description: 'Validating KPIs and service quality after update' },
  ],
  [ActionType.PROVISIONING_REFRESH]: [
    { name: 'Fetching Current Config', description: 'Reading active provisioning file from CMTS' },
    { name: 'Generating Updated Config', description: 'Building new DOCSIS config file with corrections' },
    { name: 'Pushing Config to Provisioning Server', description: 'Uploading config to TFTP/DHCP server' },
    { name: 'Triggering Modem Re-Provisioning', description: 'Forcing modems to download new config' },
    { name: 'Verifying Service Parameters', description: 'Confirming correct QoS and channel assignments' },
  ],
  [ActionType.CMTS_PORT_RESET]: [
    { name: 'Analyzing Port Status', description: 'Reading CMTS port error counters and state' },
    { name: 'Notifying Affected Subscribers', description: 'Logging impacted customer accounts' },
    { name: 'Executing Port Reset', description: 'Cycling CMTS upstream/downstream port' },
    { name: 'Waiting for Port Recovery', description: 'Monitoring port link-up and modem re-ranging' },
    { name: 'Verifying Modem Registrations', description: 'Confirming all modems re-registered successfully' },
    { name: 'KPI Validation', description: 'Checking SNR, power levels, and throughput post-reset' },
  ],
  [ActionType.SIGNAL_LEVEL_ADJUSTMENT]: [
    { name: 'Reading Current Levels', description: 'Measuring DS/US power and SNR at node' },
    { name: 'Calculating Optimal Levels', description: 'Computing target power based on plant specs' },
    { name: 'Applying Adjustments', description: 'Setting new power levels on node controller' },
    { name: 'Monitoring Signal Quality', description: 'Observing MER/SNR improvements across modems' },
  ],
  [ActionType.TRAFFIC_REROUTE]: [
    { name: 'Mapping Current Routes', description: 'Analyzing active traffic flows and utilization' },
    { name: 'Identifying Alternate Paths', description: 'Finding available capacity on adjacent nodes' },
    { name: 'Updating Routing Configuration', description: 'Modifying traffic steering rules' },
    { name: 'Migrating Active Sessions', description: 'Gradually shifting subscriber traffic' },
    { name: 'Validating Latency and QoS', description: 'Confirming service quality on new paths' },
  ],
  [ActionType.NODE_CAPACITY_REBALANCE]: [
    { name: 'Analyzing Node Utilization', description: 'Reviewing channel loading across node group' },
    { name: 'Identifying Overloaded Segments', description: 'Finding channels exceeding capacity thresholds' },
    { name: 'Computing Rebalance Plan', description: 'Calculating optimal modem-to-channel assignments' },
    { name: 'Migrating Subscriber Sessions', description: 'Moving modems to less loaded channels' },
    { name: 'Verifying Load Distribution', description: 'Confirming balanced utilization across channels' },
    { name: 'Performance Monitoring', description: 'Watching throughput and latency stabilization' },
  ],
};

export enum EventType {
  SESSION_START = 'session_start',
  SESSION_END = 'session_end',
  CHANNEL_BONDING_CHANGE = 'channel_bonding_change',
  MODEM_REGISTRATION = 'modem_registration',
  MODEM_OFFLINE = 'modem_offline',
  DATA_SESSION_START = 'data_session_start',
  DATA_SESSION_END = 'data_session_end',
  PROVISIONING = 'provisioning',
}

export enum IssueCategory {
  EQUIPMENT = 'equipment',
  CONFIGURATION = 'configuration',
  CAPACITY = 'capacity',
  EXTERNAL = 'external',
}

export enum Region {
  NORTHEAST = 'Northeast',
  SOUTHEAST = 'Southeast',
  MIDWEST = 'Midwest',
  SOUTH_CENTRAL = 'South Central',
  MOUNTAIN = 'Mountain',
  PACIFIC = 'Pacific',
  CANADA = 'Canada',
  LATIN_AMERICA = 'Latin America',
  EUROPE = 'Europe',
  MIDDLE_EAST = 'Middle East',
  APAC = 'Asia Pacific',
  OCEANIA = 'Oceania',
  AFRICA = 'Africa',
}

// Geographic filter regions for dashboard filtering
// Values cover US regional divisions + international regions
export enum GeographicRegion {
  NORTHEAST = 'NORTHEAST',
  SOUTHEAST = 'SOUTHEAST',
  MIDWEST = 'MIDWEST',
  SOUTH_CENTRAL = 'SOUTH_CENTRAL',
  MOUNTAIN = 'MOUNTAIN',
  PACIFIC = 'PACIFIC',
  CANADA = 'CANADA',
  LATIN_AMERICA = 'LATIN_AMERICA',
  EUROPE = 'EUROPE',
  MIDDLE_EAST = 'MIDDLE_EAST',
  APAC = 'APAC',
  OCEANIA = 'OCEANIA',
  AFRICA = 'AFRICA',
}

// Network element types beyond nodes
export enum NetworkElementType {
  NODE = 'node',
  AAU = 'aau',           // Active Antenna Unit
  HVAC = 'hvac',         // HVAC climate control
  SMSC = 'smsc',         // SMS Center
  HLR = 'hlr',           // Home Location Register
}

// Network element status
export enum NetworkElementStatus {
  OPERATIONAL = 'operational',
  DEGRADED = 'degraded',
  FAILED = 'failed',
  MAINTENANCE = 'maintenance',
  OFFLINE = 'offline',
}

export enum SiteType {
  MACRO = 'Macro',
  MICRO = 'Micro',
  SMALL_CELL = 'Small Cell',
  INDOOR_DAS = 'Indoor DAS',
  FEMTOCELL = 'Femtocell',
}

export enum SiteAccessType {
  ROOFTOP = 'Rooftop',
  GROUND_TOWER = 'Ground Tower',
  MONOPOLE = 'Monopole',
  BUILDING_MOUNTED = 'Building Mounted',
}

export enum BackhaulType {
  FIBER = 'Fiber',
  MICROWAVE = 'Microwave',
  SATELLITE = 'Satellite',
  COPPER = 'Copper',
}

export enum PowerSource {
  GRID = 'Grid',
  SOLAR = 'Solar',
  HYBRID = 'Hybrid',
  GENERATOR = 'Generator',
}

export enum TerrainType {
  URBAN = 'Urban',
  SUBURBAN = 'Suburban',
  RURAL = 'Rural',
  DENSE_URBAN = 'Dense Urban',
}

export enum SLATier {
  CRITICAL = 'Critical',
  STANDARD = 'Standard',
  BASIC = 'Basic',
}

export enum SiteAccessibility {
  EASY = 'Easy',
  MODERATE = 'Moderate',
  DIFFICULT = 'Difficult',
  REMOTE = 'Remote',
}

// Core data models
export interface FiberNode {
  node_id: string;
  headend_id?: string;
  hub_id?: string;
  service_area?: string;
  region: string;
  city?: string;
  state?: string;
  latitude: number;
  longitude: number;

  // Node Classification
  node_type?: string; // N+0, N+1, N+2, N+3
  homes_passed?: number;
  homes_active?: number;
  docsis_version?: string; // 3.0, 3.1, 4.0

  // RF Configuration
  downstream_channels?: number;
  upstream_channels?: number;
  ofdm_channels?: number;
  ofdma_channels?: number;

  // Equipment
  manufacturer?: string;
  hardware_model?: string;
  firmware_version?: string;

  // Power
  power_supply_count?: number;
  power_supply_status?: string; // all_ok, partial_failure, critical
  battery_backup_hours?: number;

  // Plant Details
  amplifier_cascade?: number;
  coax_plant_miles?: number;
  fiber_miles?: number;

  // Status & Maintenance
  status: NodeStatus;
  commissioned_date?: Date;
  last_maintenance?: Date;

  // Relationships
  neighbor_nodes?: string[];
}

export interface KPIMetrics {
  metric_id: string;
  node_id: string;
  timestamp: Date;
  // RF Signal Levels (DOCSIS)
  ds_power_level_dbmv: number;
  us_power_level_dbmv: number;
  ds_snr_db: number;
  us_snr_db: number;
  ds_mer_db: number;
  us_mer_db: number;
  // Forward Error Correction
  fec_corrected_codewords: number;
  fec_uncorrected_codewords: number;
  // DOCSIS Timeouts
  t3_timeouts: number;
  t4_timeouts: number;
  // Throughput
  downstream_throughput_mbps: number;
  upstream_throughput_mbps: number;
  // Network Performance
  latency_ms: number;
  packet_loss_percent: number;
  jitter_ms: number;
  // Channel Utilization
  ds_channel_utilization_percent: number;
  us_channel_utilization_percent: number;
  ofdm_utilization_percent: number;
  // Modem Counts
  active_modems: number;
  registered_modems: number;
  offline_modems: number;
  modems_with_flaps: number;
  // Equipment Health
  node_temperature: number;
  node_cpu_utilization: number;
  node_memory_utilization: number;
  power_supply_voltage: number;
}

export interface Alert {
  alert_id: string;
  node_id: string;
  timestamp: Date;
  alert_type: AlertType;
  severity: AlertSeverity;
  description: string;
  affected_kpis: string[];
  ai_confidence: number;
  model_name: string;
  root_cause?: string;
  status: AlertStatus;
  acknowledged_by?: string;
  resolved_at?: Date;
}

export interface SelfHealingAction {
  action_id: string;
  alert_id: string;
  node_id: string;
  timestamp: Date;
  action_type: ActionType;
  action_details: Record<string, unknown>;
  status: ActionStatus;
  effectiveness_score?: number;
  completion_time?: Date;
  rollback_available: boolean;
  automated: boolean;
  // Detailed remediation workflow tracking
  remediation_steps?: RemediationStep[];
  current_step_index?: number;
  step_started_at?: Date;
}

export interface NetworkEvent {
  event_id: string;
  node_id: string;
  timestamp: Date;
  event_type: EventType;
  source_node_id?: string;
  target_node_id?: string;
  user_id_hash: string;
  duration_seconds?: number;
  data_volume_mb?: number;
  qos_class: string;
  success: boolean;
  failure_reason?: string;
}

export interface CommonIssue {
  issue_id: string;
  issue_category: IssueCategory;
  description: string;
  occurrence_count: number;
  first_seen: Date;
  last_seen: Date;
  affected_nodes: number;
  common_factors: CommonFactors;
  avg_resolution_time: number;
  recommended_action: string;
  cost_impact: number;
}

export interface CommonFactors {
  time_of_day_pattern?: string;
  geographic_clustering?: string;
  technology_type?: TechnologyType[];
  equipment_vendor?: string;
  weather_conditions?: string;
  network_configuration?: string;
}

// Aggregated data models for efficiency
export interface NetworkHealthSummary {
  total_nodes: number;
  healthy_nodes: number;
  degraded_nodes: number;
  outage_nodes: number;
  maintenance_nodes: number;
  active_alerts: number;
  critical_alerts: number;
  warning_alerts: number;
  info_alerts: number;
  self_healing_actions_last_hour: number;
  network_availability: number;
  avg_ds_snr_db: number;
  total_active_modems: number;
  last_updated: Date;
}

export interface KPITrend {
  timestamp: Date;
  value: number;
}

export interface KPITrendData {
  ds_snr_db: KPITrend[];
  downstream_throughput_mbps: KPITrend[];
  packet_loss_percent: KPITrend[];
  latency_ms: KPITrend[];
}

// UI State types
export interface TimeWindow {
  value: number;
  unit: 'hour' | 'day';
  label: string;
}

export interface FilterOptions {
  severity?: AlertSeverity[];
  alertType?: AlertType[];
  region?: Region[];
  status?: AlertStatus[];
}

// Cache types for performance optimization
export interface CachedQuery<T> {
  data: T;
  timestamp: number;
  ttl: number; // Time to live in milliseconds
}

export type QueryCache = Map<string, CachedQuery<unknown>>;

// Environmental and Sensor Data Types
export interface AntennaSensorData {
  sensor_id: string;
  node_id: string;
  timestamp: Date;
  azimuth_angle: number; // 0-360 degrees
  tilt_angle: number; // -90 to 90 degrees (negative = downtilt)
  azimuth_drift: number; // degrees drifted from configured value
  tilt_drift: number; // degrees drifted from configured value
  last_calibration: Date;
  mechanical_health: number; // 0-100%
  motor_status: 'operational' | 'degraded' | 'failed';
  vibration_level: number; // 0-100 scale
}

export interface WeatherData {
  weather_id: string;
  node_id: string;
  timestamp: Date;
  temperature_celsius: number;
  humidity_percent: number;
  wind_speed_kmh: number;
  wind_direction: number; // 0-360 degrees
  precipitation_mm: number; // mm/hour
  atmospheric_pressure_hpa: number;
  visibility_km: number;
  conditions: 'clear' | 'cloudy' | 'rain' | 'snow' | 'fog' | 'storm' | 'extreme';
  lightning_detected: boolean;
}

export interface EnvironmentalSensor {
  sensor_id: string;
  node_id: string;
  timestamp: Date;
  power_quality: number; // 0-100%, voltage stability
  power_fluctuations: number; // number of fluctuations in last hour
  backup_battery_level: number; // 0-100%
  interference_level: number; // dBm, signal interference
  noise_floor: number; // dBm
  ground_resistance: number; // ohms
  cabinet_temperature: number; // celsius
  cabinet_humidity: number; // percent
  equipment_vibration: number; // 0-100 scale
  door_status: 'closed' | 'open' | 'tampered';
}

export interface EquipmentSensorData {
  sensor_id: string;
  node_id: string;
  timestamp: Date;
  component_health: ComponentHealth[];
  firmware_version: string;
  last_reboot: Date;
  uptime_hours: number;
  error_log_count: number; // errors in last 24h
  warning_log_count: number; // warnings in last 24h
  fan_speed_rpm: number;
  power_consumption_watts: number;
  signal_quality_db: number;
}

export interface ComponentHealth {
  component_name: string;
  component_type: 'baseband' | 'rf_unit' | 'antenna' | 'power_supply' | 'cooling' | 'backhaul' | 'gps';
  health_score: number; // 0-100%
  status: 'healthy' | 'degraded' | 'critical' | 'failed';
  last_maintenance: Date;
  estimated_remaining_life_days: number;
  manufacturer: string;
  serial_number: string;
}

// ============================================
// Network Elements (AAU, HVAC, SMSC, HLR)
// ============================================

// Active Antenna Unit (AAU) - main network component in node
export interface AAU {
  aau_id: string;
  node_id: string;
  sector_id: string;
  manufacturer: string;
  model: string;
  serial_number: string;
  firmware_version: string;
  status: NetworkElementStatus;

  // RF characteristics
  frequency_bands: string[];
  max_tx_power_watts: number;
  current_tx_power_watts: number;
  antenna_ports: number;
  mimo_config: string; // e.g., "64T64R", "32T32R"
  beamforming_enabled: boolean;

  // Performance metrics
  temperature_celsius: number;
  power_consumption_watts: number;
  vswr: number; // Voltage Standing Wave Ratio
  efficiency_percent: number;

  // Timestamps
  installed_date: Date;
  last_maintenance: Date;
  last_calibration: Date;
}

// HVAC Unit for node climate control
export interface HVACUnit {
  hvac_id: string;
  node_id: string;
  manufacturer: string;
  model: string;
  serial_number: string;
  status: NetworkElementStatus;

  // Operational parameters
  cooling_capacity_kw: number;
  heating_capacity_kw: number;
  current_mode: 'cooling' | 'heating' | 'fan_only' | 'off' | 'auto';
  setpoint_celsius: number;
  current_temp_celsius: number;
  humidity_percent: number;

  // Performance
  power_consumption_watts: number;
  compressor_status: 'running' | 'idle' | 'fault';
  filter_condition: 'good' | 'replace_soon' | 'replace_now';
  refrigerant_level_percent: number;

  // Alarms
  high_temp_alarm: boolean;
  low_temp_alarm: boolean;
  compressor_fault: boolean;

  // Timestamps
  installed_date: Date;
  last_maintenance: Date;
  last_filter_change: Date;
}

// SMS Center (SMSC) for messaging services
export interface SMSC {
  smsc_id: string;
  region: GeographicRegion;
  provider: string;
  name: string;
  status: NetworkElementStatus;

  // Capacity and load
  max_tps: number; // Transactions per second
  current_tps: number;
  queue_depth: number;
  max_queue_depth: number;

  // Performance metrics
  delivery_success_rate: number;
  avg_delivery_time_ms: number;
  pending_messages: number;
  failed_messages_24h: number;

  // Connectivity
  connected_hlrs: string[];
  connected_gateways: string[];
  primary_ip: string;
  backup_ip: string;

  // Hardware
  cpu_utilization: number;
  memory_utilization: number;
  storage_utilization: number;

  // Timestamps
  last_restart: Date;
  last_health_check: Date;
}

// Home Location Register (HLR) for subscriber/location tracking
export interface HLR {
  hlr_id: string;
  region: GeographicRegion;
  provider: string;
  name: string;
  status: NetworkElementStatus;

  // Capacity
  max_subscribers: number;
  active_subscribers: number;
  subscriber_utilization: number;

  // Performance
  query_rate_per_second: number;
  avg_response_time_ms: number;
  failed_queries_24h: number;
  location_update_rate: number;

  // Connectivity
  connected_mscs: string[]; // Mobile Switching Centers
  connected_sgsns: string[]; // SGSN nodes
  connected_mmes: string[]; // MME nodes (4G)

  // Replication
  replication_status: 'synced' | 'syncing' | 'out_of_sync' | 'error';
  replica_lag_ms: number;
  backup_hlr_id?: string;

  // Hardware
  cpu_utilization: number;
  memory_utilization: number;
  disk_utilization: number;

  // Timestamps
  last_backup: Date;
  last_sync: Date;
}

// Provider/Carrier information per geographic region
export interface Provider {
  provider_id: string;
  name: string;
  region: GeographicRegion;
  country: string;
  node_count: number;
  subscriber_count: number;
  market_share_percent: number;
  technologies: string[];
  primary_color: string; // For map visualization
}

// Geographic filter state
export interface GeographicFilter {
  regions: GeographicRegion[];
  providers: string[];
  showAAUs: boolean;
  showHVACs: boolean;
  showSMSCs: boolean;
  showHLRs: boolean;
}

// Enhanced AI Analysis with multi-source data
export interface EnhancedAnomalyContext {
  alert: Alert;
  node: FiberNode;
  recentKPIs: KPIMetrics[];
  antennaSensor?: AntennaSensorData[];
  weatherData?: WeatherData[];
  environmentalSensor?: EnvironmentalSensor[];
  equipmentSensor?: EquipmentSensorData[];
  neighborNodeData?: {
    node: FiberNode;
    kpis: KPIMetrics[];
    status: NodeStatus;
  }[];
}


// ============================================
// Network Configuration Management Types
// ============================================

export enum DeviceType {
  FIREWALL = 'firewall',
  SWITCH = 'switch',
  ROUTER = 'router',
  MODEM = 'modem',
}

export enum ComplianceStatus {
  COMPLIANT = 'compliant',
  DRIFTED = 'drifted',
  NON_COMPLIANT = 'non_compliant',
  UNKNOWN = 'unknown',
}

export enum ChangeRequestStatus {
  PENDING_REVIEW = 'pending_review',
  APPROVED = 'approved',
  REJECTED = 'rejected',
  EXECUTING = 'executing',
  COMPLETED = 'completed',
  FAILED = 'failed',
  CANCELLED = 'cancelled',
  ROLLED_BACK = 'rolled_back',
}

export interface NetworkDevice {
  id: number;
  device_id: string;
  device_type: string;
  device_role: string;
  hostname: string;
  description?: string;
  headend_id?: string;
  hub_id?: string;
  region?: string;
  manufacturer: string;
  hardware_model: string;
  serial_number?: string;
  firmware_version?: string;
  os_version?: string;
  management_ip?: string;
  interfaces?: { name: string; status: string; speed_gbps: number }[];
  uplink_speed_gbps?: number;
  status: string;
  last_seen?: string;
  uptime_seconds?: number;
  running_config?: Record<string, unknown>;
  config_hash?: string;
  compliance_status: string;
  last_compliance_scan?: string;
  last_config_change?: string;
  cpu_utilization?: number;
  memory_utilization?: number;
  temperature_celsius?: number;
  created_at?: string;
}

export interface ConfigChangeLog {
  change_id: string;
  device_id: string;
  change_request_id?: string;
  change_type: string;
  change_description?: string;
  config_diff?: Record<string, unknown>;
  status: string;
  applied_by?: string;
  change_timestamp: string;
  rollback_available: boolean;
  rollback_deadline?: string;
  rolled_back_at?: string;
}

export interface ConfigCompliance {
  compliance_id: string;
  device_id: string;
  compliance_status: string;
  severity: string;
  drift_details?: { field: string; expected: string; actual: string }[];
  drift_count: number;
  scan_timestamp: string;
  resolved_at?: string;
}

export interface ChangeRequest {
  request_id: string;
  title: string;
  description?: string;
  change_type: string;
  target_devices: { device_id: string; device_type: string; hostname: string }[];
  device_count: number;
  ai_risk_assessment?: string;
  ai_impact_score?: number;
  ai_recommendation?: string;
  status: string;
  requested_by?: string;
  reviewed_by?: string;
  approved_by?: string;
  approved_at?: string;
  execution_started_at?: string;
  execution_completed_at?: string;
  execution_log?: { device_id: string; status: string; change_id?: string }[];
  failure_reason?: string;
  rollback_available: boolean;
  rollback_deadline?: string;
  created_at?: string;
}

export interface DeviceSummary {
  total_devices: number;
  by_type: Record<string, number>;
  by_status: Record<string, number>;
  compliance_rate: number;
  drift_count: number;
  recent_changes: number;
}

export interface ComplianceSummary {
  overall_compliance_rate: number;
  totals: Record<string, number>;
  by_device_type: Record<string, {
    compliant: number;
    drifted: number;
    non_compliant: number;
    unknown: number;
    total: number;
  }>;
}

