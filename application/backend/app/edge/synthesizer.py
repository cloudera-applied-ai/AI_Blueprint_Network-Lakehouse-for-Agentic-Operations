"""Scapy-based synthetic pcap generation, one builder per edge scenario.

Each capture is a realistic slice of headend traffic: a large benign baseline
(dozens of internal hosts doing DNS, real TLS handshakes with SNI, HTTP, NTP,
DHCP renewals, SNMP polling of the CMTS, TR-069 to the ACS) with the scenario's
attack traffic mixed in at the right point in time. Packets carry Ethernet +
optional 802.1Q framing, per-host MACs, realistic TTLs, TCP handshakes/teardown
with sequence numbers, and event-time timestamps, so the primary-DC parser sees
the same structure a real .pcap has (flows, SNI, JA3, DNS names, L2).

Builders take a seeded Random so every event varies while staying reproducible.
"""
from __future__ import annotations

import random
from pathlib import Path

from scapy.all import DNS, DNSQR, DNSRR, IP, TCP, UDP, Ether, Raw, SNMP, wrpcap
from scapy.contrib.igmp import IGMP  # noqa: F401  (ensures contrib import path works)
from scapy.layers.dhcp import BOOTP, DHCP
from scapy.layers.l2 import Dot1Q

from ..pcap import tls

_BASE_TS = 1_754_870_400.0  # 2025-08-11T00:00:00Z, fixed so captures are deterministic
_WINDOW_S = 120.0           # each capture spans ~2 minutes

# Attack actors (kept from the scenario scripts so the UI banners still match).
_C2_IP = "45.133.1.77"
_EXFIL_IP = "185.220.101.42"
_SCAN_TARGET = "10.20.30.40"
_INTERNAL = "10.20.30.15"

# Infrastructure the benign baseline talks to.
_GATEWAY = "10.20.30.1"
_DNS_RESOLVER = "10.20.30.2"
_CMTS = "10.20.30.3"
_ACS = "10.20.30.5"          # TR-069 auto-config server
_NTP = "216.239.35.0"        # time.google.com
_DHCP_SERVER = "10.20.30.1"

# Popular destinations the benign clients reach (name -> public IP for geoip).
_POPULAR = [
    ("www.google.com", "142.250.72.196"),
    ("clients3.google.com", "142.250.72.206"),
    ("www.microsoft.com", "23.55.155.30"),
    ("windowsupdate.microsoft.com", "20.73.194.208"),
    ("www.cloudflare.com", "104.16.132.229"),
    ("api.github.com", "140.82.113.6"),
    ("cdn.jsdelivr.net", "151.101.65.229"),
    ("outlook.office365.com", "52.96.104.2"),
    ("www.netflix.com", "44.242.60.108"),
    ("i.redd.it", "151.101.65.140"),
    ("telemetry.comcast.net", "96.114.157.30"),
    ("ocsp.digicert.com", "93.184.220.29"),
]
_TLS_CLIENTS = ["chrome", "firefox", "schannel", "openssl", "mbedtls"]


def _mac(rng: random.Random, host: int) -> str:
    return "02:%02x:%02x:%02x:%02x:%02x" % (
        (host >> 8) & 0xFF, host & 0xFF, rng.randint(0, 255),
        rng.randint(0, 255), rng.randint(0, 255))


_GW_MAC = "02:aa:00:00:00:01"


class _Builder:
    """Accumulates packets with L2 framing, per-host MAC + TTL, and timestamps."""

    def __init__(self, rng: random.Random, *, vlan: int | None = 30):
        self.rng = rng
        self.vlan = vlan
        self.pkts: list = []
        self._macs: dict[str, str] = {}

    def mac_for(self, ip: str) -> str:
        if ip not in self._macs:
            # Infra + external share the gateway-side MAC (packets are routed).
            internal = ip.startswith("10.20.30.")
            self._macs[ip] = _mac(self.rng, len(self._macs) + 2) if internal else _GW_MAC
        return self._macs[ip]

    def emit(self, ts: float, ip_pkt) -> None:
        src, dst = ip_pkt.src, ip_pkt.dst
        eth = Ether(src=self.mac_for(src), dst=self.mac_for(dst) if dst.startswith("10.20.30.") else _GW_MAC)
        frame = eth / Dot1Q(vlan=self.vlan) / ip_pkt if self.vlan else eth / ip_pkt
        frame.time = ts
        self.pkts.append(frame)

    # -- TCP helpers -------------------------------------------------------
    def tcp_session(self, ts: float, src: str, sport: int, dst: str, dport: int,
                    *, req: bytes = b"", resp: bytes = b"", teardown: bool = True,
                    ttl_src: int = 64, ttl_dst: int = 118) -> float:
        """A full TCP session: handshake, optional data, optional FIN teardown.
        Returns the timestamp after the session completes."""
        rng = self.rng
        cseq = rng.randint(1_000_000, 4_000_000_000)
        sseq = rng.randint(1_000_000, 4_000_000_000)
        rtt = rng.uniform(0.004, 0.045)
        self.emit(ts, IP(src=src, dst=dst, ttl=ttl_src) / TCP(sport=sport, dport=dport, flags="S", seq=cseq))
        ts += rtt
        self.emit(ts, IP(src=dst, dst=src, ttl=ttl_dst) / TCP(sport=dport, dport=sport, flags="SA", seq=sseq, ack=cseq + 1))
        ts += rtt / 2
        self.emit(ts, IP(src=src, dst=dst, ttl=ttl_src) / TCP(sport=sport, dport=dport, flags="A", seq=cseq + 1, ack=sseq + 1))
        cseq += 1
        sseq += 1
        if req:
            for chunk in _chunks(req, 1400):
                ts += rng.uniform(0.001, 0.02)
                self.emit(ts, IP(src=src, dst=dst, ttl=ttl_src) / TCP(sport=sport, dport=dport, flags="PA", seq=cseq, ack=sseq) / Raw(load=chunk))
                cseq += len(chunk)
        if resp:
            for chunk in _chunks(resp, 1400):
                ts += rng.uniform(0.002, 0.03)
                self.emit(ts, IP(src=dst, dst=src, ttl=ttl_dst) / TCP(sport=dport, dport=sport, flags="PA", seq=sseq, ack=cseq) / Raw(load=chunk))
                sseq += len(chunk)
        if teardown:
            ts += rng.uniform(0.005, 0.05)
            self.emit(ts, IP(src=src, dst=dst, ttl=ttl_src) / TCP(sport=sport, dport=dport, flags="FA", seq=cseq, ack=sseq))
            ts += rtt
            self.emit(ts, IP(src=dst, dst=src, ttl=ttl_dst) / TCP(sport=dport, dport=sport, flags="FA", seq=sseq, ack=cseq + 1))
            ts += rtt / 2
            self.emit(ts, IP(src=src, dst=dst, ttl=ttl_src) / TCP(sport=sport, dport=dport, flags="A", seq=cseq + 1, ack=sseq + 1))
        return ts

    def tls_session(self, ts: float, src: str, dst: str, sni: str, client: str,
                    *, app_out: int = 1, app_in: int = 1, sport: int | None = None) -> float:
        """A realistic HTTPS session: handshake (ClientHello w/ SNI + JA3,
        ServerHello) then a few application-data records."""
        rng = self.rng
        sport = sport or rng.randint(49152, 65535)
        profile = tls.PROFILES[client]
        ch = tls.build_client_hello(sni, profile, rng)
        sh = tls.build_server_hello(profile, rng)
        ts = self.tcp_session(ts, src, sport, dst, 443, req=ch, resp=sh, teardown=False)
        cseq_note = None  # (data records use fresh PA packets; seq realism not required post-handshake)
        for _ in range(app_out):
            ts += rng.uniform(0.005, 0.08)
            self.emit(ts, IP(src=src, dst=dst, ttl=64) / TCP(sport=sport, dport=443, flags="PA") / Raw(load=tls.app_data(rng.randint(120, 1300), rng)))
        for _ in range(app_in):
            ts += rng.uniform(0.01, 0.1)
            self.emit(ts, IP(src=dst, dst=src, ttl=118) / TCP(sport=443, dport=sport, flags="PA") / Raw(load=tls.app_data(rng.randint(400, 1400), rng)))
        ts += rng.uniform(0.02, 0.2)
        self.emit(ts, IP(src=src, dst=dst, ttl=64) / TCP(sport=sport, dport=443, flags="FA"))
        return ts

    def dns_query(self, ts: float, src: str, qname: str, answer: str | None,
                  *, qtype: str = "A", nx: bool = False) -> None:
        sport = self.rng.randint(49152, 65535)
        txid = self.rng.randint(0, 65535)
        qt = {"A": 1, "AAAA": 28, "HTTPS": 65}.get(qtype, 1)
        self.emit(ts, IP(src=src, dst=_DNS_RESOLVER, ttl=64) / UDP(sport=sport, dport=53) /
                  DNS(id=txid, rd=1, qd=DNSQR(qname=qname, qtype=qt)))
        an = None
        rcode = 3 if nx else 0
        if answer and not nx:
            an = DNSRR(rrname=qname, type=1, rdata=answer, ttl=self.rng.randint(60, 3600))
        self.emit(ts + self.rng.uniform(0.003, 0.03),
                  IP(src=_DNS_RESOLVER, dst=src, ttl=118) / UDP(sport=53, dport=sport) /
                  DNS(id=txid, qr=1, rd=1, ra=1, rcode=rcode, qd=DNSQR(qname=qname, qtype=qt),
                      an=an, ancount=1 if an else 0))

    def udp_exchange(self, ts: float, src: str, sport: int, dst: str, dport: int,
                     req: bytes, resp: bytes | None = None) -> None:
        self.emit(ts, IP(src=src, dst=dst, ttl=64) / UDP(sport=sport, dport=dport) / Raw(load=req))
        if resp is not None:
            self.emit(ts + self.rng.uniform(0.002, 0.02),
                      IP(src=dst, dst=src, ttl=118) / UDP(sport=dport, dport=sport) / Raw(load=resp))


def _chunks(data: bytes, n: int):
    for i in range(0, len(data), n):
        yield data[i:i + n]


def _internal_host(rng: random.Random) -> str:
    # Subscriber CPE + headend hosts across a /24, avoiding infra + attack IPs.
    while True:
        h = rng.randint(20, 240)
        ip = f"10.20.30.{h}"
        if ip not in (_GATEWAY, _DNS_RESOLVER, _CMTS, _ACS, _SCAN_TARGET, _INTERNAL):
            return ip


def _benign_baseline(b: _Builder, *, n_hosts: int = 40, sessions: int = 220) -> None:
    """Fill the capture with ordinary headend/subscriber traffic."""
    rng = b.rng
    hosts = sorted({_internal_host(rng) for _ in range(n_hosts)})

    # Infra chatter spread across the window.
    for i in range(12):  # NTP sync from a few hosts
        h = rng.choice(hosts)
        ts = _BASE_TS + rng.uniform(0, _WINDOW_S)
        b.udp_exchange(ts, h, rng.randint(49152, 65535), _NTP, 123,
                       b"\x1b" + b"\x00" * 47, b"\x1c" + b"\x00" * 47)
    for i in range(8):  # DHCP renewals (unicast REQUEST/ACK)
        h = rng.choice(hosts)
        ts = _BASE_TS + rng.uniform(0, _WINDOW_S)
        req = BOOTP(op=1, chaddr=bytes(rng.randrange(256) for _ in range(6))) / DHCP(options=[("message-type", "request"), "end"])
        ack = BOOTP(op=2) / DHCP(options=[("message-type", "ack"), "end"])
        b.emit(ts, IP(src=h, dst=_DHCP_SERVER, ttl=64) / UDP(sport=68, dport=67) / req)
        b.emit(ts + rng.uniform(0.003, 0.02), IP(src=_DHCP_SERVER, dst=h, ttl=64) / UDP(sport=67, dport=68) / ack)
    for i in range(10):  # SNMP polls of the CMTS from the NOC collector
        ts = _BASE_TS + rng.uniform(0, _WINDOW_S)
        try:
            b.emit(ts, IP(src=_CMTS, dst=_GATEWAY, ttl=64) / UDP(sport=rng.randint(49152, 65535), dport=161) /
                   SNMP(community="public"))
        except Exception:
            b.udp_exchange(ts, _GATEWAY, rng.randint(49152, 65535), _CMTS, 161, b"\x30\x26\x02\x01\x01\x04\x06public")
    for i in range(6):  # TR-069 CWMP (CPE -> ACS) over HTTP
        h = rng.choice(hosts)
        ts = _BASE_TS + rng.uniform(0, _WINDOW_S)
        body = (b"POST /acs HTTP/1.1\r\nHost: acs.local\r\nContent-Type: text/xml\r\n"
                b"User-Agent: TR069-Client/1.0\r\nSOAPAction: \r\n\r\n"
                b"<soap:Envelope><cwmp:Inform></cwmp:Inform></soap:Envelope>")
        b.tcp_session(ts, h, rng.randint(49152, 65535), _ACS, 7547, req=body,
                      resp=b"HTTP/1.1 200 OK\r\nContent-Length: 0\r\n\r\n")

    # Web/DNS/TLS sessions — the bulk of the baseline.
    for _ in range(sessions):
        h = rng.choice(hosts)
        ts = _BASE_TS + rng.uniform(0, _WINDOW_S)
        name, ip = rng.choice(_POPULAR)
        client = rng.choice(_TLS_CLIENTS)
        b.dns_query(ts, h, name, ip, qtype=rng.choice(["A", "A", "A", "HTTPS"]))
        b.tls_session(ts + rng.uniform(0.02, 0.15), h, ip, name, client,
                      app_out=rng.randint(1, 4), app_in=rng.randint(1, 6))
    # A little plain HTTP + OCSP for variety
    for _ in range(12):
        h = rng.choice(hosts)
        ts = _BASE_TS + rng.uniform(0, _WINDOW_S)
        b.dns_query(ts, h, "ocsp.digicert.com", "93.184.220.29")
        b.tcp_session(ts + 0.03, h, rng.randint(49152, 65535), "93.184.220.29", 80,
                      req=b"GET / HTTP/1.1\r\nHost: ocsp.digicert.com\r\nUser-Agent: Mozilla/5.0\r\n\r\n",
                      resp=b"HTTP/1.1 200 OK\r\nContent-Length: 5\r\n\r\nhello")


# --------------------------------------------------------------------------- attacks

def _synth_port_scan(b: _Builder) -> None:
    rng = b.rng
    _benign_baseline(b)
    attacker = _internal_host(rng)
    ts = _BASE_TS + rng.uniform(20, 60)
    ports = list(range(1, 1025))
    rng.shuffle(ports)
    open_ports = {22, 80, 443, 3389}
    for dport in ports[:420]:
        ts += rng.uniform(0.001, 0.004)
        sport = rng.randint(40000, 60000)
        b.emit(ts, IP(src=attacker, dst=_SCAN_TARGET, ttl=64) / TCP(sport=sport, dport=dport, flags="S", seq=rng.randint(0, 2**32 - 1)))
        if dport in open_ports:
            b.emit(ts + 0.001, IP(src=_SCAN_TARGET, dst=attacker, ttl=64) / TCP(sport=dport, dport=sport, flags="SA"))
            b.emit(ts + 0.002, IP(src=attacker, dst=_SCAN_TARGET, ttl=64) / TCP(sport=sport, dport=dport, flags="R"))
        else:  # closed port -> RST/ACK, like a real stack
            b.emit(ts + 0.001, IP(src=_SCAN_TARGET, dst=attacker, ttl=64) / TCP(sport=dport, dport=sport, flags="RA"))


def _synth_c2_beacon(b: _Builder) -> None:
    rng = b.rng
    _benign_baseline(b)
    ts = _BASE_TS
    sni = "cdn-update-cache.example"
    # Periodic HTTPS beacons: a real ClientHello (odd JA3 for an implant) + a
    # constant-size app-data record every ~20s with jitter.
    for _ in range(6):
        ts += rng.uniform(18, 22)
        b.dns_query(ts - 0.05, _INTERNAL, sni, _C2_IP)
        b.tls_session(ts, _INTERNAL, _C2_IP, sni, "openssl", app_out=1, app_in=1)
    # A plaintext HTTP check-in with a suspicious UA + beacon path.
    ts += rng.uniform(18, 22)
    b.tcp_session(ts, _INTERNAL, rng.randint(49152, 65535), _C2_IP, 80,
                  req=(b"GET /gate.php?id=7f3a2 HTTP/1.1\r\nHost: cdn-update-cache.example\r\n"
                       b"User-Agent: Mozilla/5.0 (Windows NT 10.0) beacon/1.2\r\nAccept: */*\r\n\r\n"),
                  resp=b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\nok")


def _synth_data_exfiltration(b: _Builder) -> None:
    rng = b.rng
    _benign_baseline(b)
    ts = _BASE_TS + rng.uniform(15, 30)
    sni = "backup.sync-vault.example"
    b.dns_query(ts - 0.05, _INTERNAL, sni, _EXFIL_IP)
    # TLS handshake, then a large asymmetric outbound stream of high-entropy data.
    sport = rng.randint(49152, 65535)
    profile = tls.PROFILES["openssl"]
    ts = b.tcp_session(ts, _INTERNAL, sport, _EXFIL_IP, 443,
                       req=tls.build_client_hello(sni, profile, rng),
                       resp=tls.build_server_hello(profile, rng), teardown=False)
    for i in range(120):
        ts += rng.uniform(0.003, 0.02)
        b.emit(ts, IP(src=_INTERNAL, dst=_EXFIL_IP, ttl=64) / TCP(sport=sport, dport=443, flags="PA") /
               Raw(load=tls.app_data(1380, rng)))
        if i % 12 == 0:
            b.emit(ts + 0.002, IP(src=_EXFIL_IP, dst=_INTERNAL, ttl=118) / TCP(sport=443, dport=sport, flags="A"))


def _synth_ddos(b: _Builder) -> None:
    rng = b.rng
    _benign_baseline(b, sessions=120)
    target = _INTERNAL
    ts = _BASE_TS + rng.uniform(30, 50)
    # DNS-amplification + SYN flood from many spoofed sources.
    for i in range(700):
        ts += rng.uniform(0.0002, 0.0008)
        src = f"198.51.100.{rng.randint(1, 254)}" if i % 3 else f"203.0.113.{rng.randint(1, 254)}"
        if i % 2 == 0:
            b.emit(ts, IP(src=src, dst=target, ttl=rng.randint(48, 64)) / UDP(sport=rng.randint(1024, 65535), dport=53) /
                   DNS(rd=1, qd=DNSQR(qname="isc.org", qtype=255)))  # ANY = amplification
        else:
            b.emit(ts, IP(src=src, dst=target, ttl=rng.randint(48, 64)) / TCP(sport=rng.randint(1024, 65535), dport=80, flags="S", seq=rng.randint(0, 2**32 - 1)))


BUILDERS = {
    "port_scan": _synth_port_scan,
    "c2_beacon": _synth_c2_beacon,
    "data_exfiltration": _synth_data_exfiltration,
    "ddos": _synth_ddos,
}


def generate(scenario_id: str, out_path: str, *, seed: int = 0) -> str:
    """Generate a synthetic pcap for `scenario_id` and write it to `out_path`."""
    builder_fn = BUILDERS.get(scenario_id)
    if builder_fn is None:
        raise ValueError(f"No synthesizer for scenario: {scenario_id}")
    rng = random.Random(seed)
    b = _Builder(rng, vlan=30)
    builder_fn(b)
    b.pkts.sort(key=lambda p: p.time)
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    wrpcap(out_path, b.pkts)
    return out_path
