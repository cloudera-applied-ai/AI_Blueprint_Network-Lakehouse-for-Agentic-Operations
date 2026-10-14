"""Edge scenario registry.

Each scenario carries a scripted detection narrative (the headend's local-model
thought-stream), the containment actions the edge takes, and the pcap it
produces (a committed synthetic fixture, or a fresh scapy synthesis).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

# Committed synthetic fixtures live in the pcap package (shipped in the image).
BUNDLED_PCAP_DIR = Path(__file__).resolve().parent.parent / "pcap" / "fixtures"


@dataclass(frozen=True)
class ScriptedStep:
    delay_s: float
    type: str  # thought | action | observation | tool_call | tool_result | final_answer
    content: str
    tool_name: str | None = None
    tool_input: dict | None = None
    tool_output: dict | None = None


@dataclass(frozen=True)
class EdgeScenario:
    id: str
    name: str
    description: str
    severity_hint: str
    pcap_source_default: str  # bundled | synthesized
    script: list[ScriptedStep]
    edge_actions: list[dict] = field(default_factory=list)

    @property
    def bundled_pcap(self) -> Path:
        return BUNDLED_PCAP_DIR / f"{self.id}.pcap"


def _step(delay, type_, content, **kw) -> ScriptedStep:
    return ScriptedStep(delay_s=delay, type=type_, content=content, **kw)


SCENARIOS: dict[str, EdgeScenario] = {
    "port_scan": EdgeScenario(
        id="port_scan",
        name="Internal Port Scan",
        description="A compromised host at the headend sweeps a wide TCP port range against a server.",
        severity_hint="medium",
        pcap_source_default="synthesized",
        script=[
            _step(1.0, "thought", "Ingesting flow telemetry from the headend span port; watching for fan-out patterns."),
            _step(1.6, "observation", "Host 10.20.30.x opened 400+ distinct destination ports on 10.20.30.40 in 8s."),
            _step(1.4, "tool_call", "Scoring the flow against the on-device anomaly model.",
                  tool_name="local_model.infer",
                  tool_input={"feature": "dst_port_fanout", "window_s": 8, "distinct_ports": 412},
                  tool_output={"class": "port_scan", "confidence": 0.91}),
            _step(0.9, "tool_result", "Model verdict: port_scan (confidence 0.91) — above the 0.75 containment threshold."),
            _step(1.2, "action", "Applying an edge ACL to rate-limit the offending source and quarantine the host VLAN."),
            _step(1.3, "tool_call", "Pushing the containment policy to the edge firewall.",
                  tool_name="edge_firewall.apply_acl",
                  tool_input={"src": "10.20.30.x", "action": "rate_limit+quarantine"},
                  tool_output={"acl": "EDGE-ACL-207", "status": "applied"}),
            _step(1.1, "action", "Capturing the suspect flow for forensic analysis at the primary DC."),
            _step(1.4, "tool_call", "Dumping the ring buffer to a pcap.",
                  tool_name="packet_capture.dump", tool_output={"packets": 812, "file": "suspect_port_scan.pcap"}),
            _step(1.2, "tool_call", "Staging the capture to central object storage.",
                  tool_name="staging.upload", tool_output={"status": "queued"}),
            _step(0.8, "final_answer", "Port scan contained at the edge. Suspect capture staged for deep analysis."),
        ],
        edge_actions=[
            {"action": "rate_limit", "target": "10.20.30.0/24", "detail": "EDGE-ACL-207 applied to source host"},
            {"action": "quarantine", "target": "host VLAN 30", "detail": "moved to isolation VLAN pending review"},
            {"action": "capture", "target": "span port", "detail": "812-packet forensic dump"},
        ],
    ),
    "c2_beacon": EdgeScenario(
        id="c2_beacon",
        name="C2 Beacon",
        description="A host at the headend beacons to an external server on a regular interval with jitter.",
        severity_hint="high",
        pcap_source_default="bundled",
        script=[
            _step(1.0, "thought", "Correlating periodic egress flows; C2 beacons hide in regular timing with small jitter."),
            _step(1.6, "observation", "10.20.30.15 → 45.133.1.77:443 every ~60s (jitter σ≈1.4s) with near-constant payload size."),
            _step(1.4, "tool_call", "Scoring the beaconing timeseries on-device.",
                  tool_name="local_model.infer",
                  tool_input={"feature": "beacon_periodicity", "interval_s": 60, "jitter_sigma": 1.4},
                  tool_output={"class": "c2_beacon", "confidence": 0.94}),
            _step(0.9, "tool_result", "Model verdict: c2_beacon (confidence 0.94). Destination reputation: unknown-hosting."),
            _step(1.2, "action", "Blocking the destination IP at the edge and holding the host session open for capture."),
            _step(1.3, "tool_call", "Blackholing the C2 endpoint.",
                  tool_name="edge_firewall.block_ip",
                  tool_input={"ip": "45.133.1.77", "direction": "egress"},
                  tool_output={"acl": "EDGE-ACL-311", "status": "applied"}),
            _step(1.1, "action", "Capturing the beacon session for signature extraction downstream."),
            _step(1.4, "tool_call", "Dumping the beacon flow to a pcap.",
                  tool_name="packet_capture.dump", tool_output={"packets": 1843, "file": "suspect_c2.pcap"}),
            _step(1.2, "tool_call", "Staging the capture to central object storage.",
                  tool_name="staging.upload", tool_output={"status": "queued"}),
            _step(0.8, "final_answer", "C2 channel blocked at the edge. Beacon capture staged for signature analysis."),
        ],
        edge_actions=[
            {"action": "block_ip", "target": "45.133.1.77", "detail": "EDGE-ACL-311 egress blackhole"},
            {"action": "capture", "target": "beacon session", "detail": "1843-packet forensic dump"},
            {"action": "flag_host", "target": "10.20.30.15", "detail": "marked for EDR sweep"},
        ],
    ),
    "data_exfiltration": EdgeScenario(
        id="data_exfiltration",
        name="Data Exfiltration",
        description="A large, high-entropy outbound transfer from the headend suggests bulk data theft.",
        severity_hint="critical",
        pcap_source_default="synthesized",
        script=[
            _step(1.0, "thought", "Monitoring egress byte ratios; exfil shows a sharp outbound/inbound asymmetry."),
            _step(1.6, "observation", "10.20.30.15 → 185.220.101.42: 300MB outbound in 90s, inbound < 1MB, payload entropy > 7.9."),
            _step(1.4, "tool_call", "Scoring the transfer profile on-device.",
                  tool_name="local_model.infer",
                  tool_input={"feature": "egress_asymmetry", "out_mb": 300, "entropy": 7.93},
                  tool_output={"class": "data_exfiltration", "confidence": 0.97}),
            _step(0.9, "tool_result", "Model verdict: data_exfiltration (confidence 0.97) — critical threshold exceeded."),
            _step(1.2, "action", "Severing the transfer and throttling the host uplink immediately."),
            _step(1.3, "tool_call", "Tearing down the offending session.",
                  tool_name="edge_firewall.drop_session",
                  tool_input={"src": "10.20.30.15", "dst": "185.220.101.42"},
                  tool_output={"status": "session_dropped", "acl": "EDGE-ACL-402"}),
            _step(1.1, "action", "Preserving the partial transfer for DLP classification at the primary DC."),
            _step(1.4, "tool_call", "Dumping the exfil flow to a pcap.",
                  tool_name="packet_capture.dump", tool_output={"packets": 2210, "file": "suspect_exfil.pcap"}),
            _step(1.2, "tool_call", "Staging the capture to central object storage.",
                  tool_name="staging.upload", tool_output={"status": "queued"}),
            _step(0.8, "final_answer", "Exfiltration severed at the edge. Partial capture staged for DLP analysis."),
        ],
        edge_actions=[
            {"action": "drop_session", "target": "10.20.30.15 → 185.220.101.42", "detail": "EDGE-ACL-402 session teardown"},
            {"action": "throttle", "target": "10.20.30.15 uplink", "detail": "capped to 1 Mbps pending review"},
            {"action": "capture", "target": "exfil flow", "detail": "2210-packet forensic dump"},
        ],
    ),
    "ddos": EdgeScenario(
        id="ddos",
        name="DDoS Flood",
        description="A high-rate flood from many spoofed sources targets a service at the headend.",
        severity_hint="high",
        pcap_source_default="bundled",
        script=[
            _step(1.0, "thought", "Watching inbound packet-rate and source cardinality; floods spike both at once."),
            _step(1.6, "observation", "10.20.30.15 receiving 50k pps from 250+ distinct sources (mixed UDP/53 + SYN/80)."),
            _step(1.4, "tool_call", "Scoring the inbound flood on-device.",
                  tool_name="local_model.infer",
                  tool_input={"feature": "inbound_rate", "pps": 50000, "distinct_src": 254},
                  tool_output={"class": "volumetric_ddos", "confidence": 0.89}),
            _step(0.9, "tool_result", "Model verdict: volumetric_ddos (confidence 0.89). Engaging local scrubbing."),
            _step(1.2, "action", "Enabling SYN-cookies and rate-limiting UDP/53 at the edge; announcing a scrub route."),
            _step(1.3, "tool_call", "Activating edge DDoS mitigation.",
                  tool_name="edge_firewall.enable_scrubbing",
                  tool_input={"target": "10.20.30.15", "modes": ["syn_cookies", "udp_ratelimit"]},
                  tool_output={"status": "scrubbing_active", "policy": "EDGE-DDOS-118"}),
            _step(1.1, "action", "Sampling the attack traffic for fingerprinting at the primary DC."),
            _step(1.4, "tool_call", "Dumping a flood sample to a pcap.",
                  tool_name="packet_capture.dump", tool_output={"packets": 1000, "file": "suspect_ddos.pcap"}),
            _step(1.2, "tool_call", "Staging the capture to central object storage.",
                  tool_name="staging.upload", tool_output={"status": "queued"}),
            _step(0.8, "final_answer", "Flood mitigated at the edge. Attack sample staged for fingerprinting."),
        ],
        edge_actions=[
            {"action": "enable_scrubbing", "target": "10.20.30.15", "detail": "EDGE-DDOS-118 (SYN cookies + UDP rate-limit)"},
            {"action": "capture", "target": "flood sample", "detail": "1000-packet attack sample"},
        ],
    ),
}


def scenario_list() -> list[dict]:
    return [
        {
            "id": s.id,
            "name": s.name,
            "description": s.description,
            "severity_hint": s.severity_hint,
            "pcap_source_default": s.pcap_source_default,
        }
        for s in SCENARIOS.values()
    ]
