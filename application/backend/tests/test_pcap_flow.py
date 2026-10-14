"""Packet-analysis HTTP surface + agents (LLM mocked)."""
from pathlib import Path

from tests.conftest import CANNED_LLM_JSON

_FIXTURE = Path(__file__).resolve().parent.parent / "app" / "pcap" / "fixtures" / "port_scan.pcap"


def test_scenarios_and_staging_public_shape(pcap_client):
    assert pcap_client.get("/api/v1/edge/scenarios").status_code == 200
    ids = {s["id"] for s in pcap_client.get("/api/v1/edge/scenarios").json()}
    assert {"port_scan", "c2_beacon", "data_exfiltration", "ddos"} <= ids
    assert pcap_client.get("/api/v1/edge/staging/status").json()["backend"] == "local"


def test_pcap_requires_api_key(anon_pcap_client):
    assert anon_pcap_client.get("/api/v1/pcap/captures").status_code == 401


def test_analyze_upload_and_fetch(pcap_client, monkeypatch):
    monkeypatch.setattr("app.pcap.agents.base.chat", lambda **kw: CANNED_LLM_JSON)
    with open(_FIXTURE, "rb") as fh:
        resp = pcap_client.post(
            "/api/v1/pcap/analyze",
            files={"file": ("port_scan.pcap", fh, "application/octet-stream")},
        )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body["agents"]) == 4
    assert body["metadata"]["total_packets"] > 0
    capture_id = body["capture_id"]

    listing = pcap_client.get("/api/v1/pcap/captures").json()
    assert any(c["id"] == capture_id for c in listing)

    detail = pcap_client.get(f"/api/v1/pcap/captures/{capture_id}")
    assert detail.status_code == 200
    assert "edge_context" not in detail.json()


def test_edge_event_via_api(pcap_client, monkeypatch):
    monkeypatch.setattr("app.pcap.agents.base.chat", lambda **kw: CANNED_LLM_JSON)
    resp = pcap_client.post(
        "/api/v1/edge/events",
        json={"headend_id": "HE-TEST-01", "scenario_id": "port_scan", "pcap_source": "bundled"},
    )
    assert resp.status_code == 202
    execution_id = resp.json()["execution_id"]

    # Wait for the daemon-thread scripted run (EDGE_SIM_SPEED=0) to stage.
    import time
    detail = {}
    for _ in range(100):
        detail = pcap_client.get(f"/api/v1/edge/events/{execution_id}").json()
        if detail["status"] in ("staged", "completed", "failed"):
            break
        time.sleep(0.05)
    assert detail["status"] == "staged", detail.get("error")
    assert detail["thoughts"]

    poll = pcap_client.post("/api/v1/edge/poll")
    assert poll.status_code == 200
    detail = pcap_client.get(f"/api/v1/edge/events/{execution_id}").json()
    assert detail["status"] == "completed"
    assert detail["analysis_id"]

    capture = pcap_client.get(f"/api/v1/pcap/captures/{detail['analysis_id']}").json()
    assert capture["edge_context"]["scenario_id"] == "port_scan"
    assert capture["edge_context"]["headend_id"] == "HE-TEST-01"


def test_bad_headend_404(pcap_client):
    resp = pcap_client.post(
        "/api/v1/edge/events", json={"headend_id": "NOPE", "scenario_id": "port_scan"}
    )
    assert resp.status_code == 404
