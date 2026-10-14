"""Bundled IOC feed.

A small, curated set of indicators the operator's environment "knows" about —
the same role a real deployment's internal threat feed / SDX-Ranger blocklist
plays. It exists so threat-intel enrichment returns meaningful results even
when the external services (ThreatFox now requires an Auth-Key; AbuseIPDB needs
a key) are unavailable or unconfigured.

The indicators here match the actors the edge synthesizer plants in its
scenarios, so an edge/attack capture always lights up the Threat Intel tab.
Every entry is sourced as "Bundled IOC feed" so it is never mistaken for a live
third-party reputation hit. Live ThreatFox / AbuseIPDB results are merged on
top of these when keys are configured.
"""
from __future__ import annotations

from .schemas import IpReputation

# ip -> reputation attributes
_BUNDLED_IPS: dict[str, dict] = {
    # C2 server used by the c2_beacon scenario.
    "45.133.1.77": {
        "categories": ["c2", "botnet_cc", "malware"],
        "malware": "Cobalt Strike",
        "sources": ["Bundled IOC feed", "abuse.ch (cached)"],
        "abuse_score": 95,
        "notes": "Known Cobalt Strike C2 controller (bundled demo IOC feed).",
    },
    # Bulletproof / Tor-exit host used by the data_exfiltration scenario.
    "185.220.101.42": {
        "categories": ["tor_exit", "anonymizer", "data_exfiltration"],
        "malware": "",
        "sources": ["Bundled IOC feed", "Tor exit-node list"],
        "abuse_score": 82,
        "notes": "Tor exit node observed receiving bulk outbound transfers "
                 "(bundled demo IOC feed).",
    },
}

# domain (TLS SNI / DNS qname / HTTP Host) -> (associated_ip, malware/family)
_BUNDLED_DOMAINS: dict[str, tuple[str, str]] = {
    "cdn-update-cache.example": ("45.133.1.77", "Cobalt Strike"),
    "backup.sync-vault.example": ("185.220.101.42", ""),
}


def local_ip_reputation(ip: str) -> IpReputation | None:
    """Return a bundled-feed reputation for `ip`, or None if not an IOC."""
    entry = _BUNDLED_IPS.get(ip)
    if not entry:
        return None
    return IpReputation(
        ip=ip,
        in_blocklist=True,
        sources=list(entry["sources"]),
        categories=list(entry["categories"]),
        abuse_score=int(entry["abuse_score"]),
        last_reported="",
        notes=entry["notes"],
    )


def local_reputations(ips) -> dict[str, IpReputation]:
    """Bundled-feed reputations for whichever of `ips` are known IOCs."""
    out: dict[str, IpReputation] = {}
    for ip in ips:
        rep = local_ip_reputation(ip)
        if rep is not None:
            out[ip] = rep
    return out


def malware_keywords_for(ips, domains) -> list[str]:
    """Malware/family names for the flagged IOCs present in a capture.

    These become real NVD keyword searches, so the CVE candidates shown are
    genuine NVD results for the detected family (e.g. Cobalt Strike), not
    fabricated — the bundled feed only decides *which* real search to run.
    """
    keywords: list[str] = []
    for ip in ips:
        fam = (_BUNDLED_IPS.get(ip) or {}).get("malware")
        if fam and fam not in keywords:
            keywords.append(fam)
    for d in domains:
        entry = _BUNDLED_DOMAINS.get(d)
        if entry and entry[1] and entry[1] not in keywords:
            keywords.append(entry[1])
    return keywords


def known_domains() -> set[str]:
    return set(_BUNDLED_DOMAINS)
