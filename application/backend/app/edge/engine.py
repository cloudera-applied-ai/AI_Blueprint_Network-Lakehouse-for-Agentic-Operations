"""Scripted edge-event runner.

Runs a scenario's detection narrative as a thought-stream on a daemon thread
(the agentic_capacity_planner pattern), committing each thought to the
EdgeAnomalyExecutionModel row so any uvicorn worker serves the poll endpoint.
After the script it produces a pcap (bundled fixture or synthesized) and stages
it, leaving the execution in `staged` for the primary-DC poller to ingest.
"""
from __future__ import annotations

import hashlib
import logging
import os
import shutil
import tempfile
import threading
import time
import uuid
from datetime import datetime, timezone

from ..database import SessionLocal
from ..models import EdgeAnomalyExecutionModel
from . import scenarios, staging, synthesizer

log = logging.getLogger(__name__)

# Multiplier for scripted step delays. 0 in tests for instant completion.
_SIM_SPEED = float(os.environ.get("EDGE_SIM_SPEED", "1"))


def create_execution(headend_id: str, headend_name: str, scenario_id: str, pcap_source: str | None) -> str:
    scenario = scenarios.SCENARIOS.get(scenario_id)
    if scenario is None:
        raise ValueError(f"Unknown scenario: {scenario_id}")
    source = pcap_source or scenario.pcap_source_default
    if source not in ("bundled", "synthesized"):
        raise ValueError("pcap_source must be 'bundled' or 'synthesized'")

    execution_id = f"edge-{uuid.uuid4().hex[:12]}"
    with SessionLocal() as db:
        db.add(
            EdgeAnomalyExecutionModel(
                execution_id=execution_id,
                headend_id=headend_id,
                headend_name=headend_name,
                scenario_id=scenario_id,
                status="running",
                progress_percent=0.0,
                pcap_source=source,
                staging_backend=staging.backend_name(),
                thoughts=[],
                edge_actions=[],
                started_at=datetime.now(timezone.utc),
            )
        )
        db.commit()
    return execution_id


def start(headend_id: str, headend_name: str, scenario_id: str, pcap_source: str | None) -> str:
    """Create an execution row and run it on a background daemon thread."""
    execution_id = create_execution(headend_id, headend_name, scenario_id, pcap_source)
    thread = threading.Thread(target=_run, args=(execution_id,), daemon=True)
    thread.start()
    return execution_id


def _append_thought(execution_id: str, step: scenarios.ScriptedStep, agent_name: str, progress: float) -> None:
    thought = {
        "id": uuid.uuid4().hex,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "agent_id": "edge-local-model",
        "agent_name": agent_name,
        "type": step.type,
        "content": step.content,
        "tool_name": step.tool_name,
        "tool_input": step.tool_input,
        "tool_output": step.tool_output,
    }
    with SessionLocal() as db:
        row = db.query(EdgeAnomalyExecutionModel).filter_by(execution_id=execution_id).first()
        if row is None:
            return
        row.thoughts = list(row.thoughts or []) + [thought]  # reassign so SQLAlchemy tracks it
        row.progress_percent = progress
        db.commit()


def _set(execution_id: str, **fields) -> None:
    with SessionLocal() as db:
        row = db.query(EdgeAnomalyExecutionModel).filter_by(execution_id=execution_id).first()
        if row is None:
            return
        for k, v in fields.items():
            setattr(row, k, v)
        db.commit()


def _run(execution_id: str) -> None:
    with SessionLocal() as db:
        row = db.query(EdgeAnomalyExecutionModel).filter_by(execution_id=execution_id).first()
        if row is None:
            log.warning("edge _run: %s not found", execution_id)
            return
        scenario_id = row.scenario_id
        pcap_source = row.pcap_source
        agent_name = f"{row.headend_name or 'Headend'} · local model"

    scenario = scenarios.SCENARIOS[scenario_id]
    total = len(scenario.script)

    try:
        for i, step in enumerate(scenario.script, start=1):
            if _SIM_SPEED > 0 and step.delay_s:
                time.sleep(step.delay_s * _SIM_SPEED)
            _append_thought(execution_id, step, agent_name, round(100 * i / total, 1))

        stamped = [{**a, "at": datetime.now(timezone.utc).isoformat()} for a in scenario.edge_actions]
        _set(execution_id, status="edge_complete", edge_actions=stamped)

        pcap_path = _obtain_pcap(scenario, pcap_source, execution_id)
        staged = staging.stage_pcap(pcap_path, execution_id)
        try:
            os.unlink(pcap_path)
        except OSError:
            pass

        _set(
            execution_id,
            status="staged",
            staging_backend=staged.backend,
            staged_uri=staged.uri,
            staged_key=staged.key,
        )
        log.info("Edge execution %s staged to %s (%s)", execution_id, staged.uri, staged.backend)
    except Exception as exc:  # noqa: BLE001
        log.exception("Edge execution %s failed", execution_id)
        _set(execution_id, status="failed", error=str(exc))


def _obtain_pcap(scenario: scenarios.EdgeScenario, pcap_source: str, execution_id: str) -> str:
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pcap")
    tmp.close()
    if pcap_source == "bundled" and scenario.bundled_pcap.exists():
        shutil.copyfile(scenario.bundled_pcap, tmp.name)
        return tmp.name
    seed = int(hashlib.sha256(execution_id.encode()).hexdigest(), 16) % (2**32)
    synthesizer.generate(scenario.id, tmp.name, seed=seed)
    return tmp.name
