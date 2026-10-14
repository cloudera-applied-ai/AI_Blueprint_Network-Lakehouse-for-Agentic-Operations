// Agent Studio Types for LangChain-based workflow execution

export interface AgentNode {
  id: string;
  name: string;
  role: string;
  goal: string;
  backstory: string;
  tools: string[];
  allowDelegation: boolean;
  type: 'manager' | 'worker';
  status: 'idle' | 'thinking' | 'executing' | 'completed' | 'error';
  imagePath?: string;
}

export interface ToolNode {
  id: string;
  name: string;
  description: string;
  parameters: ToolParameter[];
  agentId: string; // Parent agent
  status: 'idle' | 'executing' | 'completed' | 'error';
  imagePath?: string;
}

export interface ToolParameter {
  name: string;
  type: 'string' | 'number' | 'boolean' | 'array' | 'object';
  description: string;
  required: boolean;
  default?: unknown;
}

export interface WorkflowTemplate {
  id: string;
  name: string;
  description: string;
  agents: AgentNode[];
  tools: ToolNode[];
  managerAgentId: string;
  isConversational: boolean;
  process: 'sequential' | 'hierarchical';
}

export interface ThoughtMessage {
  id: string;
  timestamp: Date;
  agentId: string;
  agentName: string;
  type: 'thought' | 'action' | 'observation' | 'final_answer' | 'error' | 'tool_call' | 'tool_result';
  content: string;
  toolName?: string;
  toolInput?: Record<string, unknown>;
  toolOutput?: string;
}

export interface ExecutionStep {
  id: string;
  stepNumber: number;
  timestamp: Date;
  agentId: string;
  agentName: string;
  action: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
  duration?: number;
  thoughts: ThoughtMessage[];
}

export interface WorkflowExecution {
  id: string;
  workflowId: string;
  startTime: Date;
  endTime?: Date;
  status: 'idle' | 'running' | 'completed' | 'failed';
  userInput: string;
  steps: ExecutionStep[];
  finalOutput?: string;
  error?: string;
}

export interface ChatMessage {
  id: string;
  timestamp: Date;
  role: 'user' | 'assistant' | 'system';
  content: string;
  thoughts?: ThoughtMessage[];
  executionId?: string;
}

export interface LogEntry {
  id: string;
  timestamp: Date;
  level: 'debug' | 'info' | 'warn' | 'error';
  source: string;
  message: string;
  metadata?: Record<string, unknown>;
}

export interface ArtifactFile {
  id: string;
  name: string;
  type: 'json' | 'csv' | 'chart' | 'text' | 'image';
  size: number;
  createdAt: Date;
  path: string;
  preview?: string;
}

export interface MonitoringMetrics {
  tokensUsed: number;
  executionTime: number;
  agentCalls: number;
  toolCalls: number;
  errors: number;
  successRate: number;
}

// Pre-built workflow templates for telco operations
export const TELCO_WORKFLOW_TEMPLATES: Partial<WorkflowTemplate>[] = [
  {
    id: 'network-operations',
    name: 'Telco Network Operations Workflow',
    description: 'Multi-agent workflow for network KPI analysis, failure prediction, and visualization',
    process: 'hierarchical',
    isConversational: true,
  },
  {
    id: 'incident-response',
    name: 'Incident Response Workflow',
    description: 'Automated incident triage, root cause analysis, and remediation planning',
    process: 'hierarchical',
    isConversational: true,
  },
  {
    id: 'performance-analysis',
    name: 'Performance Analysis Workflow',
    description: 'Deep dive into network performance with weather correlation and geographic analysis',
    process: 'sequential',
    isConversational: true,
  },
];
