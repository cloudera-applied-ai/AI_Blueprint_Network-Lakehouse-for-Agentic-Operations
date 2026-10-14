"""Packet-capture network-security analysis (ported from amp-telco-packetanalysis).

Integrates into the NOC app: scapy parsing + geoip/threat-intel enrichment +
four network-security agents, driven by this repo's LLM queue and persisted in
PostgreSQL. Used by both the manual-upload flow and the edge anomaly poller.
"""
