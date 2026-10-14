/**
 * LLM and AI Agent Types
 */

export interface LLMConfig {
  enabled: boolean;
  provider: LLMProvider;
  endpoint: string;
  model: string;
  /** Optional generalist model for prose/reports/chat (analyst uses `model`). */
  writerModel?: string;
  /** Optional separate endpoint/provider/key for the writer model. Blank => same as analyst. */
  writerProvider?: LLMProvider | '';
  writerEndpoint?: string;
  writerApiKey?: string;
  apiKey?: string;
  jwtTokenPath?: string;
  temperature?: number;
  maxTokens?: number;
}

export enum LLMProvider {
  OPENAI = 'openai',
  ANTHROPIC = 'anthropic',
  OLLAMA = 'ollama',
  CLOUDERA = 'cloudera',
  CUSTOM = 'custom',
}

export interface LLMMessage {
  role: 'system' | 'user' | 'assistant';
  content: string;
}

export interface LLMResponse {
  content: string;
  usage?: {
    promptTokens: number;
    completionTokens: number;
    totalTokens: number;
  };
  model?: string;
}

export interface AIInsight {
  id: string;
  timestamp: Date;
  type: InsightType;
  severity: 'info' | 'warning' | 'critical';
  title: string;
  description: string;
  recommendation: string;
  confidence: number;
  affectedNodes: string[];
  relatedAlerts?: string[];
  metadata?: Record<string, any>;
}

export enum InsightType {
  PATTERN_DETECTED = 'pattern_detected',
  ANOMALY_FORECAST = 'anomaly_forecast',
  ROOT_CAUSE = 'root_cause',
  OPTIMIZATION = 'optimization',
  CAPACITY_WARNING = 'capacity_warning',
  DEGRADATION_TREND = 'degradation_trend',
}

export interface AgentAnalysis {
  summary: string;
  rootCause: string;
  recommendations: string[];
  confidence: number;
  reasoning: string;
}

/**
 * Autonomous AI Action Plan
 */
export interface AIActionPlan {
  id: string;
  timestamp: Date;
  triggeredBy: string; // alert_id or insight_id
  rootCause: string;
  priority: 'critical' | 'high' | 'medium' | 'low';
  steps: AIActionStep[];
  status: 'pending' | 'executing' | 'completed' | 'failed';
  executionStartTime?: Date;
  completionTime?: Date;
  confidence: number;
  reasoning: string;
  affectedNodes: string[];
}

export interface AIActionStep {
  id: string;
  order: number;
  type: 'automated_healing' | 'crew_dispatch' | 'configuration_change' | 'monitoring';
  description: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed' | 'skipped';
  startTime?: Date;
  completionTime?: Date;
  result?: string;
  metadata?: Record<string, any>;
}

/**
 * Crew Dispatch for hardware/physical interventions
 */
export interface CrewDispatch {
  id: string;
  timestamp: Date;
  nodeId: string;
  issueType: 'hardware_failure' | 'antenna_alignment' | 'power_system' | 'connectivity' | 'preventive_maintenance';
  severity: 'critical' | 'high' | 'medium' | 'low';
  description: string;
  location: {
    city: string;
    region: string;
    coordinates: { lat: number; lng: number };
  };
  assignedCrew?: string;
  estimatedArrival?: Date;
  status: 'dispatched' | 'en_route' | 'on_site' | 'completed' | 'cancelled';
  dispatchTime: Date;
  arrivalTime?: Date;
  completionTime?: Date;
  workLog?: string;
  aiInitiated: boolean;
  relatedPlanId?: string;
}

/**
 * Autonomous Action Log
 */
export interface AutonomousAction {
  id: string;
  timestamp: Date;
  actionType: 'healing' | 'crew_dispatch' | 'configuration' | 'analysis';
  description: string;
  triggeredBy: string;
  status: 'initiated' | 'executing' | 'completed' | 'failed';
  confidence: number;
  result?: string;
  metadata?: Record<string, any>;
}
