"""Edge engine (scripted run) + poller ingest, EDGE_SIM_SPEED=0."""
import pytest

from app.edge import engine, poller, scenarios
from app.database import SessionLocal
from app.models import EdgeAnomalyExecutionModel, PcapAnalysisModel
from tests.conftest import CANNED_LLM_JSON


def _run_scenario(scenario_id: str, pcap_source: str) -> str:
    execution_id = engine.create_execution("HE-TEST-01", "Denver Headend", scenario_id, pcap_source)
    # Run synchronously in-thread (EDGE_SIM_SPEED=0) to avoid cross-thread sqlite.
    engine._run(execution_id)
    return execution_id


def test_engine_run_stages_pcap(pcap_db):
    execution_id = _run_scenario("c2_beacon", "synthesized")
    with SessionLocal() as db:
        row = db.query(EdgeAnomalyExecutionModel).filter_by(execution_id=execution_id).first()
        assert row.status == "staged"
        assert len(row.thoughts) == len(scenarios.SCENARIOS["c2_beacon"].script)
        assert row.thoughts[-1]["type"] == "final_answer"
        assert row.edge_actions
        assert row.staged_uri


async def test_full_flow_through_poller(pcap_db, monkeypatch):
    monkeypatch.setattr("app.pcap.agents.base.chat", lambda **kw: CANNED_LLM_JSON)
    execution_id = _run_scenario("port_scan", "bundled")

    processed = await poller.poll_once()
    assert processed == 1

    with SessionLocal() as db:
        row = db.query(EdgeAnomalyExecutionModel).filter_by(execution_id=execution_id).first()
        assert row.status == "completed"
        assert row.analysis_id is not None
        analysis = db.get(PcapAnalysisModel, row.analysis_id)
        assert analysis is not None
        assert analysis.source == "edge"
        assert analysis.headend_id == "HE-TEST-01"


async def test_poller_idempotent(pcap_db, monkeypatch):
    monkeypatch.setattr("app.pcap.agents.base.chat", lambda **kw: CANNED_LLM_JSON)
    _run_scenario("ddos", "bundled")
    assert await poller.poll_once() == 1
    assert await poller.poll_once() == 0


def test_unknown_scenario_rejected(pcap_db):
    with pytest.raises(ValueError):
        engine.create_execution("HE-TEST-01", "Denver Headend", "not_a_scenario", None)
