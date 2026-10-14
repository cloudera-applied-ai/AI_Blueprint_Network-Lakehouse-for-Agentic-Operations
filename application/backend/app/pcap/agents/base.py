from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any

from ..llm_bridge import chat, writer_enabled
from ..schemas import AgentResponse, Finding, PcapMetadata, Severity

log = logging.getLogger(__name__)


@dataclass
class AgentSpec:
    name: str
    role: str
    expertise: list[str]
    system_prompt: str
    user_prompt_template: str
    # Per-agent decoding overrides. Tighter values help small models (e.g.
    # Foundation-Sec-8B) on long, rule-heavy prompts where the default
    # temperature/max_tokens lets them loop or wander.
    temperature: float = 0.3
    max_tokens: int = 3000


# Keep this prompt SHORT. Models follow short JSON specs more reliably than
# long ones with examples. The renderer is tolerant of variations.
JSON_SCHEMA_HINT = """\
Respond ONLY with a single JSON object matching this schema:

{
  "severity": "low|medium|high|critical",
  "analysis": "Markdown-formatted prose, 3-5 paragraphs with ## headings. Cite specific IPs, ports, protocols, CVEs, and ASNs from the metadata.",
  "findings": [{"type": "...", "description": "...", "evidence": ["..."], "risk": "..."}],
  "recommendations": ["..."]
}

`analysis` MUST be a string. Use `\\n` for line breaks inside the string.
Do not wrap the response in ``` or any other prose.

GROUND-TRUTH RULES — strictly enforced, no exceptions:
  * Threat-feed / blocklist claims: an IP is in a threat feed ONLY if it appears
    in the `ip_reputations` object of the metadata. NEVER claim an IP is "known
    malicious", "in a threat feed", "on a blocklist", or "previously reported"
    unless that IP is a key in `ip_reputations`. If `ip_reputations` is empty,
    state that no IPs in this capture matched the configured blocklists.
  * CVE claims: cite a CVE ID ONLY if it appears in `cve_candidates`. Do not
    invent CVE numbers from prior knowledge.
  * GeoIP claims: country / ASN / ISP info comes ONLY from `geo_locations`.
  * Behavior claims (beaconing, exfiltration, scanning, etc.) must be supported
    by the connection counts, packet sizes, ports, or timing in `top_connections`
    and `payload_findings`. Reference the specific evidence.
  * Do not infer reputation, ownership, or affiliation that isn't in the
    metadata. Phrases like "this IP is associated with…" are forbidden unless
    the association is in `ip_reputations` or `geo_locations`.
"""

# Used in two-model mode: the analyst only produces structured findings;
# the writer model handles prose. This keeps Foundation-Sec-8B (or any small
# domain model) out of the prose-generation business it's bad at.
JSON_SCHEMA_HINT_FINDINGS_ONLY = """\
Respond ONLY with a single JSON object matching this schema:

{
  "severity": "low|medium|high|critical",
  "findings": [{"type": "...", "description": "one sentence", "evidence": ["..."], "risk": "low|medium|high"}],
  "recommendations": ["..."]
}

Do not include an `analysis` field. Do not write prose. Do not wrap the
response in ``` or any other text outside the JSON.

GROUND-TRUTH RULES — strictly enforced:
  * Threat-feed / blocklist claims about an IP only if the IP is a key in
    `ip_reputations`. If `ip_reputations` is empty, do not claim any IP is
    on a threat feed.
  * CVE IDs only from `cve_candidates`.
  * Country / ASN / ISP only from `geo_locations`.
  * Behavior claims (beaconing, exfiltration, scanning) must be supported by
    counts/sizes/ports/timing in `top_connections` and `payload_findings`.
"""


# Caps chosen to keep the whole metadata summary well within a small
# security model's context window (~8k tokens). The richer parser output
# (100+ flows, 150 DNS, 150 TLS) is compacted to terse lines here — the full
# detail still lives in the stored metadata and the UI; the agents only need a
# representative, bounded sample. Flows/DNS/TLS are already sorted so the most
# notable entries come first.
_FLOW_CAP = 18
_DNS_CAP = 18
_TLS_CAP = 12
_HTTP_CAP = 8
_PAYLOAD_CAP = 12
_GEO_CAP = 12
_REP_CAP = 15
_CVE_CAP = 8


def _fmt_bytes(n: int) -> str:
    if n < 1024:
        return f"{n}B"
    if n < 1024 * 1024:
        return f"{n / 1024:.1f}K"
    return f"{n / (1024 * 1024):.1f}M"


def _format_metadata(meta: PcapMetadata) -> str:
    """Compact, bounded text summary of the capture for the LLM agents.

    Deliberately terse (one line per flow/query/handshake) so the prompt stays
    within small-context security models. Not JSON: dense key/value lines cost
    far fewer tokens than pretty-printed dicts while carrying the same signal.
    """
    geo = getattr(meta, "geo_locations", None) or {}
    reps = getattr(meta, "ip_reputations", None) or {}
    cves = getattr(meta, "cve_candidates", None) or []
    flows = getattr(meta, "flows", None) or []
    dns = getattr(meta, "dns_queries", None) or []
    tls_hs = getattr(meta, "tls_handshakes", None) or []
    l2 = getattr(meta, "l2_summary", None) or {}

    lines: list[str] = []
    lines.append(
        f"packets={meta.total_packets} window={meta.time_range_start}..{meta.time_range_end} "
        f"src_ips={meta.unique_src_ips} dst_ips={meta.unique_dst_ips}"
    )
    lines.append("protocols=" + ", ".join(f"{k}:{v}" for k, v in meta.protocols.items()))
    if l2:
        lines.append("l2=" + ", ".join(f"{k}:{v}" for k, v in l2.items()))

    if flows:
        lines.append(f"\nFLOWS (top {min(_FLOW_CAP, len(flows))} of {len(flows)}):")
        for f in flows[:_FLOW_CAP]:
            svc = f.service or f.protocol
            extra = f" sni={f.sni}" if f.sni else ""
            flags = f" flags={'/'.join(f.tcp_flags)}" if f.tcp_flags else ""
            lines.append(
                f"  {f.source_ip}:{f.source_port}->{f.dest_ip}:{f.dest_port} {svc} "
                f"{f.state or '-'} out={_fmt_bytes(f.bytes_out)} in={_fmt_bytes(f.bytes_in)} "
                f"dur={f.duration_s}s{flags}{extra}"
            )

    if tls_hs:
        distinct_ja3 = len({t.ja3_hash for t in tls_hs if t.ja3_hash})
        lines.append(f"\nTLS ({len(tls_hs)} handshakes, {distinct_ja3} distinct JA3):")
        for t in tls_hs[:_TLS_CAP]:
            alpn = f" alpn={','.join(t.alpn)}" if t.alpn else ""
            lines.append(f"  {t.source_ip}->{t.dest_ip} sni={t.sni or '-'} {t.version} ja3={t.ja3_hash[:16]}{alpn}")

    if dns:
        nx = [d for d in dns if d.nxdomain]
        lines.append(f"\nDNS ({len(dns)} queries, {len(nx)} NXDOMAIN):")
        for d in dns[:_DNS_CAP]:
            ans = "->" + ",".join(d.response_ips) if d.response_ips else ("NXDOMAIN" if d.nxdomain else "")
            lines.append(f"  {d.qname} {d.qtype} {ans}")

    if meta.http_requests:
        lines.append(f"\nHTTP ({len(meta.http_requests)}):")
        for h in meta.http_requests[:_HTTP_CAP]:
            lines.append(f"  {h.method} {h.host}{h.path} ua=\"{h.user_agent}\"")

    if meta.payload_findings:
        lines.append(f"\nPAYLOAD FINDINGS ({len(meta.payload_findings)}):")
        for p in meta.payload_findings[:_PAYLOAD_CAP]:
            lines.append(f"  {p.source_ip}->{p.dest_ip} {p.pattern_type} ({p.size}B): {p.snippet[:80]}")

    # Geo: prefer external IPs that appear in the shown flows.
    shown_ips = {f.dest_ip for f in flows[:_FLOW_CAP]} | {f.source_ip for f in flows[:_FLOW_CAP]}
    geo_relevant = {ip: g for ip, g in geo.items() if ip in shown_ips}
    geo_other = {ip: g for ip, g in geo.items() if ip not in shown_ips}
    geo_capped = {**geo_relevant, **dict(list(geo_other.items())[: max(0, _GEO_CAP - len(geo_relevant))])}
    if geo_capped:
        lines.append(f"\nGEOIP ({len(geo_capped)} of {len(geo)}):")
        for ip, g in list(geo_capped.items())[:_GEO_CAP]:
            loc = ", ".join(x for x in (g.city, g.country) if x)
            lines.append(f"  {ip} {loc} {g.isp or g.org} {g.asn}".rstrip())

    blocklisted = {ip: r for ip, r in reps.items() if getattr(r, "in_blocklist", False)}
    if blocklisted:
        lines.append(f"\nBLOCKLISTED IPs ({len(blocklisted)}):")
        for ip, r in list(blocklisted.items())[:_REP_CAP]:
            lines.append(f"  {ip} sources={','.join(r.sources)} cats={','.join(r.categories)} abuse={r.abuse_score}")

    if cves:
        lines.append(f"\nCVE CANDIDATES ({len(cves)}):")
        for c in cves[:_CVE_CAP]:
            lines.append(f"  {c.id} ({c.severity or '-'}) kw={c.matched_keyword}: {c.summary[:100]}")

    return "\n".join(lines)


def _coerce_severity(value: str) -> Severity:
    v = (value or "").strip().lower()
    if v in ("low", "medium", "high", "critical"):
        return v  # type: ignore[return-value]
    return "medium"


_FENCE_RE = re.compile(r"^\s*```(?:json)?\s*\n?|\n?```\s*$", re.IGNORECASE)


def _strip_fences(content: str) -> str:
    s = content.strip()
    s = _FENCE_RE.sub("", s)
    return s.strip()


def _parse_json_response(content: str) -> dict | None:
    s = _strip_fences(content)
    start = s.find("{")
    if start == -1:
        return None
    end = s.rfind("}")
    # Either a complete object (greedy from first { to last }), or a
    # truncated one (model hit max_tokens mid-string). Try the complete form
    # first, then fall through to the repair pass which closes open strings
    # and braces.
    if end > start:
        blob = s[start : end + 1]
        try:
            result = json.loads(blob)
            return result if isinstance(result, dict) else None
        except json.JSONDecodeError:
            pass
    else:
        blob = s[start:]
    repaired = _repair_loose_json(blob)
    if repaired is None:
        return None
    try:
        result = json.loads(repaired)
        return result if isinstance(result, dict) else None
    except json.JSONDecodeError:
        return None


_ANALYSIS_FIELD_RE = re.compile(r'"(?:analysis|summary|narrative)"\s*:\s*"((?:[^"\\]|\\.)*)', re.IGNORECASE)


def _extract_analysis_field(content: str) -> str | None:
    """Last-ditch fallback when JSON parsing fails: pull the `analysis` string
    value out of a malformed blob via regex so the user sees prose instead of
    raw broken JSON.
    """
    m = _ANALYSIS_FIELD_RE.search(content)
    if not m:
        return None
    raw = m.group(1)
    # Decode the JSON escape sequences that matter for prose display.
    raw = (
        raw.replace("\\n", "\n")
        .replace("\\t", "\t")
        .replace('\\"', '"')
        .replace("\\\\", "\\")
    )
    return raw.strip() or None


_CTRL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def _repair_loose_json(blob: str) -> str | None:
    """Best-effort cleanup for JSON the model corrupted or truncated.

    - Strip raw control characters (they should be \\uXXXX-escaped).
    - Replace unicode replacement chars with a placeholder.
    - Close any open string + open `{`/`[` containers when the model hit
      max_tokens mid-output (a very common Foundation-Sec-8B failure mode).
    Returns the repaired blob, or None if nothing was changed.
    """
    cleaned = _CTRL_RE.sub("", blob).replace("�", "?")
    in_str = False
    escape = False
    stack: list[str] = []
    for ch in cleaned:
        if escape:
            escape = False
            continue
        if in_str:
            if ch == "\\":
                escape = True
            elif ch == '"':
                in_str = False
        else:
            if ch == '"':
                in_str = True
            elif ch in "{[":
                stack.append(ch)
            elif ch == "}" and stack and stack[-1] == "{":
                stack.pop()
            elif ch == "]" and stack and stack[-1] == "[":
                stack.pop()
    repaired = cleaned
    if in_str:
        # If we're inside a string when truncation hit, close it. A trailing
        # comma immediately after would be invalid JSON, so trim a dangling
        # comma after closing.
        repaired += '"'
    while stack:
        opener = stack.pop()
        repaired += "}" if opener == "{" else "]"
    repaired = re.sub(r",\s*([}\]])", r"\1", repaired)
    return repaired if repaired != blob else None


def _pick(parsed: dict, *keys: str) -> Any:
    """Return the first present value across snake_case / camelCase / Title Case variants."""
    for key in keys:
        if key in parsed and parsed[key] not in (None, ""):
            return parsed[key]
    return None


def _humanize_key(key: str) -> str:
    return re.sub(r"[_-]+", " ", str(key)).strip().title()


def _render_value(value: Any, depth: int = 0) -> str:
    """Convert any JSON value into reader-friendly Markdown — never raw JSON."""
    if value is None or value == "":
        return "_(none)_"
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, (int, float, str)):
        return str(value)
    if isinstance(value, list):
        return _render_list(value, depth)
    if isinstance(value, dict):
        return _render_dict(value, depth)
    return str(value)


def _render_list(items: list, depth: int) -> str:
    if not items:
        return "_(none)_"
    lines: list[str] = []
    for item in items:
        if isinstance(item, dict):
            # Pull the most "title-like" field for the header.
            title = (
                item.get("type")
                or item.get("title")
                or item.get("name")
                or item.get("id")
                or "Item"
            )
            body_keys = [k for k in item.keys() if k not in {"type", "title", "name", "id"}]
            inner: list[str] = [f"**{title}**"]
            for k in body_keys:
                rendered = _render_value(item[k], depth + 1)
                # Keep one-liners inline; multi-line goes underneath as a sublist.
                if "\n" in rendered:
                    inner.append(f"  - **{_humanize_key(k)}:**\n    {rendered.replace(chr(10), chr(10) + '    ')}")
                else:
                    inner.append(f"  - **{_humanize_key(k)}:** {rendered}")
            lines.append("- " + "\n  ".join(inner))
        elif isinstance(item, list):
            lines.append("- " + ", ".join(_render_value(x, depth + 1) for x in item))
        else:
            lines.append(f"- {_render_value(item, depth + 1)}")
    return "\n".join(lines)


def _render_dict(d: dict, depth: int = 0) -> str:
    """Convert a JSON object into Markdown headings + bullets."""
    if not d:
        return "_(empty)_"
    lines: list[str] = []
    heading_level = "#" * min(6, depth + 3)  # ###, ####, …
    for key, value in d.items():
        title = _humanize_key(key)
        if isinstance(value, dict):
            lines.append(f"{heading_level} {title}\n\n{_render_dict(value, depth + 1)}")
        elif isinstance(value, list):
            lines.append(f"{heading_level} {title}\n\n{_render_list(value, depth + 1)}")
        else:
            lines.append(f"**{title}:** {_render_value(value, depth + 1)}")
    return "\n\n".join(lines).strip() or "_(empty)_"


def _force_markdown(value: Any) -> str:
    """Always returns Markdown-renderable text. Strings pass through; other
    shapes get rendered via the dict/list helpers."""
    if value is None:
        return "_No analysis returned._"
    if isinstance(value, str):
        return value.strip() or "_No analysis returned._"
    if isinstance(value, dict):
        return _render_dict(value)
    if isinstance(value, list):
        return _render_list(value, 0)
    return str(value)


def _stringify_evidence(item: Any) -> str:
    """Turn one evidence entry into a single readable line.

    Models often return evidence as a structured object (e.g.
    {type, payload, size, timestamp}) instead of a plain string. Render
    those as `key: value` pairs and skip binary-looking blobs.
    """
    if item is None:
        return ""
    if isinstance(item, str):
        return _sanitize_text(item)
    if isinstance(item, (int, float, bool)):
        return str(item)
    if isinstance(item, dict):
        parts: list[str] = []
        for k, v in item.items():
            if v is None or v == "":
                continue
            text = _sanitize_text(v) if isinstance(v, str) else str(v)
            if not text:
                continue
            parts.append(f"{_humanize_key(k)}: {text}")
        return " · ".join(parts)
    if isinstance(item, list):
        return ", ".join(_stringify_evidence(x) for x in item if x is not None)
    return _sanitize_text(str(item))


def _sanitize_text(s: str, max_len: int = 240) -> str:
    """Make a string safe and useful for display: strip control bytes and
    summarize anything that's mostly non-printable as `<binary N bytes>`.
    """
    if not s:
        return ""
    cleaned = _CTRL_RE.sub("", s).replace("�", "?")
    printable = sum(1 for c in cleaned if c.isprintable() or c in "\t\n")
    if cleaned and printable / max(1, len(cleaned)) < 0.7:
        return f"<binary {len(s)} bytes>"
    cleaned = cleaned.strip()
    if len(cleaned) > max_len:
        cleaned = cleaned[: max_len - 1].rstrip() + "…"
    return cleaned


_MAX_FINDINGS = 12
_MAX_PER_TYPE = 4
_IPV4_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")


def _coerce_findings(raw: Any) -> list[Finding]:
    if not isinstance(raw, list):
        return []
    out: list[Finding] = []
    seen: set[tuple[str, str]] = set()
    per_type: dict[str, int] = {}
    for f in raw:
        if not isinstance(f, dict):
            continue
        evidence_raw = _pick(f, "evidence", "indicators", "iocs") or []
        if not isinstance(evidence_raw, list):
            evidence_raw = [evidence_raw]
        evidence = [s for s in (_stringify_evidence(e) for e in evidence_raw) if s]
        type_text = _sanitize_text(str(_pick(f, "type", "category", "name", "title") or "Finding"), 120)
        desc_text = _sanitize_text(str(_pick(f, "description", "details", "summary") or ""), 600)
        # Loops on small models often emit ~25 copies that differ only in the
        # IP embedded in `description`. Normalize IPs out of the dedupe key so
        # those near-duplicates collapse to one.
        norm_desc = _IPV4_RE.sub("<IP>", desc_text.lower())
        norm_type = type_text.lower()
        key = (norm_type, norm_desc)
        if key in seen:
            continue
        # Cap copies-per-type so a model fanning out one observation across
        # every IP it sees can't blow past the per-type budget.
        if per_type.get(norm_type, 0) >= _MAX_PER_TYPE:
            continue
        seen.add(key)
        per_type[norm_type] = per_type.get(norm_type, 0) + 1
        out.append(
            Finding(
                type=type_text,
                description=desc_text,
                evidence=evidence,
                risk=_sanitize_text(str(_pick(f, "risk", "severity", "impact") or ""), 120),
            )
        )
        if len(out) >= _MAX_FINDINGS:
            break
    return out


def _known_ips(meta: PcapMetadata) -> set[str]:
    """All IPs the parser actually saw — anything else cited by the model is a fabrication."""
    ips: set[str] = set()
    for c in meta.top_connections:
        ips.add(c.source_ip)
        ips.add(c.dest_ip)
    for p in meta.payload_findings:
        ips.add(p.source_ip)
        ips.add(p.dest_ip)
    for h in meta.http_requests:
        # http host fields are sometimes literal IPs
        if h.host and _IPV4_RE.fullmatch(h.host):
            ips.add(h.host)
    ips.update(meta.geo_locations.keys())
    ips.update(meta.ip_reputations.keys())
    return ips


_REP_CLAIM_RE = re.compile(
    r"(?i)\b(?:"
    r"block(?:list|listed)|"
    r"threat\s*feed|"
    r"known\s*malicious|"
    r"reported\s*as\s*malicious|"
    r"associated\s*with\s*known\s*threats?|"
    r"on\s*a\s*blocklist|"
    r"in\s*a\s*threat\s*feed|"
    r"abuse\s*ip\s*db|"
    r"threatfox|"
    r"previously\s*reported"
    r")\b"
)


def _drop_fake_reputation(findings: list[Finding], meta: PcapMetadata, agent: str) -> list[Finding]:
    """Drop findings that assert blocklist / threat-feed status for IPs the
    parser never enriched.

    Different from `_drop_fabricated_findings`: the IPs cited may be real
    (e.g. Apple, Google, Akamai pulled from `top_connections`), but the
    *reputation claim* is invented because none of those IPs are actually
    in `meta.ip_reputations`. ip_reputations is the only ground truth for
    "this IP is in a blocklist / threat feed".
    """
    real_rep_ips = set(meta.ip_reputations.keys())
    kept: list[Finding] = []
    dropped = 0
    for f in findings:
        text = " ".join([f.type, f.description, " ".join(f.evidence)])
        if not _REP_CLAIM_RE.search(text):
            kept.append(f)
            continue
        cited = set(_IPV4_RE.findall(text))
        # Reputation claim made and at least one cited IP is genuinely flagged → keep.
        if cited & real_rep_ips:
            kept.append(f)
            continue
        # Reputation claim with no citation at all → keep (could be a generic
        # observation about the capture as a whole; not strictly a fabrication).
        if not cited:
            kept.append(f)
            continue
        dropped += 1
    if dropped:
        log.warning(
            "%s: dropped %d finding(s) claiming blocklist/threat-feed status for "
            "IPs not present in ip_reputations (model fabricated reputation)",
            agent,
            dropped,
        )
    return kept


def _drop_fabricated_findings(findings: list[Finding], known: set[str], agent: str) -> list[Finding]:
    """Drop findings whose only cited IPs were never seen in the capture.

    Findings that cite no IPs at all are kept — they may be protocol/behavior
    observations that don't need an IP. Findings that cite at least one real
    IP are kept even if other IPs are also referenced.
    """
    kept: list[Finding] = []
    dropped = 0
    for f in findings:
        text = " ".join([f.type, f.description, " ".join(f.evidence)])
        cited = set(_IPV4_RE.findall(text))
        if not cited:
            kept.append(f)
            continue
        if cited & known:
            kept.append(f)
            continue
        dropped += 1
    if dropped:
        log.warning(
            "%s: dropped %d finding(s) that cited only IPs not present in metadata "
            "(model hallucinated addresses)",
            agent,
            dropped,
        )
    return kept


def _coerce_recommendations(raw: Any) -> list[str]:
    if isinstance(raw, list):
        return [str(r) for r in raw if r]
    if isinstance(raw, str) and raw.strip():
        # Split a single string into bullet-like lines.
        return [line.strip(" -*•\t") for line in raw.splitlines() if line.strip()]
    return []


def _analyst_pass(spec: AgentSpec, meta: PcapMetadata, *, findings_only: bool) -> tuple[Severity, str, list[Finding], list[str]]:
    """Call the analyst LLM. Returns (severity, raw_analysis_text, findings, recommendations).

    `raw_analysis_text` is "" when findings_only=True (writer will produce prose).
    Findings have already been filtered through dedupe + reputation + fabrication validators.
    """
    schema_hint = JSON_SCHEMA_HINT_FINDINGS_ONLY if findings_only else JSON_SCHEMA_HINT
    user_prompt = spec.user_prompt_template.format(metadata=_format_metadata(meta)) + "\n\n" + schema_hint
    content = chat(
        system=spec.system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
        max_tokens=spec.max_tokens,
        temperature=spec.temperature,
        json_mode=True,
        role="analyst",
    )

    if not content or not content.strip():
        log.warning("%s: analyst returned empty content", spec.name)
        return "medium", "", [], []

    parsed = _parse_json_response(content)
    if parsed is None:
        log.warning(
            "%s: analyst response not parseable; first 500 chars: %r",
            spec.name,
            content[:500],
        )
        # When findings_only=False (single-model mode), salvage prose from the
        # analysis field. When findings_only=True, the writer will produce
        # prose — we just lose findings on this run.
        extracted = "" if findings_only else (_extract_analysis_field(content) or "")
        return _extract_severity_from_text(content), extracted, [], []

    raw_findings = _pick(parsed, "findings", "key_findings", "iocs")
    findings = _coerce_findings(raw_findings)
    findings = _drop_fake_reputation(findings, meta, spec.name)
    findings = _drop_fabricated_findings(findings, _known_ips(meta), spec.name)
    recommendations = _coerce_recommendations(_pick(parsed, "recommendations", "remediation", "actions"))
    severity = _coerce_severity(str(_pick(parsed, "severity", "risk_level", "overall_risk") or "medium"))

    raw_analysis = "" if findings_only else (_pick(
        parsed, "analysis", "summary", "executive_summary", "overview", "report", "narrative", "details",
    ) or "")
    return severity, str(raw_analysis), findings, recommendations


_WRITER_SYSTEM_TEMPLATE = (
    "You are the writer for a SOC's PCAP analysis report, working in the "
    "{role} role (expertise: {expertise}). A separate security model has "
    "already extracted the structured findings below. Your job is to write "
    "the readable analysis prose that accompanies them.\n\n"
    "Output rules:\n"
    "- 3-5 paragraphs of Markdown, with `##` section headings.\n"
    "- Cite specific IPs, ports, protocols, ASNs, countries, and CVEs from "
    "the metadata. Never invent IPs, CVEs, ISPs, or threat-feed memberships.\n"
    "- Do not repeat the findings JSON verbatim. Synthesize them into a "
    "narrative an investigator can read top-to-bottom.\n"
    "- No JSON, no code fences, no preamble. Markdown only."
)


def _writer_pass(spec: AgentSpec, meta: PcapMetadata, severity: Severity, findings: list[Finding], recommendations: list[str]) -> tuple[str, str]:
    """Ask the writer LLM for prose Markdown analysis grounded in the analyst's findings.

    Returns (prose, error): error is "" on success and carries the real failure
    reason (HTTP status/body, timeout, ...) otherwise, so the UI can show it."""
    findings_dump = json.dumps(
        [{"type": f.type, "description": f.description, "risk": f.risk, "evidence": f.evidence} for f in findings],
        indent=2,
    )
    recs_dump = json.dumps(recommendations, indent=2) if recommendations else "[]"
    system = _WRITER_SYSTEM_TEMPLATE.format(role=spec.role, expertise=", ".join(spec.expertise))
    user = (
        f"Severity (from analyst): {severity}\n\n"
        f"VALIDATED FINDINGS:\n{findings_dump}\n\n"
        f"RECOMMENDATIONS:\n{recs_dump}\n\n"
        f"METADATA:\n{_format_metadata(meta)}\n\n"
        "Write the analysis prose now."
    )
    try:
        prose = chat(
            system=system,
            messages=[{"role": "user", "content": user}],
            max_tokens=2000,
            temperature=0.3,
            role="writer",
            label=f"writer:{spec.name}",
        ).strip()
        return prose, "" if prose else "the writer returned an empty response"
    except Exception as exc:  # noqa: BLE001
        log.warning("%s: writer pass failed (%s); falling back to a stub", spec.name, exc)
        return "", str(exc)


def run_agent(spec: AgentSpec, meta: PcapMetadata) -> AgentResponse:
    use_writer = writer_enabled()
    severity, raw_analysis, findings, recommendations = _analyst_pass(
        spec, meta, findings_only=use_writer
    )

    if use_writer:
        prose, writer_error = _writer_pass(spec, meta, severity, findings, recommendations)
        if prose:
            analysis_text = prose
        else:
            # Writer failed and analyst was findings-only — surface the real
            # reason so a misconfigured writer is diagnosable from the UI.
            analysis_text = (
                "**The writer model failed to produce prose for this section.**\n\n"
                f"Reason: {writer_error or 'unknown'}\n\n"
                "Use the **Test Writer Model** button in Settings → AI to probe the "
                "writer endpoint and auth. The analyst's validated findings below "
                "are unaffected."
            )
    else:
        analysis_text = _force_markdown(raw_analysis) if raw_analysis else (
            "_The model produced output that couldn't be parsed. Re-run the analysis, "
            "or switch models in Settings if it persists._"
        )

    if not analysis_text or not analysis_text.strip():
        analysis_text = "_No content returned._"

    return AgentResponse(
        agent_name=spec.name,
        severity=severity,
        analysis=analysis_text.strip(),
        findings=findings,
        recommendations=recommendations,
    )


def _extract_severity_from_text(text: str) -> Severity:
    """Best-effort severity extraction from free-form prose."""
    t = text.lower()
    for s in ("critical", "high", "medium", "low"):
        if s in t:
            return s  # type: ignore[return-value]
    return "medium"
