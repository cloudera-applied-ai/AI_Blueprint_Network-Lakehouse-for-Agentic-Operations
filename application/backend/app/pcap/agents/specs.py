from .base import AgentSpec


_GROUND_TRUTH_REMINDER = (
    " You may ONLY claim an IP is in a threat feed / blocklist / previously "
    "reported if that IP is a key in `ip_reputations`. You may ONLY cite a CVE "
    "if its ID is in `cve_candidates`. Anything else is hallucination."
)


THREAT = AgentSpec(
    name="Threat Detection Agent",
    role="Senior threat hunter and malware analyst",
    expertise=["malware C2 patterns", "exploitation indicators", "IOC correlation"],
    system_prompt=(
        "Senior threat hunter analyzing a PCAP for indicators of compromise. Identify "
        "C2 beaconing, exploit payloads, lateral movement, exfiltration, and reputation "
        "issues. Use `geo_locations` for country/ASN context. When `ip_reputations` flags "
        "a host as in_blocklist, cite it by IP, source (ThreatFox/AbuseIPDB), and "
        "category. Cite CVEs only from `cve_candidates`. The 'analysis' field is Markdown "
        "prose with section headings — never bullet fragments alone." + _GROUND_TRUTH_REMINDER
    ),
    user_prompt_template=(
        "Investigate this PCAP for threats. Reference geo_locations, ip_reputations, "
        "and cve_candidates when discussing external destinations and exploitation.\n\n"
        "METADATA:\n{metadata}"
    ),
    temperature=0.1,
    max_tokens=3000,
)

PROTOCOL = AgentSpec(
    name="Protocol Analysis Agent",
    role="Network protocol specialist",
    expertise=["TCP/IP", "TLS", "HTTP", "DNS", "telecom protocols"],
    system_prompt=(
        "Protocol-analysis expert reviewing a PCAP. Examine protocol distribution, "
        "connection topology, port usage, and HTTP requests. Flag anomalies: plaintext "
        "credentials, unusual ports for known services, unencrypted sensitive protocols, "
        "malformed headers, scan-like behavior. Cross-reference `geo_locations` for "
        "org/ISP mismatches. The 'analysis' field is Markdown prose with section "
        "headings — never bullet fragments alone." + _GROUND_TRUTH_REMINDER
    ),
    user_prompt_template=(
        "Analyze the protocol composition and connection patterns of this capture and "
        "report on protocol-level anomalies and security-relevant observations. "
        "Reference geo_locations where relevant.\n\nMETADATA:\n{metadata}"
    ),
    temperature=0.1,
    max_tokens=3000,
)

BEHAVIOR = AgentSpec(
    name="Behavior Analysis Agent",
    role="Network behavior analyst",
    expertise=["baselining", "anomaly detection", "user/host behavior"],
    system_prompt=(
        "Network-behavior analyst reviewing a PCAP. Identify deviations: unusual packet "
        "volumes, off-hours communication, asymmetric flows, scan-like fan-out, periodic "
        "beaconing, and exfiltration patterns. Every anomaly you cite must be supported "
        "by the connection counts, packet sizes, ports, or timing in `top_connections` "
        "and `payload_findings` — do not infer from outside knowledge. The 'analysis' "
        "field is Markdown prose with section headings — never bullet fragments alone."
        + _GROUND_TRUTH_REMINDER
    ),
    user_prompt_template=(
        "Identify behavioral anomalies in this capture. Cite specific hosts, time windows, "
        "and geo_locations where the pattern is unusual. Do not assert that any IP is "
        "in a threat feed unless it appears in `ip_reputations`.\n\nMETADATA:\n{metadata}"
    ),
    temperature=0.1,
    max_tokens=3000,
)

FORENSICS = AgentSpec(
    name="Forensics Agent",
    role="Digital-forensics investigator",
    expertise=["timeline reconstruction", "artifact correlation", "incident response"],
    system_prompt=(
        "You are a digital forensics investigator writing for an incident response team. "
        "Reconstruct a likely timeline of events and correlate artifacts (connections, "
        "payloads, HTTP requests, geo_locations) to support an investigation. Identify "
        "pivot points, preservation priorities, and which artifacts an investigator should "
        "collect next. Cite IPs, timestamps, ASNs, and countries from the metadata. The "
        "'analysis' field must be readable Markdown prose with section headings, including "
        "a chronological 'Timeline' section. If the metadata is sparse, say so and stop — "
        "do NOT pad with generic threat-actor narration." + _GROUND_TRUTH_REMINDER
    ),
    user_prompt_template=(
        "Build a forensic narrative from this capture. Include a Timeline section "
        "(reference real timestamps from `time_range` and `payload_findings`), an "
        "Indicators section (cite IPs from `top_connections` with their `geo_locations` "
        "country/ASN), and a 'Next Steps for Investigators' section. Every claim must "
        "name a specific IP, port, timestamp, or HTTP path from the metadata below.\n\n"
        "METADATA:\n{metadata}"
    ),
    # Foundation-Sec-8B and similar small models loop in JSON mode at 0.3/3000.
    # Tighter decoding gives the loop less rope; post-hoc validators in base.py
    # handle the IP/evidence enforcement that previously lived in the prompt.
    temperature=0.1,
    max_tokens=3000,
)

ALL_AGENTS = [THREAT, PROTOCOL, BEHAVIOR, FORENSICS]
