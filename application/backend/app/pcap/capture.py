"""Lightweight in-memory holder for a parsed capture + agent results.

Replaces the standalone app's `Session` object. The report/chat/docx modules
consume `.metadata` (PcapMetadata) and `.agents` (list[AgentResponse]); the
persistence layer (routes/pcap.py + edge poller) maps this to/from
`PcapAnalysisModel` rows.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .schemas import AgentResponse, PcapMetadata


@dataclass
class Capture:
    id: str
    metadata: PcapMetadata
    agents: list[AgentResponse]
    source: str = "upload"  # "upload" | "edge"
    filename: str = ""
    headend_id: str | None = None
    edge_execution_id: str | None = None
    # Backward-compat alias for ported code that referenced `.session_id`.
    extra: dict = field(default_factory=dict)

    @property
    def session_id(self) -> str:
        return self.id
