from __future__ import annotations

import json

from .agents.base import _format_metadata
from .capture import Capture as Session
from .llm_bridge import chat
from .schemas import ChatMessage


CHAT_SYSTEM = (
    "You are a network-security analyst answering questions about a specific PCAP capture. "
    "Use the metadata and agent findings provided as ground truth. Be concise and cite specific "
    "IPs, ports, protocols, and findings. If asked something outside the data, say so. "
    "Strict rule: an IP is in a threat feed / blocklist ONLY if it appears in `ip_reputations` "
    "in the metadata. A CVE applies ONLY if it appears in `cve_candidates`. Never invent "
    "reputation, malware-family, or CVE claims from prior knowledge — if the metadata "
    "doesn't support it, say the data doesn't show it."
)


def build_context(session: Session) -> str:
    agents_summary = [
        {
            "agent": a.agent_name,
            "severity": a.severity,
            "analysis": a.analysis,
            "findings": [f.model_dump() for f in a.findings],
            "recommendations": a.recommendations,
        }
        for a in session.agents
    ]
    return (
        "PCAP_METADATA:\n"
        + _format_metadata(session.metadata)
        + "\n\nAGENT_FINDINGS:\n"
        + json.dumps(agents_summary, indent=2)
    )


def reply(session: Session, messages: list[ChatMessage]) -> str:
    context = build_context(session)
    convo = [m for m in messages if m.role != "system"]
    if not convo:
        return "Ask a question about the capture."

    first_user_content = (
        f"Context for this conversation (do not echo back, use as ground truth):\n\n{context}\n\n"
        f"--- user question ---\n{convo[0].content}"
    )
    full: list[dict[str, str]] = [{"role": "user", "content": first_user_content}]
    for m in convo[1:]:
        full.append({"role": m.role, "content": m.content})
    return chat(system=CHAT_SYSTEM, messages=full, max_tokens=1500, temperature=0.4, role="writer", priority=1)
