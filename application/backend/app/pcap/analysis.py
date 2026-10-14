"""The analysis pipeline: parse → enrich → agents → persist.

Shared by the manual-upload route and the edge staging poller. Mirrors the
standalone app's orchestration (threat-intel runs concurrently with the agents
with a bounded wait) but persists to PcapAnalysisModel.
"""
from __future__ import annotations

import asyncio
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession

from ..models import PcapAnalysisModel
from . import config as pcap_config
from . import threat_intel
from .agents.orchestrator import run_all_agents
from .capture import Capture
from .parser import parse_pcap
from .schemas import AgentResponse, PcapMetadata

log = logging.getLogger(__name__)


async def analyze_pcap_file(
    path: str,
    filename: str,
    *,
    source: str = "upload",
    headend_id: str | None = None,
    edge_execution_id: str | None = None,
) -> Capture:
    """Analyze a pcap already on disk. Raises ValueError if it can't be parsed."""
    try:
        metadata = await asyncio.to_thread(parse_pcap, path)
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"Failed to parse PCAP: {exc}") from exc

    # Threat-intel enrichment runs concurrently with the LLM agents — both are
    # I/O-bound and independent. If enrichment fails, analysis still ships.
    enrich_task = asyncio.create_task(
        threat_intel.enrich(
            metadata,
            abuseipdb_key=pcap_config.get_abuseipdb_key(),
            nvd_key=pcap_config.get_nvd_key(),
            threatfox_key=pcap_config.get_threatfox_key(),
        )
    )
    try:
        reputations, cves = await asyncio.wait_for(asyncio.shield(enrich_task), timeout=15.0)
    except asyncio.TimeoutError:
        reputations, cves = {}, []
    metadata.ip_reputations = reputations
    metadata.cve_candidates = cves

    agents = await run_all_agents(metadata)

    if not enrich_task.done():
        try:
            reputations, cves = await asyncio.wait_for(enrich_task, timeout=5.0)
            metadata.ip_reputations = reputations
            metadata.cve_candidates = cves
        except asyncio.TimeoutError:
            enrich_task.cancel()

    return Capture(
        id=uuid.uuid4().hex,
        metadata=metadata,
        agents=agents,
        source=source,
        filename=filename,
        headend_id=headend_id,
        edge_execution_id=edge_execution_id,
    )


def persist_capture(db: DBSession, capture: Capture) -> PcapAnalysisModel:
    row = PcapAnalysisModel(
        id=capture.id,
        source=capture.source,
        filename=capture.filename,
        headend_id=capture.headend_id,
        metadata_json=capture.metadata.model_dump(),
        agents_json=[a.model_dump() for a in capture.agents],
        edge_execution_id=capture.edge_execution_id,
    )
    db.add(row)
    db.commit()
    return row


def capture_from_model(row: PcapAnalysisModel) -> Capture:
    return Capture(
        id=row.id,
        metadata=PcapMetadata.model_validate(row.metadata_json),
        agents=[AgentResponse.model_validate(a) for a in (row.agents_json or [])],
        source=row.source,
        filename=row.filename or "",
        headend_id=row.headend_id,
        edge_execution_id=row.edge_execution_id,
    )


def get_capture(db: DBSession, capture_id: str) -> Capture | None:
    row = db.get(PcapAnalysisModel, capture_id)
    return capture_from_model(row) if row else None


def list_captures(db: DBSession, limit: int = 50) -> list[dict]:
    rows = (
        db.execute(
            select(PcapAnalysisModel).order_by(PcapAnalysisModel.created_at.desc()).limit(limit)
        )
        .scalars()
        .all()
    )
    order = ["critical", "high", "medium", "low"]
    out: list[dict] = []
    for row in rows:
        meta = row.metadata_json or {}
        sevs = [a.get("severity") for a in (row.agents_json or [])]
        highest = next((s for s in order if s in sevs), "low")
        out.append(
            {
                "id": row.id,
                "created_at": row.created_at.isoformat() if row.created_at else "",
                "source": row.source,
                "filename": row.filename,
                "headend_id": row.headend_id,
                "total_packets": meta.get("total_packets", 0),
                "highest_severity": highest,
                "edge_execution_id": row.edge_execution_id,
            }
        )
    return out
