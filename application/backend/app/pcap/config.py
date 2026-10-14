"""Optional configuration for the pcap module (threat-intel keys, edge sim)."""
from __future__ import annotations

import os


def get_abuseipdb_key() -> str:
    """AbuseIPDB key (optional). ThreatFox + NVD work key-less at low rate."""
    return os.environ.get("ABUSEIPDB_API_KEY", "")


def get_nvd_key() -> str:
    return os.environ.get("NVD_API_KEY", "")


def get_threatfox_key() -> str:
    """ThreatFox Auth-Key (abuse.ch made it mandatory in 2024).

    Without it, live ThreatFox lookups are skipped; the bundled IOC feed still
    flags known-bad indicators.
    """
    return os.environ.get("THREATFOX_API_KEY", "")
