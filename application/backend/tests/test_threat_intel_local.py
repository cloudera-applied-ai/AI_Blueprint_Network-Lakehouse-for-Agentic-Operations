"""The bundled IOC feed flags the demo's known-bad indicators without any
external API keys, so the Threat Intel tab is never empty for attack captures."""
import asyncio
import tempfile

from app.edge import synthesizer
from app.pcap import threat_intel, threat_intel_local
from app.pcap.parser import parse_pcap


def _parse(sid: str):
    with tempfile.NamedTemporaryFile(suffix=".pcap") as t:
        synthesizer.generate(sid, t.name, seed=7)
        return parse_pcap(t.name)


def test_c2_ip_is_blocklisted_by_local_feed():
    m = _parse("c2_beacon")
    reps = asyncio.run(threat_intel.lookup_ip_reputations(threat_intel._candidate_external_ips(m)))
    assert "45.133.1.77" in reps
    r = reps["45.133.1.77"]
    assert r.in_blocklist
    assert "Bundled IOC feed" in r.sources
    assert r.abuse_score > 0
    assert r.categories


def test_exfil_ip_is_blocklisted_by_local_feed():
    m = _parse("data_exfiltration")
    reps = asyncio.run(threat_intel.lookup_ip_reputations(threat_intel._candidate_external_ips(m)))
    assert "185.220.101.42" in reps
    assert reps["185.220.101.42"].in_blocklist


def test_benign_only_capture_has_no_blocklist_hits():
    # A capture with no planted external IOC (internal port scan) stays clean.
    m = _parse("port_scan")
    reps = asyncio.run(threat_intel.lookup_ip_reputations(threat_intel._candidate_external_ips(m)))
    assert all(ip not in reps for ip in ("45.133.1.77", "185.220.101.42"))


def test_malware_family_becomes_cve_keyword():
    m = _parse("c2_beacon")
    kws = threat_intel._extract_keywords(m)
    assert "Cobalt Strike" in kws


def test_threatfox_skipped_without_key_but_local_still_flags():
    # No key, no network dependence: local feed alone flags the IOC.
    reps = asyncio.run(threat_intel.lookup_ip_reputations(["45.133.1.77", "8.8.8.8"]))
    assert "45.133.1.77" in reps and "8.8.8.8" not in reps


def test_local_feed_helpers():
    assert threat_intel_local.local_ip_reputation("8.8.8.8") is None
    assert threat_intel_local.malware_keywords_for(["45.133.1.77"], set()) == ["Cobalt Strike"]
