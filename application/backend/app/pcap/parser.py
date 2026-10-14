"""PCAP parsing using scapy. Extracts metadata used to feed the LLM agents.

Beyond simple protocol/connection counting this reconstructs bidirectional
transport flows (with TCP state and per-direction byte counts), and pulls
application-layer identity out of the packets — DNS query names, TLS SNI and
JA3 fingerprints, and a layer-2 summary (ARP/DHCP/VLAN). That gives the agents
the kind of signal a analyst reads off a real capture in Wireshark, instead of
just "top 15 connections".
"""
from __future__ import annotations

import math
from collections import defaultdict
from datetime import datetime, timezone

from scapy.all import ARP, DNS, DNSQR, DNSRR, ICMP, IP, TCP, UDP, Raw, rdpcap
from scapy.layers import http
from scapy.layers.l2 import Dot1Q, Ether

from . import geoip
from .schemas import (
    ConnectionInfo,
    DnsQueryInfo,
    FlowInfo,
    HttpRequestInfo,
    PayloadFinding,
    PcapMetadata,
    TlsHandshakeInfo,
)
from .tls import parse_client_hello

PROTO_NAMES = {1: "ICMP", 6: "TCP", 17: "UDP"}

# Well-known ports -> service label, for flow annotation.
SERVICE_PORTS = {
    20: "ftp-data", 21: "ftp", 22: "ssh", 23: "telnet", 25: "smtp", 53: "dns",
    67: "dhcp", 68: "dhcp", 69: "tftp", 80: "http", 110: "pop3", 123: "ntp",
    143: "imap", 161: "snmp", 162: "snmp-trap", 179: "bgp", 389: "ldap",
    443: "https", 445: "smb", 465: "smtps", 514: "syslog", 546: "dhcpv6",
    547: "dhcpv6", 587: "smtp-submission", 636: "ldaps", 993: "imaps",
    995: "pop3s", 1812: "radius", 1813: "radius-acct", 3306: "mysql",
    3389: "rdp", 4500: "ipsec-nat-t", 5060: "sip", 5061: "sips", 5222: "xmpp",
    5353: "mdns", 6379: "redis", 7547: "tr069-cwmp", 8080: "http-alt",
    8443: "https-alt", 51820: "wireguard",
}

PAYLOAD_PATTERNS: dict[str, list[str]] = {
    "command_injection": [";", "&&", "||", "`", "$(", "|"],
    "sql_injection": ["select ", "union ", "drop ", "or 1=1", "--"],
    "xss": ["<script>", "javascript:", "onerror=", "onload="],
    "file_paths": ["../", "/..", "/etc/passwd", "/etc/shadow", "/proc/", "/dev/"],
    "base64_blob": ["eyJ", "PHN2"],
    "powershell": ["powershell", "-enc", "-exec bypass", "iex"],
    "encoding": ["eval(", "char(", "fromcharcode", "decode"],
    "shell_commands": ["cmd.exe", "sh -c", "bash -c", "/bin/"],
}

EXE_SIGNATURES: dict[bytes, str] = {
    b"MZ": "Windows executable",
    b"\x7fELF": "Linux executable",
    b"\x89PNG": "PNG image",
    b"PK": "ZIP archive",
}

_DNS_QTYPES = {1: "A", 2: "NS", 5: "CNAME", 6: "SOA", 12: "PTR", 15: "MX",
               16: "TXT", 28: "AAAA", 33: "SRV", 65: "HTTPS"}


def _service(port: int) -> str:
    return SERVICE_PORTS.get(port, "")


def _entropy(data: bytes) -> float:
    if not data:
        return 0.0
    counts: dict[int, int] = {}
    for b in data:
        counts[b] = counts.get(b, 0) + 1
    total = len(data)
    return -sum((c / total) * math.log2(c / total) for c in counts.values())


_TLS_RECORD_TYPES = {0x14, 0x15, 0x16, 0x17}
_TLS_VERSIONS = {0x0301, 0x0302, 0x0303, 0x0304}


def _looks_like_tls(payload: bytes) -> bool:
    if len(payload) < 5:
        return False
    return payload[0] in _TLS_RECORD_TYPES and ((payload[1] << 8) | payload[2]) in _TLS_VERSIONS


def _printable_ratio(data: bytes) -> float:
    if not data:
        return 0.0
    printable = sum(1 for b in data if 0x20 <= b < 0x7F or b in (0x09, 0x0A, 0x0D))
    return printable / len(data)


def _classify_payload(payload: bytes) -> tuple[str, str] | None:
    sample = payload[:512]
    if _looks_like_tls(sample):
        return None
    for sig, label in EXE_SIGNATURES.items():
        if payload.startswith(sig):
            return f"file_transfer:{label}", label
    if _printable_ratio(sample) >= 0.85:
        try:
            text = sample.decode("utf-8", errors="ignore").lower()
        except Exception:
            text = ""
        matched = [kind for kind, needles in PAYLOAD_PATTERNS.items() if any(n in text for n in needles)]
        if matched:
            snippet = sample[:200].decode("utf-8", errors="replace")
            return ", ".join(matched), snippet
    if len(payload) >= 32 and _entropy(payload) > 7.5:
        return "high_entropy", f"entropy={_entropy(payload):.2f} size={len(payload)}B"
    return None


class _Flow:
    """Accumulator for one bidirectional flow, keyed by a canonical 5-tuple."""

    __slots__ = ("a", "b", "proto", "ap", "bp", "pk_ab", "pk_ba", "by_ab",
                 "by_ba", "t0", "t1", "flags", "syn", "synack", "fin", "rst",
                 "sni", "ja3")

    def __init__(self, a, ap, b, bp, proto):
        self.a, self.ap, self.b, self.bp, self.proto = a, ap, b, bp, proto
        self.pk_ab = self.pk_ba = self.by_ab = self.by_ba = 0
        self.t0 = None
        self.t1 = None
        self.flags: set[str] = set()
        self.syn = self.synack = self.fin = self.rst = False
        self.sni = ""
        self.ja3 = ""


def parse_pcap(path: str) -> PcapMetadata:
    packets = rdpcap(path)

    protocols: dict[str, int] = defaultdict(int)
    l2: dict[str, int] = defaultdict(int)
    flows: dict[tuple, _Flow] = {}

    payload_findings: list[PayloadFinding] = []
    http_requests: list[HttpRequestInfo] = []
    dns_queries: list[DnsQueryInfo] = []
    tls_handshakes: list[TlsHandshakeInfo] = []
    seen_client_hello: set[tuple] = set()
    src_ips: set[str] = set()
    dst_ips: set[str] = set()
    timestamps: list[float] = []

    for pkt in packets:
        ts = float(pkt.time)
        timestamps.append(ts)

        if Ether in pkt:
            if pkt.haslayer(Dot1Q):
                l2["VLAN-tagged"] += 1
        if pkt.haslayer(ARP):
            l2["ARP"] += 1
            protocols["ARP"] += 1
            continue

        if not pkt.haslayer(IP):
            protocols["non-IP"] += 1
            continue

        ip = pkt[IP]
        proto_name = PROTO_NAMES.get(int(ip.proto), f"IP-proto-{int(ip.proto)}")
        protocols[proto_name] += 1
        src_ips.add(ip.src)
        dst_ips.add(ip.dst)
        plen = len(pkt)

        sport = dport = None
        tcp = udp = None
        if pkt.haslayer(TCP):
            tcp = pkt[TCP]
            sport, dport = int(tcp.sport), int(tcp.dport)
        elif pkt.haslayer(UDP):
            udp = pkt[UDP]
            sport, dport = int(udp.sport), int(udp.dport)

        # ---- flow accumulation (canonical key so both directions merge) ----
        if sport is not None:
            fwd = (ip.src, sport) <= (ip.dst, dport)
            if fwd:
                key = (ip.src, sport, ip.dst, dport, proto_name)
                a, ap, b, bp = ip.src, sport, ip.dst, dport
            else:
                key = (ip.dst, dport, ip.src, sport, proto_name)
                a, ap, b, bp = ip.dst, dport, ip.src, sport
            fl = flows.get(key)
            if fl is None:
                fl = flows[key] = _Flow(a, ap, b, bp, proto_name)
            fl.t0 = ts if fl.t0 is None else min(fl.t0, ts)
            fl.t1 = ts if fl.t1 is None else max(fl.t1, ts)
            a_to_b = (ip.src, sport) == (a, ap)
            if a_to_b:
                fl.pk_ab += 1
                fl.by_ab += plen
            else:
                fl.pk_ba += 1
                fl.by_ba += plen
            if tcp is not None:
                f = int(tcp.flags)
                syn, ack, fin, rst = f & 0x02, f & 0x10, f & 0x01, f & 0x04
                if syn and ack:
                    fl.synack = True
                    fl.flags.add("SYN-ACK")
                elif syn:
                    fl.syn = True
                    fl.flags.add("SYN")
                if fin:
                    fl.fin = True
                    fl.flags.add("FIN")
                if rst:
                    fl.rst = True
                    fl.flags.add("RST")

        # ---- DNS ----
        if pkt.haslayer(DNS):
            dns = pkt[DNS]
            if dns.qd is not None and int(dns.qr) == 0:
                qname = _decode(getattr(dns.qd, "qname", b"")).rstrip(".")
                dns_queries.append(DnsQueryInfo(
                    source_ip=ip.src, dest_ip=ip.dst, qname=qname,
                    qtype=_DNS_QTYPES.get(int(getattr(dns.qd, "qtype", 1)), "A"),
                ))
            elif int(dns.qr) == 1 and dns_queries:
                answers = []
                rr = dns.an
                for _ in range(int(getattr(dns, "ancount", 0) or 0)):
                    if rr is None:
                        break
                    if isinstance(rr, DNSRR) and int(getattr(rr, "type", 0)) in (1, 28):
                        answers.append(_decode(getattr(rr, "rdata", b"")))
                    rr = rr.payload if hasattr(rr, "payload") else None
                nx = int(getattr(dns, "rcode", 0)) == 3
                qn = _decode(getattr(dns.qd, "qname", b"")).rstrip(".") if dns.qd else ""
                for q in reversed(dns_queries):
                    if q.qname == qn and not q.response_ips and not q.nxdomain:
                        q.response_ips = [a for a in answers if a]
                        q.nxdomain = nx
                        break

        # ---- TLS ClientHello (SNI + JA3) ----
        if tcp is not None and pkt.haslayer(Raw):
            raw = bytes(pkt[Raw].load)
            if raw[:1] == b"\x16":
                ch = parse_client_hello(raw)
                if ch is not None:
                    tup = (ip.src, ip.dst, ch.sni)
                    if tup not in seen_client_hello:
                        seen_client_hello.add(tup)
                        tls_handshakes.append(TlsHandshakeInfo(
                            source_ip=ip.src, dest_ip=ip.dst, sni=ch.sni,
                            version=ch.version, ja3=ch.ja3, ja3_hash=ch.ja3_hash,
                            alpn=ch.alpn,
                        ))
                    if sport is not None:
                        fkey = key
                        if fkey in flows:
                            flows[fkey].sni = ch.sni or flows[fkey].sni
                            flows[fkey].ja3 = ch.ja3_hash or flows[fkey].ja3

        # ---- payload signatures ----
        if pkt.haslayer(Raw):
            classification = _classify_payload(bytes(pkt[Raw].load))
            if classification:
                pattern_type, snippet = classification
                payload_findings.append(PayloadFinding(
                    source_ip=ip.src, dest_ip=ip.dst, pattern_type=pattern_type,
                    snippet=snippet[:200], size=len(pkt[Raw].load),
                ))

        # ---- HTTP ----
        if pkt.haslayer(http.HTTPRequest):
            h = pkt[http.HTTPRequest]
            http_requests.append(HttpRequestInfo(
                method=_decode(h.Method), path=_decode(h.Path),
                host=_decode(getattr(h, "Host", b"")),
                user_agent=_decode(getattr(h, "User_Agent", b"")),
            ))

    # ---- finalize flows ----
    flow_list: list[FlowInfo] = []
    for fl in flows.values():
        state = ""
        if fl.proto == "TCP":
            if fl.rst:
                state = "reset"
            elif fl.synack and fl.fin:
                state = "closed"
            elif fl.synack:
                state = "established"
            elif fl.syn and not fl.synack:
                state = "rejected" if fl.pk_ba == 0 else "syn_sent"
            else:
                state = "in_progress"
        service = _service(fl.bp) or _service(fl.ap)
        flow_list.append(FlowInfo(
            source_ip=fl.a, dest_ip=fl.b, protocol=fl.proto,
            source_port=fl.ap, dest_port=fl.bp, service=service,
            packets_out=fl.pk_ab, packets_in=fl.pk_ba,
            bytes_out=fl.by_ab, bytes_in=fl.by_ba,
            duration_s=round((fl.t1 - fl.t0), 3) if fl.t0 is not None else 0.0,
            tcp_flags=_ordered_flags(fl.flags), state=state,
            sni=fl.sni, ja3=fl.ja3,
        ))
    # Sort by "notability", not raw packet count: a port scan or C2 beacon is
    # many *tiny* flows, so pure top-by-packets would bury them under benign
    # bulk HTTPS. Boost anomalous TCP states and external destinations so the
    # attack flows survive the cap and reach the agents.
    def _notable(f: FlowInfo) -> int:
        score = f.bytes_out + f.bytes_in
        if f.state in ("reset", "rejected", "syn_sent"):
            score += 1_000_000
        if not f.dest_ip.startswith(("10.", "192.168.", "172.16.")):
            score += 50_000
        # strong egress asymmetry (exfil) is inherently notable
        if f.bytes_out > 4 * (f.bytes_in + 1) and f.bytes_out > 50_000:
            score += 2_000_000
        return score

    # Merge "most notable" flows (so scan/beacon/exfil survive) with "top
    # talkers by bytes" (so the benign baseline is still represented), rather
    # than letting hundreds of tiny scan flows crowd everything else out.
    by_notable = sorted(flow_list, key=_notable, reverse=True)
    by_bytes = sorted(flow_list, key=lambda f: f.bytes_out + f.bytes_in, reverse=True)
    merged: list[FlowInfo] = []
    seen_flow: set[tuple] = set()
    for f in by_notable[:110] + by_bytes[:60]:
        fk = (f.source_ip, f.source_port, f.dest_ip, f.dest_port, f.protocol)
        if fk not in seen_flow:
            seen_flow.add(fk)
            merged.append(f)
    flow_list = merged

    # ---- top_connections kept for back-compat, derived from flows ----
    top_connections = [
        ConnectionInfo(
            source_ip=f.source_ip, dest_ip=f.dest_ip, protocol=f.protocol,
            packet_count=f.packets_out + f.packets_in,
            bytes_transferred=f.bytes_out + f.bytes_in,
            source_ports=[f.source_port] if f.source_port else [],
            dest_ports=[f.dest_port] if f.dest_port else [],
        )
        for f in flow_list[:25]
    ]

    if timestamps:
        start = datetime.fromtimestamp(min(timestamps), tz=timezone.utc).isoformat()
        end = datetime.fromtimestamp(max(timestamps), tz=timezone.utc).isoformat()
    else:
        now = datetime.now(tz=timezone.utc).isoformat()
        start, end = now, now

    geo_locations = geoip.lookup(src_ips | dst_ips)

    return PcapMetadata(
        total_packets=len(packets),
        time_range_start=start,
        time_range_end=end,
        protocols=dict(protocols),
        top_connections=top_connections,
        payload_findings=payload_findings[:50],
        http_requests=http_requests[:50],
        unique_src_ips=len(src_ips),
        unique_dst_ips=len(dst_ips),
        flows=flow_list[:150],
        dns_queries=dns_queries[:150],
        tls_handshakes=tls_handshakes[:150],
        l2_summary=dict(l2),
        geo_locations=geo_locations,
    )


def _ordered_flags(flags: set[str]) -> list[str]:
    order = ["SYN", "SYN-ACK", "FIN", "RST"]
    return [f for f in order if f in flags]


def _decode(val: bytes | str | None) -> str:
    if val is None:
        return ""
    if isinstance(val, bytes):
        return val.decode("utf-8", errors="replace")
    return str(val)
