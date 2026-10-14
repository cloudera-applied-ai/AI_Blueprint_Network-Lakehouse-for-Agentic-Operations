"""GeoIP enrichment for external IPs in a capture.

Uses ip-api.com's free batch endpoint (45 req/min, no auth, batches of up to 100
per call). Skips RFC1918 / loopback / link-local / multicast / reserved ranges.
Caches results in process memory so repeated captures don't re-lookup.

If the lookup fails or the host has no internet egress, the analyzer still
returns metadata — geo_locations is just an empty dict.
"""
from __future__ import annotations

import ipaddress
import logging
from threading import Lock
from typing import Iterable

import httpx

from .schemas import GeoLocation

log = logging.getLogger(__name__)

API_URL = "http://ip-api.com/batch"
FIELDS = "status,message,query,country,countryCode,region,regionName,city,lat,lon,isp,org,as"
BATCH_SIZE = 100
TIMEOUT = 10.0

_cache: dict[str, GeoLocation] = {}
_cache_lock = Lock()


def _is_external(ip: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return not (
        addr.is_private
        or addr.is_loopback
        or addr.is_link_local
        or addr.is_multicast
        or addr.is_reserved
        or addr.is_unspecified
    )


def _lookup_batch(ips: list[str]) -> dict[str, GeoLocation]:
    if not ips:
        return {}
    payload = [{"query": ip, "fields": FIELDS} for ip in ips]
    out: dict[str, GeoLocation] = {}
    try:
        with httpx.Client(timeout=TIMEOUT) as client:
            res = client.post(API_URL, json=payload)
            res.raise_for_status()
            for entry in res.json():
                if entry.get("status") != "success":
                    continue
                ip = entry.get("query") or ""
                if not ip:
                    continue
                out[ip] = GeoLocation(
                    ip=ip,
                    country=entry.get("country") or "",
                    country_code=entry.get("countryCode") or "",
                    region=entry.get("regionName") or entry.get("region") or "",
                    city=entry.get("city") or "",
                    lat=float(entry.get("lat") or 0.0),
                    lon=float(entry.get("lon") or 0.0),
                    isp=entry.get("isp") or "",
                    org=entry.get("org") or "",
                    asn=entry.get("as") or "",
                )
    except Exception as exc:  # noqa: BLE001
        log.warning("GeoIP lookup failed: %s", exc)
    return out


def lookup(ips: Iterable[str]) -> dict[str, GeoLocation]:
    """Return geo info for external IPs only. Private IPs are silently skipped."""
    external = sorted({ip for ip in ips if _is_external(ip)})
    if not external:
        return {}

    result: dict[str, GeoLocation] = {}
    pending: list[str] = []

    with _cache_lock:
        for ip in external:
            if ip in _cache:
                result[ip] = _cache[ip]
            else:
                pending.append(ip)

    for i in range(0, len(pending), BATCH_SIZE):
        batch = _lookup_batch(pending[i : i + BATCH_SIZE])
        with _cache_lock:
            _cache.update(batch)
        result.update(batch)

    return result
