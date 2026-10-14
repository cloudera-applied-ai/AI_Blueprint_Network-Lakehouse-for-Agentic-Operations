from typing import Literal
from pydantic import BaseModel


Severity = Literal["low", "medium", "high", "critical"]


class ConnectionInfo(BaseModel):
    source_ip: str
    dest_ip: str
    protocol: str
    packet_count: int
    bytes_transferred: int
    source_ports: list[int] = []
    dest_ports: list[int] = []


class PayloadFinding(BaseModel):
    source_ip: str
    dest_ip: str
    pattern_type: str
    snippet: str
    size: int


class HttpRequestInfo(BaseModel):
    method: str
    path: str
    host: str
    user_agent: str


class GeoLocation(BaseModel):
    ip: str
    country: str = ""
    country_code: str = ""
    region: str = ""
    city: str = ""
    lat: float = 0.0
    lon: float = 0.0
    isp: str = ""
    org: str = ""
    asn: str = ""


class IpReputation(BaseModel):
    ip: str
    in_blocklist: bool
    sources: list[str] = []
    categories: list[str] = []
    abuse_score: int = 0
    last_reported: str = ""
    notes: str = ""


class CveCandidate(BaseModel):
    id: str
    summary: str
    severity: str = ""
    score: float = 0.0
    matched_keyword: str = ""
    url: str = ""


class FlowInfo(BaseModel):
    """A bidirectional transport flow (5-tuple), reconstructed from packets."""
    source_ip: str
    dest_ip: str
    protocol: str
    source_port: int = 0
    dest_port: int = 0
    service: str = ""          # best-effort app protocol: https, dns, http, ntp…
    packets_out: int = 0
    packets_in: int = 0
    bytes_out: int = 0
    bytes_in: int = 0
    duration_s: float = 0.0
    tcp_flags: list[str] = []  # observed control flags, e.g. ["SYN","SYN-ACK","FIN"]
    state: str = ""            # established | reset | rejected | syn_sent | request_only
    sni: str = ""              # from TLS ClientHello, if any
    ja3: str = ""              # JA3 hash of the ClientHello, if any


class DnsQueryInfo(BaseModel):
    source_ip: str
    dest_ip: str
    qname: str
    qtype: str = "A"
    response_ips: list[str] = []
    nxdomain: bool = False


class TlsHandshakeInfo(BaseModel):
    source_ip: str
    dest_ip: str
    sni: str = ""
    version: str = ""
    ja3: str = ""
    ja3_hash: str = ""
    alpn: list[str] = []
    client: str = ""           # inferred stack name (chrome, openssl…) when known


class PcapMetadata(BaseModel):
    total_packets: int
    time_range_start: str
    time_range_end: str
    protocols: dict[str, int]
    top_connections: list[ConnectionInfo]
    payload_findings: list[PayloadFinding]
    http_requests: list[HttpRequestInfo]
    unique_src_ips: int
    unique_dst_ips: int
    flows: list[FlowInfo] = []
    dns_queries: list[DnsQueryInfo] = []
    tls_handshakes: list[TlsHandshakeInfo] = []
    l2_summary: dict[str, int] = {}   # ARP, DHCP, VLAN counts etc.
    geo_locations: dict[str, GeoLocation] = {}
    ip_reputations: dict[str, IpReputation] = {}
    cve_candidates: list[CveCandidate] = []


class Finding(BaseModel):
    type: str
    description: str
    evidence: list[str] = []
    risk: str = ""


class AgentResponse(BaseModel):
    agent_name: str
    severity: Severity
    analysis: str
    findings: list[Finding]
    recommendations: list[str]


class AnalyzeResponse(BaseModel):
    session_id: str
    metadata: PcapMetadata
    agents: list[AgentResponse]


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str


class ChatRequest(BaseModel):
    session_id: str
    messages: list[ChatMessage]


class ChatResponse(BaseModel):
    reply: str


class ReportRequest(BaseModel):
    session_id: str


class ReportResponse(BaseModel):
    report_markdown: str
