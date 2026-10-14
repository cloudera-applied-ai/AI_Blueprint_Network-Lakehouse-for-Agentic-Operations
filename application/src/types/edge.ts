// Edge data center anomaly flow types (mirror of app/edge + routes/edge.py)

import type { PcapSeverity } from './packet';

export interface EdgeScenario {
  id: string;
  name: string;
  description: string;
  severity_hint: PcapSeverity;
  pcap_source_default: 'bundled' | 'synthesized';
}

export interface ThoughtMessage {
  id: string;
  timestamp: string;
  agent_id: string;
  agent_name: string;
  type: 'thought' | 'action' | 'observation' | 'tool_call' | 'tool_result' | 'final_answer';
  content: string;
  tool_name?: string | null;
  tool_input?: Record<string, unknown> | null;
  tool_output?: Record<string, unknown> | null;
}

export interface EdgeAction {
  action: string;
  target: string;
  detail: string;
  at?: string;
}

export type EdgeStatus =
  | 'running'
  | 'edge_complete'
  | 'staged'
  | 'analyzing'
  | 'completed'
  | 'failed';

export interface EdgeEvent {
  execution_id: string;
  headend_id: string;
  headend_name: string | null;
  scenario_id: string;
  status: EdgeStatus;
  progress_percent: number;
  pcap_source: 'bundled' | 'synthesized';
  staging_backend: 's3' | 'local';
  staged_uri: string | null;
  thoughts: ThoughtMessage[];
  edge_actions: EdgeAction[];
  analysis_id: string | null;
  error: string | null;
  started_at: string | null;
  completed_at: string | null;
}

export interface EdgeContext {
  execution_id: string;
  headend_id: string;
  headend_name: string | null;
  scenario_id: string;
  pcap_source: string;
  staging_backend: string;
  staged_uri: string | null;
  edge_actions: EdgeAction[];
}

export interface StagingStatus {
  backend: 's3' | 'local';
  configured: boolean;
  bucket: string | null;
  endpoint_url: string | null;
  incoming_count: number;
  local_root: string | null;
}
