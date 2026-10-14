// Packet-capture analysis types (mirror of app/pcap/schemas.py)

export type PcapSeverity = 'low' | 'medium' | 'high' | 'critical';

export interface ConnectionInfo {
  source_ip: string;
  dest_ip: string;
  protocol: string;
  packet_count: number;
  bytes_transferred: number;
  source_ports: number[];
  dest_ports: number[];
}

export interface PayloadFinding {
  source_ip: string;
  dest_ip: string;
  pattern_type: string;
  snippet: string;
  size: number;
}

export interface HttpRequestInfo {
  method: string;
  path: string;
  host: string;
  user_agent: string;
}

export interface GeoLocation {
  ip: string;
  country: string;
  country_code: string;
  region: string;
  city: string;
  lat: number;
  lon: number;
  isp: string;
  org: string;
  asn: string;
}

export interface IpReputation {
  ip: string;
  in_blocklist: boolean;
  sources: string[];
  categories: string[];
  abuse_score: number;
  last_reported: string;
  notes: string;
}

export interface CveCandidate {
  id: string;
  summary: string;
  severity: string;
  score: number;
  matched_keyword: string;
  url: string;
}

export interface FlowInfo {
  source_ip: string;
  dest_ip: string;
  protocol: string;
  source_port: number;
  dest_port: number;
  service: string;
  packets_out: number;
  packets_in: number;
  bytes_out: number;
  bytes_in: number;
  duration_s: number;
  tcp_flags: string[];
  state: string;
  sni: string;
  ja3: string;
}

export interface DnsQueryInfo {
  source_ip: string;
  dest_ip: string;
  qname: string;
  qtype: string;
  response_ips: string[];
  nxdomain: boolean;
}

export interface TlsHandshakeInfo {
  source_ip: string;
  dest_ip: string;
  sni: string;
  version: string;
  ja3: string;
  ja3_hash: string;
  alpn: string[];
  client: string;
}

export interface PcapMetadata {
  total_packets: number;
  time_range_start: string;
  time_range_end: string;
  protocols: Record<string, number>;
  top_connections: ConnectionInfo[];
  payload_findings: PayloadFinding[];
  http_requests: HttpRequestInfo[];
  unique_src_ips: number;
  unique_dst_ips: number;
  flows: FlowInfo[];
  dns_queries: DnsQueryInfo[];
  tls_handshakes: TlsHandshakeInfo[];
  l2_summary: Record<string, number>;
  geo_locations: Record<string, GeoLocation>;
  ip_reputations: Record<string, IpReputation>;
  cve_candidates: CveCandidate[];
}

export interface PcapFinding {
  type: string;
  description: string;
  evidence: string[];
  risk: string;
}

export interface PcapAgentResponse {
  agent_name: string;
  severity: PcapSeverity;
  analysis: string;
  findings: PcapFinding[];
  recommendations: string[];
}

export interface PcapChatMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
}

export interface CaptureResponse {
  capture_id: string;
  source: 'upload' | 'edge';
  filename: string;
  headend_id: string | null;
  edge_execution_id: string | null;
  metadata: PcapMetadata;
  agents: PcapAgentResponse[];
  edge_context?: import('./edge').EdgeContext | null;
}

export interface CaptureSummary {
  id: string;
  created_at: string;
  source: 'upload' | 'edge';
  filename: string;
  headend_id: string | null;
  total_packets: number;
  highest_severity: PcapSeverity;
  edge_execution_id: string | null;
}
