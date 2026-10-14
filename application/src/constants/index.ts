import { Region, TechnologyType, GeographicRegion } from '@/types';

// Geographic constants for regional node distribution
export const REGION_COORDINATES: Record<Region, { lat: [number, number]; lng: [number, number] }> = {
  [Region.NORTHEAST]: { lat: [39.8, 43.2], lng: [-75.2, -70.0] },
  [Region.SOUTHEAST]: { lat: [24.8, 37.0], lng: [-88.0, -79.5] },
  [Region.MIDWEST]: { lat: [38.1, 46.0], lng: [-95.8, -81.8] },
  [Region.SOUTH_CENTRAL]: { lat: [28.4, 34.0], lng: [-99.8, -95.5] },
  [Region.MOUNTAIN]: { lat: [32.2, 42.0], lng: [-113.2, -103.8] },
  [Region.PACIFIC]: { lat: [33.0, 49.8], lng: [-124.0, -116.5] },
  [Region.CANADA]: { lat: [42.8, 49.8], lng: [-124.0, -78.0] },
  [Region.LATIN_AMERICA]: { lat: [-35.0, 20.5], lng: [-100.0, -45.5] },
  [Region.EUROPE]: { lat: [48.5, 52.2], lng: [-1.0, 9.5] },
  [Region.MIDDLE_EAST]: { lat: [23.5, 30.5], lng: [31.0, 56.5] },
  [Region.APAC]: { lat: [-6.6, 37.8], lng: [72.3, 140.4] },
  [Region.OCEANIA]: { lat: [-38.2, -33.0], lng: [143.8, 151.8] },
  [Region.AFRICA]: { lat: [-26.6, 6.8], lng: [3.0, 37.2] },
};

// Node distribution targets (total = 7200)
export const NODES_PER_REGION: Record<Region, number> = {
  [Region.NORTHEAST]: 480,
  [Region.SOUTHEAST]: 920,
  [Region.MIDWEST]: 840,
  [Region.SOUTH_CENTRAL]: 440,
  [Region.MOUNTAIN]: 520,
  [Region.PACIFIC]: 680,
  [Region.CANADA]: 320,
  [Region.LATIN_AMERICA]: 560,
  [Region.EUROPE]: 560,
  [Region.MIDDLE_EAST]: 280,
  [Region.APAC]: 680,
  [Region.OCEANIA]: 320,
  [Region.AFRICA]: 440,
};

// Cable network equipment manufacturers
export const MANUFACTURERS: string[] = [
  'Cisco',
  'CommScope/Arris',
  'Casa Systems',
  'Harmonic',
  'Vecima Networks',
  'Calix',
];

// Hardware models by manufacturer
export const HARDWARE_MODELS: Record<string, string[]> = {
  'Cisco': ['cBR-8', 'ASR 9000', 'NCS 5500', 'Catalyst 8500', 'CBR-D30'],
  'CommScope/Arris': ['E6000', 'CER 2400', 'CM8200', 'SG4860', 'TG3482'],
  'Casa Systems': ['C100G', 'C40G', 'C10G', 'Axyom 1024', 'CCAP'],
  'Harmonic': ['CableOS', 'NSG Pro', 'XOS', 'Electra X2', 'Proview'],
  'Vecima Networks': ['Entra EX440', 'Entra EN2261', 'Terrace QAM', 'Terrace RPS', 'DAA Node'],
  'Calix': ['E9-2', 'E7-2', 'GigaSpire BLAST', 'GP4200', 'GP1100'],
};

// Firmware version ranges by manufacturer
export const FIRMWARE_VERSIONS: Record<string, { major: [number, number], minor: [number, number] }> = {
  'Cisco': { major: [16, 17], minor: [1, 12] },
  'CommScope/Arris': { major: [10, 13], minor: [0, 15] },
  'Casa Systems': { major: [7, 10], minor: [0, 18] },
  'Harmonic': { major: [3, 6], minor: [0, 20] },
  'Vecima Networks': { major: [4, 7], minor: [1, 10] },
  'Calix': { major: [22, 25], minor: [0, 12] },
};

// DOCSIS channel frequency bands
export const FREQUENCY_BANDS: Record<string, string[]> = {
  'DOCSIS 3.0': ['108 MHz', '258 MHz', '450 MHz', '600 MHz'],
  'DOCSIS 3.1': ['108 MHz', '258 MHz', '450 MHz', '600 MHz', '750 MHz', '1002 MHz'],
  'DOCSIS 4.0': ['108 MHz', '258 MHz', '450 MHz', '600 MHz', '750 MHz', '1218 MHz', '1794 MHz'],
  'FTTH': ['1310 nm', '1490 nm', '1550 nm'],
};

// Site owners (cable MSOs and ISPs)
export const SITE_OWNERS = [
  'Comcast/Xfinity', 'Charter Spectrum', 'Cox Communications', 'Altice USA',
  'Mediacom', 'Cable One/Sparklight', 'WOW! Internet', 'Breezeline',
  'Midco', 'Atlantic Broadband', 'Astound Broadband', 'RCN',
  'Grande Communications', 'Wave Broadband', 'Suddenlink', 'TDS Telecom',
];

// Climate zones
export const CLIMATE_ZONES = [
  'Tropical', 'Arid', 'Temperate', 'Continental', 'Polar',
  'Mediterranean', 'Subtropical', 'Oceanic',
];

// Generator types
export const GENERATOR_TYPES = [
  'Diesel', 'Natural Gas', 'Propane', 'Hybrid Diesel-Solar',
];

// Core network nodes (example naming convention)
export const CORE_NETWORK_PREFIXES = ['CMTS', 'OLT', 'EDGE', 'AGG', 'CORE'];

// Site type distribution probabilities
export const SITE_TYPE_DISTRIBUTION: Record<string, number> = {
  'Macro': 0.65,        // 65% - Most common for wide area coverage
  'Micro': 0.20,        // 20% - Urban areas
  'Small Cell': 0.10,   // 10% - Dense urban, capacity boost
  'Indoor DAS': 0.04,   // 4% - Buildings, venues
  'Femtocell': 0.01,    // 1% - Rare in network operator deployments
};

// Structure height ranges by site type (meters)
export const STRUCTURE_HEIGHT_RANGES: Record<string, [number, number]> = {
  'Macro': [30, 60],
  'Micro': [10, 20],
  'Small Cell': [5, 10],
  'Indoor DAS': [3, 8],
  'Femtocell': [2, 4],
};

// Coverage radius by site type (km)
export const COVERAGE_RADIUS_RANGES: Record<string, [number, number]> = {
  'Macro': [2, 35],
  'Micro': [0.5, 2],
  'Small Cell': [0.1, 0.5],
  'Indoor DAS': [0.05, 0.2],
  'Femtocell': [0.01, 0.05],
};

// Backhaul capacity ranges by type (Mbps)
export const BACKHAUL_CAPACITY_RANGES: Record<string, [number, number]> = {
  'Fiber': [1000, 10000],      // 1-10 Gbps
  'Microwave': [100, 1000],    // 100 Mbps - 1 Gbps
  'Satellite': [10, 100],      // 10-100 Mbps
  'Copper': [10, 100],         // 10-100 Mbps
};

// Power consumption by site type (kW)
export const POWER_CONSUMPTION_RANGES: Record<string, [number, number]> = {
  'Macro': [3, 8],
  'Micro': [1, 3],
  'Small Cell': [0.1, 0.5],
  'Indoor DAS': [0.5, 2],
  'Femtocell': [0.01, 0.05],
};

// Typical sector configurations
export const SECTOR_CONFIGURATIONS = {
  STANDARD_3_SECTOR: [0, 120, 240],      // Most common
  OMNIDIRECTIONAL: [0],                   // Micro/small cells
  DUAL_SECTOR: [0, 180],                  // Some urban deployments
  SIX_SECTOR: [0, 60, 120, 180, 240, 300], // Dense urban capacity boost
};

export const CITIES_BY_REGION: Record<Region, string[]> = {
  [Region.NORTHEAST]: ['New York City', 'Boston', 'Manhattan', 'Brooklyn', 'Queens', 'Stamford', 'Cambridge', 'Quincy'],
  [Region.SOUTHEAST]: ['Charlotte', 'Tampa', 'Atlanta', 'Miami', 'Nashville', 'Fort Lauderdale', 'Murfreesboro', 'Concord'],
  [Region.MIDWEST]: ['Chicago', 'Columbus', 'Minneapolis', 'Detroit', 'Kansas City', 'St. Paul', 'Warren', 'Overland Park'],
  [Region.SOUTH_CENTRAL]: ['Dallas', 'Fort Worth', 'San Antonio', 'Arlington', 'Plano', 'New Braunfels', 'Denton', 'Waxahachie'],
  [Region.MOUNTAIN]: ['Denver', 'Salt Lake City', 'Phoenix', 'Mesa', 'Scottsdale', 'Boulder', 'Ogden', 'Chandler'],
  [Region.PACIFIC]: ['Los Angeles', 'Seattle', 'Portland', 'Long Beach', 'Anaheim', 'Tacoma', 'Beaverton', 'Riverside'],
  [Region.CANADA]: ['Toronto', 'Vancouver', 'Mississauga', 'Brampton', 'Surrey', 'Burnaby', 'Oakville', 'Burlington'],
  [Region.LATIN_AMERICA]: ['Mexico City', 'Sao Paulo', 'Buenos Aires', 'Guarulhos', 'Campinas', 'La Plata', 'Ecatepec', 'Quilmes'],
  [Region.EUROPE]: ['London', 'Frankfurt', 'Paris', 'Versailles', 'Reading', 'Wiesbaden', 'Saint-Denis', 'Croydon'],
  [Region.MIDDLE_EAST]: ['Dubai', 'Cairo', 'Abu Dhabi', 'Giza', 'Sharjah', 'Ajman', 'Al Ain', 'Heliopolis'],
  [Region.APAC]: ['Tokyo', 'Mumbai', 'Seoul', 'Singapore', 'Jakarta', 'Yokohama', 'Incheon', 'Bekasi'],
  [Region.OCEANIA]: ['Sydney', 'Melbourne', 'Geelong', 'Parramatta', 'Penrith', 'Dandenong', 'Blacktown', 'Frankston'],
  [Region.AFRICA]: ['Lagos Island', 'Johannesburg', 'Nairobi CBD', 'Pretoria', 'Ikeja', 'Sandton', 'Thika', 'Soweto'],
};

// KPI thresholds for anomaly detection (relaxed for realistic demo)
export const KPI_THRESHOLDS = {
  ds_snr_db: { critical: 25, warning: 30, healthy: 35 }, // dB - higher is better
  packet_loss_percent: { critical: 5, warning: 2, healthy: 1 },
  us_snr_db: { critical: 20, warning: 25, healthy: 30 }, // dB - higher is better
  latency_ms: { critical: 150, warning: 80, healthy: 30 }, // ms
  downstream_throughput_mbps: { critical: 50, warning: 100, healthy: 200 }, // Mbps
  node_cpu_utilization: { critical: 95, warning: 85, healthy: 70 },
  node_memory_utilization: { critical: 90, warning: 80, healthy: 65 },
  node_temperature: { critical: 80, warning: 70, healthy: 55 }, // Celsius
};

// Time windows for KPI trend charts
export const TIME_WINDOWS = [
  { value: 1, unit: 'hour' as const, label: '1 Hour' },
  { value: 6, unit: 'hour' as const, label: '6 Hours' },
  { value: 24, unit: 'hour' as const, label: '24 Hours' },
];

// Technology adoption rates (for realistic distribution)
export const TECHNOLOGY_ADOPTION: Record<TechnologyType, number> = {
  [TechnologyType.DOCSIS_30]: 0.15,
  [TechnologyType.DOCSIS_31]: 0.50,
  [TechnologyType.DOCSIS_40]: 0.20,
  [TechnologyType.FTTH]: 0.15,
};

// Cache configuration for query optimization (increased TTLs for better performance)
export const CACHE_CONFIG = {
  NODE_DATA: 60000, // 1 minute
  KPI_METRICS: 10000, // 10 seconds (increased from 5s)
  ALERTS: 15000, // 15 seconds (increased from 10s)
  ACTIONS: 15000, // 15 seconds (increased from 10s)
  NETWORK_HEALTH: 10000, // 10 seconds (increased from 5s)
  COMMON_ISSUES: 300000, // 5 minutes
};

// Update intervals for real-time simulation
// Increased intervals to reduce memory pressure and CPU usage
export const UPDATE_INTERVALS = {
  KPI_GENERATION: 300000, // Backend samples each node every 5 min (KPI_GENERATION_INTERVAL_SECONDS), in 30s rotating slices
  ALERT_CHECK: 10000, // Check for anomalies every 10 seconds
  SELF_HEALING: 15000, // Process self-healing every 15 seconds
  UI_REFRESH: 10000, // UI refresh rate - 10 seconds (increased from 5s to reduce memory churn)
  AI_ANALYSIS: 60000, // AI analysis every 60 seconds (increased from 30s)
  AI_PATTERN_ANALYSIS: 120000, // Pattern analysis every 2 minutes (increased from 60s)
};

// Failure scenario probabilities (per hour per node)
export const FAILURE_PROBABILITIES = {
  NODE_OUTAGE: 0.001,
  DEGRADED_SERVICE: 0.01,
  HIGH_PACKET_LOSS: 0.02,
  CONGESTION: 0.05,
  EQUIPMENT_FAILURE: 0.005,
  SIGNAL_DEGRADATION: 0.03,
};

// Self-healing action effectiveness ranges
export const ACTION_EFFECTIVENESS = {
  LOAD_BALANCE: { min: 70, max: 95 },
  PARAMETER_OPTIMIZATION: { min: 60, max: 90 },
  NODE_REBOOT: { min: 80, max: 100 },
  TRAFFIC_REROUTING: { min: 75, max: 95 },
  RF_ADJUSTMENT: { min: 65, max: 85 },
  TICKET_CREATION: { min: 50, max: 70 },
  CAPACITY_EXPANSION: { min: 70, max: 90 },
};

// Database configuration
// Note: Backend now uses tiered retention (raw: 1hr, 1min: 6hr, 5min: 24hr, hourly: 7d, daily: 30d)
// Frontend keeps minimal data in memory - relies on backend/NVMe for storage
export const DB_CONFIG = {
  RETENTION_DAYS: 1, // Keep only 1 day in frontend memory (backend has full history on NVMe)
  INITIAL_HISTORY_DAYS: 1, // Generate 1 day of historical data at startup
  BATCH_SIZE: 100, // For bulk inserts
  MAX_RECORDS: 5000, // Maximum KPI records in frontend memory (rely on backend for more)
  MAX_ALERTS: 200, // Maximum alerts in memory
  MAX_ACTIONS: 200, // Maximum actions in memory
  PERSIST_INTERVAL_MS: 15000, // Save to IndexedDB every 15 seconds
  INDEXEDDB_MAX_RECORDS: 2000, // Maximum records to persist to IndexedDB
};

// ============================================
// Geographic Filtering Configuration
// ============================================

// Providers by region (fictional cable/ISP providers per region)
export const PROVIDERS_BY_REGION: Record<GeographicRegion, string[]> = {
  [GeographicRegion.NORTHEAST]: ['Liberty Cable', 'Harbor Broadband', 'Atlantic Fiber', 'Patriot Cable'],
  [GeographicRegion.SOUTHEAST]: ['Magnolia Cable', 'Palmetto Broadband', 'Peachtree Fiber', 'Gulf Cable'],
  [GeographicRegion.MIDWEST]: ['Prairie Cable', 'Heartland Broadband', 'Great Lakes Fiber', 'Plains Cable'],
  [GeographicRegion.SOUTH_CENTRAL]: ['Lone Star Cable', 'Frontier Broadband', 'Red River Fiber', 'Rio Grande Cable'],
  [GeographicRegion.MOUNTAIN]: ['Summit Cable', 'Rocky Mountain Broadband', 'Desert Fiber', 'Crest Cable'],
  [GeographicRegion.PACIFIC]: ['Cascade Cable', 'Pacific Broadband', 'Golden State Fiber', 'Coastal Cable'],
  [GeographicRegion.CANADA]: ['Maple Broadband', 'Northern Cable', 'Aurora Fiber', 'Boreal Cable'],
  [GeographicRegion.LATIN_AMERICA]: ['Sol Cable', 'Andes Broadband', 'Rio Fiber', 'Aztec Cable'],
  [GeographicRegion.EUROPE]: ['Europa Cable', 'Continental Broadband', 'Thames Fiber', 'Rhine Cable'],
  [GeographicRegion.MIDDLE_EAST]: ['Oasis Cable', 'Crescent Broadband', 'Gulf Fiber', 'Dunes Cable'],
  [GeographicRegion.APAC]: ['Orient Cable', 'Dragon Broadband', 'Lotus Fiber', 'Monsoon Cable'],
  [GeographicRegion.OCEANIA]: ['Southern Cross Cable', 'Outback Broadband', 'Coral Fiber', 'Kiwi Cable'],
  [GeographicRegion.AFRICA]: ['Savanna Cable', 'Sahel Broadband', 'Kilimanjaro Fiber', 'Ubuntu Cable'],
};

// Service area to geographic region mapping (backend sets node.region to service area name)
export const SERVICE_AREA_TO_REGION: Record<string, GeographicRegion> = {
  // Northeast
  'New York City': GeographicRegion.NORTHEAST,
  'Boston': GeographicRegion.NORTHEAST,
  // Southeast
  'Charlotte': GeographicRegion.SOUTHEAST,
  'Tampa Bay': GeographicRegion.SOUTHEAST,
  'Atlanta': GeographicRegion.SOUTHEAST,
  'Miami': GeographicRegion.SOUTHEAST,
  'Nashville': GeographicRegion.SOUTHEAST,
  // Midwest
  'Chicago': GeographicRegion.MIDWEST,
  'Columbus': GeographicRegion.MIDWEST,
  'Minneapolis': GeographicRegion.MIDWEST,
  'Detroit': GeographicRegion.MIDWEST,
  'Kansas City': GeographicRegion.MIDWEST,
  // South Central
  'Dallas-Fort Worth': GeographicRegion.SOUTH_CENTRAL,
  'San Antonio': GeographicRegion.SOUTH_CENTRAL,
  // Mountain
  'Denver': GeographicRegion.MOUNTAIN,
  'Salt Lake City': GeographicRegion.MOUNTAIN,
  'Phoenix': GeographicRegion.MOUNTAIN,
  // Pacific
  'Los Angeles': GeographicRegion.PACIFIC,
  'Seattle': GeographicRegion.PACIFIC,
  'Portland': GeographicRegion.PACIFIC,
  // Canada
  'Toronto': GeographicRegion.CANADA,
  'Vancouver': GeographicRegion.CANADA,
  // Latin America
  'Mexico City': GeographicRegion.LATIN_AMERICA,
  'Sao Paulo': GeographicRegion.LATIN_AMERICA,
  'Buenos Aires': GeographicRegion.LATIN_AMERICA,
  // Europe
  'London': GeographicRegion.EUROPE,
  'Frankfurt': GeographicRegion.EUROPE,
  'Paris': GeographicRegion.EUROPE,
  // Middle East
  'Dubai': GeographicRegion.MIDDLE_EAST,
  'Cairo': GeographicRegion.MIDDLE_EAST,
  // APAC
  'Tokyo': GeographicRegion.APAC,
  'Mumbai': GeographicRegion.APAC,
  'Seoul': GeographicRegion.APAC,
  'Singapore': GeographicRegion.APAC,
  'Jakarta': GeographicRegion.APAC,
  // Oceania
  'Sydney': GeographicRegion.OCEANIA,
  'Melbourne': GeographicRegion.OCEANIA,
  // Africa
  'Lagos': GeographicRegion.AFRICA,
  'Johannesburg': GeographicRegion.AFRICA,
  'Nairobi': GeographicRegion.AFRICA,
};

// Default geographic region by base region (identity mapping)
export const REGION_TO_GEOGRAPHIC_REGION: Record<Region, GeographicRegion> = {
  [Region.NORTHEAST]: GeographicRegion.NORTHEAST,
  [Region.SOUTHEAST]: GeographicRegion.SOUTHEAST,
  [Region.MIDWEST]: GeographicRegion.MIDWEST,
  [Region.SOUTH_CENTRAL]: GeographicRegion.SOUTH_CENTRAL,
  [Region.MOUNTAIN]: GeographicRegion.MOUNTAIN,
  [Region.PACIFIC]: GeographicRegion.PACIFIC,
  [Region.CANADA]: GeographicRegion.CANADA,
  [Region.LATIN_AMERICA]: GeographicRegion.LATIN_AMERICA,
  [Region.EUROPE]: GeographicRegion.EUROPE,
  [Region.MIDDLE_EAST]: GeographicRegion.MIDDLE_EAST,
  [Region.APAC]: GeographicRegion.APAC,
  [Region.OCEANIA]: GeographicRegion.OCEANIA,
  [Region.AFRICA]: GeographicRegion.AFRICA,
};

// Provider colors for map visualization
export const PROVIDER_COLORS: Record<string, string> = {
  // Northeast
  'Liberty Cable': '#cd040b',
  'Harbor Broadband': '#00a8e0',
  'Atlantic Fiber': '#e20074',
  'Patriot Cable': '#0033a0',
  // Southeast
  'Magnolia Cable': '#da291c',
  'Palmetto Broadband': '#003087',
  'Peachtree Fiber': '#4b286d',
  'Gulf Cable': '#2bb673',
  // Midwest
  'Prairie Cable': '#e60000',
  'Heartland Broadband': '#ff7300',
  'Great Lakes Fiber': '#00b2a9',
  'Plains Cable': '#231f20',
  // South Central
  'Lone Star Cable': '#007b85',
  'Frontier Broadband': '#e60000',
  'Red River Fiber': '#ff7900',
  'Rio Grande Cable': '#0019a5',
  // Mountain
  'Summit Cable': '#e20074',
  'Rocky Mountain Broadband': '#ff7900',
  'Desert Fiber': '#00a0df',
  'Crest Cable': '#001155',
  // Pacific
  'Cascade Cable': '#0078d4',
  'Pacific Broadband': '#da0000',
  'Golden State Fiber': '#ea002a',
  'Coastal Cable': '#ffd500',
  // Canada
  'Maple Broadband': '#da291c',
  'Northern Cable': '#003087',
  'Aurora Fiber': '#4b286d',
  'Boreal Cable': '#2bb673',
  // Latin America
  'Sol Cable': '#ffcc00',
  'Andes Broadband': '#00a0df',
  'Rio Fiber': '#660099',
  'Aztec Cable': '#00348a',
  // Europe
  'Europa Cable': '#e20074',
  'Continental Broadband': '#ff7900',
  'Thames Fiber': '#00b2a9',
  'Rhine Cable': '#001155',
  // Middle East
  'Oasis Cable': '#5cb95c',
  'Crescent Broadband': '#4f2683',
  'Gulf Fiber': '#ff0066',
  'Dunes Cable': '#3cc3dc',
  // APAC
  'Orient Cable': '#e60012',
  'Dragon Broadband': '#da0000',
  'Lotus Fiber': '#ea002a',
  'Monsoon Cable': '#0078d4',
  // Oceania
  'Southern Cross Cable': '#4cc34c',
  'Outback Broadband': '#0064d2',
  'Coral Fiber': '#e60000',
  'Kiwi Cable': '#ffd500',
  // Africa
  'Savanna Cable': '#228b22',
  'Sahel Broadband': '#daa520',
  'Kilimanjaro Fiber': '#8b4513',
  'Ubuntu Cable': '#e74c3c',
};

// Cable amplifier/node manufacturers and models
export const AAU_MANUFACTURERS: Record<string, string[]> = {
  'Cisco': ['GS7000', 'GS7600', 'CBR-8 LC', 'RPD-1600'],
  'CommScope/Arris': ['NC4000', 'NC2000', 'AM6000', 'GX2-RX200'],
  'Casa Systems': ['A1000', 'A5200', 'A3100', 'A7200'],
  'Harmonic': ['NSG-EXO', 'VOS360', 'CableOS R3', 'Proview 8100'],
  'Vecima Networks': ['EN2261', 'EX440', 'EX220', 'EN4200'],
};

// HVAC manufacturers
export const HVAC_MANUFACTURERS: string[] = [
  'Vertiv', 'Schneider Electric', 'Emerson', 'Delta', 'Huawei NetEngine',
];

// CMTS/OLT network element names by region
export const CORE_ELEMENT_NAMES: Record<GeographicRegion, { smsc: string[], hlr: string[] }> = {
  [GeographicRegion.NORTHEAST]: {
    smsc: ['CMTS-NE-NYC', 'CMTS-NE-BOS'],
    hlr: ['OLT-NE-PRIMARY', 'OLT-NE-SECONDARY'],
  },
  [GeographicRegion.SOUTHEAST]: {
    smsc: ['CMTS-SE-ATL', 'CMTS-SE-MIA', 'CMTS-SE-CLT', 'CMTS-SE-TPA'],
    hlr: ['OLT-SE-PRIMARY', 'OLT-SE-SECONDARY', 'OLT-SE-DR'],
  },
  [GeographicRegion.MIDWEST]: {
    smsc: ['CMTS-MW-CHI', 'CMTS-MW-DET', 'CMTS-MW-MSP', 'CMTS-MW-CMH'],
    hlr: ['OLT-MW-PRIMARY', 'OLT-MW-SECONDARY', 'OLT-MW-DR'],
  },
  [GeographicRegion.SOUTH_CENTRAL]: {
    smsc: ['CMTS-SC-DFW', 'CMTS-SC-SAT'],
    hlr: ['OLT-SC-PRIMARY', 'OLT-SC-SECONDARY'],
  },
  [GeographicRegion.MOUNTAIN]: {
    smsc: ['CMTS-MT-DEN', 'CMTS-MT-PHX', 'CMTS-MT-SLC'],
    hlr: ['OLT-MT-PRIMARY', 'OLT-MT-SECONDARY'],
  },
  [GeographicRegion.PACIFIC]: {
    smsc: ['CMTS-PC-LAX', 'CMTS-PC-SEA', 'CMTS-PC-PDX'],
    hlr: ['OLT-PC-PRIMARY', 'OLT-PC-SECONDARY', 'OLT-PC-DR'],
  },
  [GeographicRegion.CANADA]: {
    smsc: ['CMTS-CA-TOR'],
    hlr: ['OLT-CA-PRIMARY', 'OLT-CA-SECONDARY'],
  },
  [GeographicRegion.LATIN_AMERICA]: {
    smsc: ['CMTS-LA-MEX', 'CMTS-LA-SAO'],
    hlr: ['OLT-LA-PRIMARY', 'OLT-LA-SECONDARY'],
  },
  [GeographicRegion.EUROPE]: {
    smsc: ['CMTS-EU-LON', 'CMTS-EU-FRA'],
    hlr: ['OLT-EU-PRIMARY', 'OLT-EU-SECONDARY'],
  },
  [GeographicRegion.MIDDLE_EAST]: {
    smsc: ['CMTS-ME-DXB'],
    hlr: ['OLT-ME-PRIMARY', 'OLT-ME-SECONDARY'],
  },
  [GeographicRegion.APAC]: {
    smsc: ['CMTS-AP-TYO', 'CMTS-AP-BOM', 'CMTS-AP-SIN'],
    hlr: ['OLT-AP-PRIMARY', 'OLT-AP-SECONDARY', 'OLT-AP-DR'],
  },
  [GeographicRegion.OCEANIA]: {
    smsc: ['CMTS-OC-SYD', 'CMTS-OC-MEL'],
    hlr: ['OLT-OC-PRIMARY', 'OLT-OC-SECONDARY'],
  },
  [GeographicRegion.AFRICA]: {
    smsc: ['CMTS-AF-LOS', 'CMTS-AF-JNB', 'CMTS-AF-NBO'],
    hlr: ['OLT-AF-PRIMARY', 'OLT-AF-SECONDARY'],
  },
};
