from __future__ import annotations

from .capture import Capture as Session
from .chat import build_context
from .llm_bridge import chat


REPORT_SYSTEM = (
    "You are a senior security consultant authoring a formal incident report. Output Markdown "
    "only, with these sections: Executive Summary, Severity Assessment, Key Findings (per "
    "agent), Attack Vector Analysis, Timeline, Prioritized Recommendations, Technical "
    "Appendix, Glossary. Be specific and reference IPs/ports/protocols from the data. "
    "Strict rule: an IP is in a threat feed / blocklist ONLY if it appears in `ip_reputations` "
    "in the metadata; a CVE is applicable ONLY if it appears in `cve_candidates`. Never "
    "invent reputation, malware-family, or CVE claims from prior knowledge. If a section "
    "would be empty under these rules, state that explicitly rather than fabricating."
)


def generate_report(session: Session) -> str:
    context = build_context(session)
    user = (
        "Produce the full security report for this PCAP using the metadata and agent findings "
        "below. Markdown only.\n\n" + context
    )
    return chat(
        system=REPORT_SYSTEM,
        messages=[{"role": "user", "content": user}],
        max_tokens=4000,
        temperature=0.3,
        role="writer",
    )
