/**
 * API Module Barrel Export
 * Re-exports all API functions and types from domain-specific modules
 */

// Core client utilities
export { apiRequest, apiClient, getApiBaseUrl } from './baseClient';

// Node operations
export {
  getNodes,
  getNodeById,
  getNodeMetadataSummary,
  generateNodes,
  type FiberNodeResponse,
  type NodeMetadataSummary,
} from './nodeApi';

// Headend operations (legacy headend API with pagination)
export {
  getHeadends as getDatacenters,
  getHeadendMetadataSummary as getDatacenterMetadataSummary,
  type HeadendResponse as DatacenterResponse,
  type HeadendMetadataSummary as DatacenterMetadataSummary,
  getHeadendMetadataSummary,
  type HeadendResponse,
  type HeadendMetadataSummary,
} from './headendApi';

// KPI metrics
export {
  getKPIs,
  generateKPIs,
  generateHistoricalKPIs,
  getAggregatedKPIs,
  type KPIMetricsResponse,
  type AggregatedKPIData,
  type AggregatedKPIsResponse,
} from './kpiApi';

// Alerts
export {
  getAlerts,
  generateAlerts,
  type AlertsResponse,
} from './alertApi';

// Self-healing actions
export {
  getActions,
  cleanupOldActions,
  generateActions,
  type ActionsResponse,
} from './actionApi';

// System health, stats, and control
export {
  getStats,
  checkBackendHealth,
  getSystemStatus,
  pauseSystem,
  resumeSystem,
  isLLMPaused,
  type StatsResponse,
  type SystemStatus,
} from './systemApi';

// LLM configuration
export {
  getLLMConfig,
  createOrUpdateLLMConfig,
  updateLLMConfig,
  deleteLLMConfig,
  type LLMConfig,
  type LLMConfigCreate,
  type LLMConfigUpdate,
} from './llmApi';

// AI insights, analyses, and action plans
export {
  getAIInsights,
  triggerAIAnalysis,
  getAIAnalyses,
  getAIActionPlans,
  getAIActionPlan,
  cancelAIActionPlan,
  analyzeAndExecuteAlert,
  getAIStatus,
  type AIInsight,
  type AIInsightsResponse,
  type AIAnalysis,
  type AIAnalysisListResponse,
  type AIActionStep,
  type AIActionPlan,
  type AIActionPlanListResponse,
  type AnalyzeAndExecuteResponse,
  type AIStatus,
} from './aiApi';

// SLA and financial
export {
  getSLAStatus,
  getFinancialSummary,
  type SLAConfig,
  type SLAStatus,
  type FinancialSummary,
} from './slaApi';

// Simulation / digital twin
export {
  runSimulation,
  getSimulationResults,
  deleteSimulationResult,
  deleteSimulationResultsBatch,
  getSimulationHistoricalContext,
  type SimulatedMetrics,
  type BaselineMetrics,
  type SimulationResult,
  type SimulationResultListResponse,
  type RunSimulationRequest,
  type HistoricalBaselines,
  type SimilarHistoricalIncident,
  type SimulationHistoricalContext,
} from './simulationApi';

// Capacity planning
export {
  startAgenticCapacityPlanning,
  getAgenticCapacityPlanningStatus,
  type CapacityForecast,
  type BandwidthBottleneck,
  type CapacityConstraint,
  type AgentThought,
  type UpgradeImpactAnalysis,
  type HardwareCompatibilityReport,
  type AgenticCapacityPlanningRequest,
  type AgenticCapacityPlanningStartResponse,
  type DatacenterComponentStatus,
  type SiteAnalysis,
  type DatacenterAnalysis,
  type UpgradeRecommendation,
  type DatacenterForecastPeriod,
  type DatacenterForecast,
  type AgenticCapacityPlanningStatus,
} from './capacityPlanningApi';

// Core network infrastructure
export {
  getHeadends,
  getHubs,
  getAmplifiers,
  getNetworkDevices,
  type Headend,
  type HeadendsResponse,
  type Hub,
  type HubsResponse,
  type Amplifier,
  type AmplifiersResponse,
  type NetworkDevice,
  type NetworkDevicesResponse,
} from './coreNetworkApi';

// Customer intelligence
export {
  getCustomerOverview,
  getCustomerList,
  getSentimentSummary,
  getPlanBreakdown,
  type CustomerOverview,
  type CustomerRecord,
  type CustomerListResponse,
  type SentimentSummary,
  type PlanBreakdown,
} from './customerApi';

// Executive dashboard
export {
  getExecutiveSummary,
  type ExecutiveSummary,
} from './executiveApi';

// Config management
export {
  getDeviceSummary,
  getDevices,
  getDeviceDetail,
  syncDevice,
  getTemplates,
  getChanges,
  rollbackChange,
  getComplianceSummary,
  triggerComplianceScan,
  getChangeRequests,
  createChangeRequest,
  updateChangeRequest,
  executeChangeRequest,
} from './configManagementApi';

// Packet-capture analysis
export {
  analyzePcap,
  listCaptures,
  getCapture,
  pcapChat,
  generatePcapReport,
  downloadPcapDocx,
} from './packetApi';

// Edge data center anomaly flow
export {
  listEdgeScenarios,
  listEdgeEvents,
  getEdgeEvent,
  triggerEdgeEvent,
  pollEdgeStaging,
  getStagingStatus,
} from './edgeApi';
