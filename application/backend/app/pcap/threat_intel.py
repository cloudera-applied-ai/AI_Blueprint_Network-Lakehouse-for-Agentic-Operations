"""Threat-intel enrichment.

Sources, best-effort and layered:

  - **Bundled IOC feed** (`threat_intel_local`) — always available; the
    operator's own curated indicators. Flags the demo's known-bad hosts/domains
    so the Threat Intel tab is populated even with no keys or no connectivity.
  - **ThreatFox** (abuse.ch) — IP/IOC blocklist matches. As of 2024 abuse.ch
    requires an Auth-Key, so this runs only when `THREATFOX_API_KEY` is set.
  - **AbuseIPDB** — richer IP reputation with abuse scores. Key-required.
  - **NVD** (NIST) — CVE keyword search, key-less at low rate (5 req/30s
    anonymous, 50 req/30s with key).

Everything is wrapped in try/except so a missing key, network outage, or
rate-limit response degrades gracefully — analysis still completes.
"""
from __future__ import annotations

import asyncio
import logging
import re
from threading import Lock
from typing import Iterable

import httpx

from . import threat_intel_local
from .schemas import CveCandidate, IpReputation, PcapMetadata

log = logging.getLogger(__name__)

THREATFOX_URL = "https://threatfox-api.abuse.ch/api/v1/"
ABUSEIPDB_URL = "https://api.abuseipdb.com/api/v2/check"
NVD_URL = "https://services.nvd.nist.gov/rest/json/cves/2.0"

HTTP_TIMEOUT = 10.0
MAX_IPS = 25
MAX_KEYWORDS = 6
MAX_CVES_PER_KEYWORD = 5

_ip_cache: dict[str, IpReputation] = {}
_cve_cache: dict[str, list[CveCandidate]] = {}
_cache_lock = Lock()


# ---------------------------------------------------------------------------
# IP reputation
# ---------------------------------------------------------------------------


async def _threatfox_one(client: httpx.AsyncClient, ip: str, key: str) -> dict | None:
    try:
        r = await client.post(
            THREATFOX_URL,
            json={"query": "search_ioc", "search_term": ip},
            headers={"Auth-Key": key},
            timeout=HTTP_TIMEOUT,
        )
        r.raise_for_status()
        body = r.json()
        if body.get("query_status") == "ok":
            return body
    except Exception as exc:  # noqa: BLE001
        log.debug("ThreatFox lookup failed for %s: %s", ip, exc)
    return None


async def _abuseipdb_one(client: httpx.AsyncClient, ip: str, key: str) -> dict | None:
    try:
        r = await client.get(
            ABUSEIPDB_URL,
            params={"ipAddress": ip, "maxAgeInDays": 90, "verbose": ""},
            headers={"Key": key, "Accept": "application/json"},
            timeout=HTTP_TIMEOUT,
        )
        r.raise_for_status()
        return r.json().get("data")
    except Exception as exc:  # noqa: BLE001
        log.debug("AbuseIPDB lookup failed for %s: %s", ip, exc)
    return None


def _merge_reputation(
    ip: str, threatfox: dict | None, abuseipdb: dict | None
) -> IpReputation | None:
    sources: list[str] = []
    categories: set[str] = set()
    descriptions: list[str] = []
    abuse_score = 0
    last_reported = ""
    in_blocklist = False

    if threatfox and threatfox.get("data"):
        sources.append("ThreatFox")
        in_blocklist = True
        for entry in threatfox["data"][:10]:
            if entry.get("threat_type"):
                categories.add(entry["threat_type"])
            if entry.get("malware"):
                categories.add(entry["malware"])
            if entry.get("first_seen"):
                last_reported = entry["first_seen"]
            tags = entry.get("tags") or []
            for t in tags:
                if t:
                    categories.add(str(t))

    if abuseipdb:
        sources.append("AbuseIPDB")
        abuse_score = int(abuseipdb.get("abuseConfidenceScore") or 0)
        if abuse_score >= 25:
            in_blocklist = True
        if abuseipdb.get("usageType"):
            descriptions.append(f"Usage: {abuseipdb['usageType']}")
        if abuseipdb.get("countryCode"):
            descriptions.append(f"Country: {abuseipdb['countryCode']}")
        if abuseipdb.get("lastReportedAt"):
            last_reported = abuseipdb["lastReportedAt"]
        for r in (abuseipdb.get("reports") or [])[:5]:
            cats = r.get("categories") or []
            categories.update(str(c) for c in cats)

    if not sources:
        return None

    return IpReputation(
        ip=ip,
        in_blocklist=in_blocklist,
        sources=sources,
        categories=sorted(categories)[:15],
        abuse_score=abuse_score,
        last_reported=last_reported,
        notes="; ".join(descriptions),
    )


async def lookup_ip_reputations(
    ips: Iterable[str], abuseipdb_key: str = "", threatfox_key: str = ""
) -> dict[str, IpReputation]:
    """Look up reputations for the given IPs, capped at MAX_IPS.

    The bundled IOC feed is always consulted first; live ThreatFox (only when a
    key is configured) and AbuseIPDB results are merged on top.
    """
    candidates = list(dict.fromkeys(ips))[:MAX_IPS]
    if not candidates:
        return {}

    out: dict[str, IpReputation] = {}
    pending: list[str] = []

    # Bundled IOC feed: always available, never cached away.
    local_hits = threat_intel_local.local_reputations(candidates)
    out.update(local_hits)

    with _cache_lock:
        for ip in candidates:
            if ip in local_hits:
                continue
            if ip in _ip_cache:
                rep = _ip_cache[ip]
                if rep.in_blocklist:
                    out[ip] = rep
            else:
                pending.append(ip)

    if not pending:
        return out

    async with httpx.AsyncClient() as client:
        tf_tasks = [
            _threatfox_one(client, ip, threatfox_key) if threatfox_key else asyncio.sleep(0, result=None)
            for ip in pending
        ]
        ab_tasks = [
            _abuseipdb_one(client, ip, abuseipdb_key) if abuseipdb_key else asyncio.sleep(0, result=None)
            for ip in pending
        ]
        tf_results, ab_results = await asyncio.gather(
            asyncio.gather(*tf_tasks),
            asyncio.gather(*ab_tasks),
        )

    for ip, tf, ab in zip(pending, tf_results, ab_results):
        rep = _merge_reputation(ip, tf, ab)
        if rep is None:
            # Cache a "clean" record so we don't re-look-up next time. Mark
            # in_blocklist=False and don't surface in the result map.
            rep = IpReputation(
                ip=ip,
                in_blocklist=False,
                sources=[],
                categories=[],
                abuse_score=0,
                last_reported="",
                notes="",
            )
        with _cache_lock:
            _ip_cache[ip] = rep
        if rep.in_blocklist:
            out[ip] = rep

    return out


# ---------------------------------------------------------------------------
# CVE search
# ---------------------------------------------------------------------------


_USER_AGENT_PRODUCT_RE = re.compile(
    r"([A-Za-z][A-Za-z0-9_.+-]{2,30})/(\d+\.\d+(?:\.\d+)?)"
)
_KNOWN_PATH_KEYWORDS = (
    ("/struts", "Apache Struts"),
    ("/wp-admin", "WordPress"),
    ("/wp-login", "WordPress"),
    ("/phpmyadmin", "phpMyAdmin"),
    ("/jenkins", "Jenkins"),
    ("/manager/html", "Apache Tomcat manager"),
    ("/cgi-bin/", "Bash CGI"),
    ("/.env", "Environment file disclosure"),
    ("/.git", "Git repository disclosure"),
    ("${jndi:", "Log4Shell"),
    ("/HNAP1", "D-Link HNAP"),
    ("/owa/", "Microsoft Exchange OWA"),
)
_PAYLOAD_PATTERN_TO_KEYWORD = {
    "command_injection": "remote command execution",
    "sql_injection": "SQL injection",
    "xss": "cross site scripting",
    "powershell": "PowerShell payload",
    "shell_commands": "shell command injection",
    "high_entropy": "obfuscated payload",
}


def _extract_keywords(meta: PcapMetadata) -> list[str]:
    """Pull terse, search-worthy keywords out of the capture."""
    keywords: list[str] = []
    seen: set[str] = set()

    def add(term: str) -> None:
        t = term.strip()
        if not t or t.lower() in seen:
            return
        seen.add(t.lower())
        keywords.append(t)

    for h in meta.http_requests[:50]:
        if h.user_agent:
            for product, version in _USER_AGENT_PRODUCT_RE.findall(h.user_agent):
                if product.lower() in {"mozilla", "applewebkit", "safari", "gecko", "chrome", "firefox", "version"}:
                    continue
                add(f"{product} {version}")
        if h.path:
            lower = h.path.lower()
            for needle, label in _KNOWN_PATH_KEYWORDS:
                if needle.lower() in lower:
                    add(label)

    for p in meta.payload_findings[:25]:
        for token in p.pattern_type.split(","):
            kw = _PAYLOAD_PATTERN_TO_KEYWORD.get(token.strip().lower())
            if kw:
                add(kw)

    # Malware families for any bundled-IOC hosts/domains seen in this capture.
    # These drive a real NVD search for that family's CVEs (e.g. Cobalt Strike).
    ips = set(_candidate_external_ips(meta))
    domains = {t.sni for t in (getattr(meta, "tls_handshakes", None) or []) if t.sni}
    domains |= {d.qname for d in (getattr(meta, "dns_queries", None) or []) if d.qname}
    domains |= {h.host for h in meta.http_requests if getattr(h, "host", "")}
    for fam in threat_intel_local.malware_keywords_for(ips, domains):
        add(fam)

    return keywords[:MAX_KEYWORDS]


async def _nvd_search(client: httpx.AsyncClient, keyword: str, key: str = "") -> list[CveCandidate]:
    headers = {"apiKey": key} if key else {}
    try:
        r = await client.get(
            NVD_URL,
            params={
                "keywordSearch": keyword,
                "resultsPerPage": MAX_CVES_PER_KEYWORD,
            },
            headers=headers,
            timeout=20.0,
        )
        r.raise_for_status()
        body = r.json()
    except Exception as exc:  # noqa: BLE001
        log.warning("NVD search failed for %s: %s", keyword, exc)
        return []

    out: list[CveCandidate] = []
    for item in body.get("vulnerabilities", []):
        cve = item.get("cve") or {}
        cve_id = cve.get("id") or ""
        if not cve_id:
            continue

        descriptions = cve.get("descriptions") or []
        summary = next(
            (d.get("value", "") for d in descriptions if d.get("lang") == "en"),
            "",
        )

        score = 0.0
        severity = ""
        metrics = cve.get("metrics") or {}
        for variant in ("cvssMetricV31", "cvssMetricV30", "cvssMetricV2"):
            entries = metrics.get(variant) or []
            if entries:
                cvss = entries[0].get("cvssData") or {}
                score = float(cvss.get("baseScore") or 0.0)
                severity = (
                    cvss.get("baseSeverity")
                    or entries[0].get("baseSeverity")
                    or ""
                )
                break

        out.append(
            CveCandidate(
                id=cve_id,
                summary=summary[:500],
                severity=str(severity).lower(),
                score=score,
                matched_keyword=keyword,
                url=f"https://nvd.nist.gov/vuln/detail/{cve_id}",
            )
        )
    return out


async def search_cves(meta: PcapMetadata, nvd_key: str = "") -> list[CveCandidate]:
    keywords = _extract_keywords(meta)
    if not keywords:
        return []

    pending: list[str] = []
    cached: list[CveCandidate] = []
    with _cache_lock:
        for kw in keywords:
            if kw in _cve_cache:
                cached.extend(_cve_cache[kw])
            else:
                pending.append(kw)

    if pending:
        async with httpx.AsyncClient() as client:
            results = await asyncio.gather(
                *(_nvd_search(client, kw, nvd_key) for kw in pending)
            )
        with _cache_lock:
            for kw, hits in zip(pending, results):
                _cve_cache[kw] = hits
        for hits in results:
            cached.extend(hits)

    # Dedupe by CVE id, prefer highest score, sort descending.
    by_id: dict[str, CveCandidate] = {}
    for c in cached:
        if c.id not in by_id or c.score > by_id[c.id].score:
            by_id[c.id] = c
    return sorted(by_id.values(), key=lambda c: (-c.score, c.id))[:25]


# ---------------------------------------------------------------------------
# Top-level entry
# ---------------------------------------------------------------------------


def _is_public_ip(ip: str) -> bool:
    """Rough public-IP check without importing ipaddress for every candidate."""
    if not ip or ":" in ip:  # skip IPv6 for the demo scope
        return ":" in ip  # treat IPv6 as "public" (rare in fixtures)
    return not (
        ip.startswith("10.")
        or ip.startswith("192.168.")
        or ip.startswith("127.")
        or ip.startswith("169.254.")
        or any(ip.startswith(f"172.{n}.") for n in range(16, 32))
    )


def _candidate_external_ips(meta: PcapMetadata) -> list[str]:
    """External IPs worth a reputation lookup — from geoip, flows, and DNS
    answers — so enrichment doesn't depend on geoip having resolved them."""
    ips: list[str] = list(meta.geo_locations or {})
    for f in getattr(meta, "flows", None) or []:
        for ip in (f.source_ip, f.dest_ip):
            if _is_public_ip(ip):
                ips.append(ip)
    for d in getattr(meta, "dns_queries", None) or []:
        for ip in d.response_ips:
            if _is_public_ip(ip):
                ips.append(ip)
    # de-dupe, preserve order
    return list(dict.fromkeys(ips))


async def enrich(
    meta: PcapMetadata,
    *,
    abuseipdb_key: str = "",
    nvd_key: str = "",
    threatfox_key: str = "",
) -> tuple[dict[str, IpReputation], list[CveCandidate]]:
    """Return (ip_reputations, cve_candidates). Best-effort, no exceptions raised."""
    external_ips = _candidate_external_ips(meta)
    rep_task = lookup_ip_reputations(
        external_ips, abuseipdb_key=abuseipdb_key, threatfox_key=threatfox_key
    )
    cve_task = search_cves(meta, nvd_key=nvd_key)

    try:
        reputations, cves = await asyncio.gather(rep_task, cve_task)
    except Exception as exc:  # noqa: BLE001
        log.warning("Threat-intel enrichment failed: %s", exc)
        return {}, []

    return reputations, cves
