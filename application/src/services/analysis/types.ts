/**
 * Node Analysis Types - All interfaces and types for the analysis modules
 */

// Equipment API response types
export interface EquipmentSummary {
  overall_health: string;
  aau_status: string;
  bbu_status: string;
  hvac_status: string;
  power_status: string;
  total_aau: number;
}

export interface EquipmentAPIResponse {
  node_id: string;
  aau_units: Array<{
    aau_id: string;
    status: string;
    temperature_celsius: number;
    efficiency_percent: number;
  }>;
  bbu: {
    status: string;
    cpu_utilization_percent: number;
    memory_utilization_percent: number;
    temperature_celsius: number;
  };
  hvac: {
    status: string;
    current_temp_celsius: number;
    setpoint_celsius: number;
    compressor_status: string;
    high_temp_alarm: boolean;
  };
  power: {
    grid_status: string;
    battery_health_percent: number;
    battery_backup_hours: number;
    ups_status: string;
    current_load_kw: number;
    max_load_kw: number;
  };
  summary: EquipmentSummary;
}

/**
 * Node Analysis Report structure
 */
export interface NodeAnalysisReport {
  nodeId: string;
  nodeName: string;
  generatedAt: Date;
  analysisStatus: 'generating' | 'complete' | 'error';
  error?: string;

  // Executive Summary
  executiveSummary: {
    overallHealth: 'excellent' | 'good' | 'fair' | 'poor' | 'critical';
    healthScore: number; // 0-100
    keyFindings: string[];
    urgentIssues: string[];
    recommendations: string[];
  };

  // Performance Analysis
  performanceAnalysis: {
    summary: string;
    kpiTrends: {
      metric: string;
      trend: 'improving' | 'stable' | 'declining';
      currentValue: number;
      avgValue: number;
      minValue: number;
      maxValue: number;
      interpretation: string;
    }[];
    anomalies: string[];
    comparisonToFleet: string;
  };

  // Equipment Status
  equipmentStatus: {
    summary: string;
    hardwareHealth: string;
    firmwareStatus: string;
    maintenanceNeeds: string[];
    endOfLifeWarnings: string[];
  };

  // Alert History Analysis
  alertAnalysis: {
    totalAlerts: number;
    criticalAlerts: number;
    warningAlerts: number;
    resolvedAlerts: number;
    activeAlerts: number;
    commonIssues: string[];
    patternAnalysis: string;
    // Actual alert list for drill-down
    alertList: {
      alert_id: string;
      alert_type: string;
      severity: 'critical' | 'warning' | 'info';
      status: string;
      description: string;
      timestamp: Date;
    }[];
  };

  // Remediation Effectiveness
  remediationAnalysis: {
    totalActions: number;
    successRate: number;
    avgResolutionTime: string;
    mostEffectiveActions: string[];
    failedActions: number;
    improvementSuggestions: string[];
  };

  // Predictive Insights
  predictiveInsights: {
    riskScore: number; // 0-100
    potentialIssues: string[];
    maintenanceRecommendations: string[];
    capacityForecast: string;
  };

  // Raw Data Summary (for debugging/verification)
  rawDataSummary: {
    kpiRecordsAnalyzed: number;
    alertsAnalyzed: number;
    actionsAnalyzed: number;
    timeRangeStart: Date;
    timeRangeEnd: Date;
  };
}

/**
 * Analysis Agent types for modular analysis
 */
export type AnalysisAgent = 'performance' | 'equipment' | 'alerts' | 'remediation' | 'predictive';

/**
 * Helper to safely convert a date value (string or Date) to Date object
 */
export const toDate = (value: Date | string | undefined | null): Date => {
  if (!value) return new Date();
  if (value instanceof Date) return value;
  const parsed = new Date(value);
  return isNaN(parsed.getTime()) ? new Date() : parsed;
};
