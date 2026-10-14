"""Synthesized pcaps re-parse via the real parser with realistic signal.

The captures carry a large benign baseline (DNS, real TLS handshakes with SNI +
JA3, HTTP, NTP/DHCP/SNMP infra) with the scenario's attack mixed in, so these
tests assert both that the baseline looks real and that the attack survives.
"""
import tempfile

import pytest

from app.edge import synthesizer
from app.pcap.parser import parse_pcap


def _gen_and_parse(scenario_id: str, seed: int = 7):
    with tempfile.NamedTemporaryFile(suffix=".pcap") as tmp:
        synthesizer.generate(scenario_id, tmp.name, seed=seed)
        return parse_pcap(tmp.name)


# --- realism shared across every scenario --------------------------------
@pytest.mark.parametrize("sid", ["port_scan", "c2_beacon", "data_exfiltration", "ddos"])
def test_capture_has_realistic_baseline(sid):
    m = _gen_and_parse(sid)
    # A real slice of headend traffic: thousands of packets, many flows,
    # DNS name resolution, and real TLS handshakes with SNI + JA3.
    assert m.total_packets > 1500
    assert len(m.flows) > 30
    assert len(m.dns_queries) > 10
    assert any(q.response_ips for q in m.dns_queries)
    assert len(m.tls_handshakes) > 10
    assert any(t.sni and t.ja3_hash for t in m.tls_handshakes)
    # Several distinct client stacks -> several distinct JA3 fingerprints.
    assert len({t.ja3_hash for t in m.tls_handshakes}) >= 3
    # Proper TCP flows, not just SYN spray: some sessions reach established.
    assert any(f.state in ("established", "closed") for f in m.flows)
    # Layer-2 framing is present (VLAN-tagged Ethernet).
    assert m.l2_summary.get("VLAN-tagged", 0) > 0


def test_port_scan_signal():
    m = _gen_and_parse("port_scan")
    # The scan shows up as many rejected/reset flows to a single target host.
    scan_flows = [f for f in m.flows if f.dest_ip == "10.20.30.40"
                  and f.state in ("rejected", "reset")]
    assert len(scan_flows) >= 20


def test_c2_beacon_signal():
    m = _gen_and_parse("c2_beacon")
    # Suspicious HTTP check-in with a beacon user-agent…
    assert any("beacon" in h.user_agent.lower() for h in m.http_requests)
    # …plus a TLS handshake to the C2 SNI.
    assert any("cdn-update-cache" in t.sni for t in m.tls_handshakes)


def test_data_exfiltration_signal():
    m = _gen_and_parse("data_exfiltration")
    # A strongly asymmetric outbound flow to the exfil host.
    exfil = [f for f in m.flows if f.dest_ip == "185.220.101.42"]
    assert exfil, "no flow to the exfil destination"
    top = max(exfil, key=lambda f: f.bytes_out)
    assert top.bytes_out > 100_000
    assert top.bytes_out > 5 * (top.bytes_in + 1)


def test_ddos_signal():
    m = _gen_and_parse("ddos")
    assert m.total_packets > 1500
    assert m.unique_src_ips > 100  # many spoofed sources


def test_bundled_fixtures_parse():
    from app.edge.scenarios import SCENARIOS
    for sid, scenario in SCENARIOS.items():
        assert scenario.bundled_pcap.exists(), f"missing fixture for {sid}"
        m = parse_pcap(str(scenario.bundled_pcap))
        assert m.total_packets > 0


def test_unknown_scenario_raises():
    with pytest.raises(ValueError):
        synthesizer.generate("nope", "/tmp/x.pcap")
