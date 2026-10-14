"""Minimal TLS handshake builder/parser (no scapy TLS layer needed).

Two consumers:
  * the edge synthesizer builds realistic ClientHello / ServerHello records so
    synthetic captures carry SNI, cipher suites, ALPN and key_share like a
    real browser or malware implant would;
  * the pcap parser extracts SNI, version, ALPN and a JA3 fingerprint from
    ClientHello records found in TCP payloads.

Only the handshake framing is implemented; everything after the handshake is
opaque "application data" records, which is all a capture shows anyway.
"""
from __future__ import annotations

import hashlib
import random
import struct
from dataclasses import dataclass, field

REC_HANDSHAKE = 0x16
REC_CCS = 0x14
REC_APPDATA = 0x17
HS_CLIENT_HELLO = 0x01
HS_SERVER_HELLO = 0x02

EXT_SNI = 0
EXT_STATUS_REQUEST = 5
EXT_SUPPORTED_GROUPS = 10
EXT_EC_POINT_FORMATS = 11
EXT_SIG_ALGS = 13
EXT_ALPN = 16
EXT_EMS = 23
EXT_SESSION_TICKET = 35
EXT_SUPPORTED_VERSIONS = 43
EXT_PSK_MODES = 45
EXT_KEY_SHARE = 51
EXT_RENEG = 0xFF01

# GREASE values are excluded from JA3 (RFC 8701 pattern 0x?a?a).
def _is_grease(v: int) -> bool:
    return (v & 0x0F0F) == 0x0A0A and ((v >> 8) == (v & 0xFF))


@dataclass
class ClientProfile:
    """A TLS client fingerprint. Cipher/extension order is what JA3 hashes."""
    name: str
    ciphers: list[int]
    extensions: list[int]
    groups: list[int]
    point_formats: list[int] = field(default_factory=lambda: [0])
    alpn: list[str] = field(default_factory=lambda: ["h2", "http/1.1"])
    versions: list[int] = field(default_factory=lambda: [0x0304, 0x0303])
    sig_algs: list[int] = field(default_factory=lambda: [
        0x0403, 0x0804, 0x0401, 0x0503, 0x0805, 0x0501, 0x0806, 0x0601])
    session_id: bool = True


# Representative profiles. Values follow well-known client stacks closely
# enough that the resulting JA3 hashes are distinct per stack.
PROFILES: dict[str, ClientProfile] = {
    "chrome": ClientProfile(
        name="chrome",
        ciphers=[0x1301, 0x1302, 0x1303, 0xC02B, 0xC02F, 0xC02C, 0xC030, 0xCCA9, 0xCCA8,
                 0xC013, 0xC014, 0x009C, 0x009D, 0x002F, 0x0035],
        extensions=[EXT_SNI, EXT_EMS, EXT_RENEG, EXT_SUPPORTED_GROUPS, EXT_EC_POINT_FORMATS,
                    EXT_SESSION_TICKET, EXT_ALPN, EXT_STATUS_REQUEST, EXT_SIG_ALGS,
                    EXT_KEY_SHARE, EXT_PSK_MODES, EXT_SUPPORTED_VERSIONS],
        groups=[0x001D, 0x0017, 0x0018],
    ),
    "firefox": ClientProfile(
        name="firefox",
        ciphers=[0x1301, 0x1303, 0x1302, 0xC02B, 0xC02F, 0xCCA9, 0xCCA8, 0xC02C, 0xC030,
                 0xC00A, 0xC009, 0xC013, 0xC014, 0x009C, 0x009D, 0x002F, 0x0035],
        extensions=[EXT_SNI, EXT_EMS, EXT_RENEG, EXT_SUPPORTED_GROUPS, EXT_EC_POINT_FORMATS,
                    EXT_SESSION_TICKET, EXT_ALPN, EXT_STATUS_REQUEST, EXT_KEY_SHARE,
                    EXT_SUPPORTED_VERSIONS, EXT_SIG_ALGS, EXT_PSK_MODES],
        groups=[0x001D, 0x0017, 0x0018, 0x0019, 0x0100, 0x0101],
    ),
    "schannel": ClientProfile(  # Windows system stack (telemetry, updates)
        name="schannel",
        ciphers=[0x1302, 0x1303, 0x1301, 0xC030, 0xC02F, 0xC028, 0xC027, 0xC014, 0xC013,
                 0x009D, 0x009C, 0x003D, 0x003C, 0x0035, 0x002F],
        extensions=[EXT_SNI, EXT_STATUS_REQUEST, EXT_SUPPORTED_GROUPS, EXT_EC_POINT_FORMATS,
                    EXT_SIG_ALGS, EXT_SESSION_TICKET, EXT_EMS, EXT_SUPPORTED_VERSIONS,
                    EXT_PSK_MODES, EXT_KEY_SHARE],
        groups=[0x001D, 0x0017, 0x0018],
        alpn=["http/1.1"],
    ),
    "openssl": ClientProfile(  # python-requests / curl / most implants
        name="openssl",
        ciphers=[0x1302, 0x1303, 0x1301, 0xC02C, 0xC030, 0x009F, 0xCCA9, 0xCCA8, 0xCCAA,
                 0xC02B, 0xC02F, 0x009E, 0xC024, 0xC028, 0x006B, 0xC023, 0xC027, 0x0067,
                 0xC00A, 0xC014, 0x0039, 0xC009, 0xC013, 0x0033, 0x009D, 0x009C, 0x003D,
                 0x003C, 0x0035, 0x002F, 0x00FF],
        extensions=[EXT_SNI, EXT_EC_POINT_FORMATS, EXT_SUPPORTED_GROUPS, EXT_SESSION_TICKET,
                    EXT_EMS, EXT_SIG_ALGS, EXT_SUPPORTED_VERSIONS, EXT_PSK_MODES, EXT_KEY_SHARE],
        groups=[0x001D, 0x0017, 0x001E, 0x0019, 0x0018],
        alpn=[],
    ),
    "mbedtls": ClientProfile(  # embedded CPE / TR-069 client
        name="mbedtls",
        ciphers=[0xC02B, 0xC02F, 0xC02C, 0xC030, 0xC009, 0xC013, 0xC00A, 0xC014,
                 0x009C, 0x009D, 0x002F, 0x0035],
        extensions=[EXT_SNI, EXT_SUPPORTED_GROUPS, EXT_EC_POINT_FORMATS, EXT_SIG_ALGS, EXT_EMS],
        groups=[0x0017, 0x0018, 0x0019],
        alpn=[],
        versions=[0x0303],
        session_id=False,
    ),
}


def _u8(v: int) -> bytes:
    return struct.pack("!B", v)


def _u16(v: int) -> bytes:
    return struct.pack("!H", v)


def _u24(v: int) -> bytes:
    return struct.pack("!I", v)[1:]


def _ext(kind: int, body: bytes) -> bytes:
    return _u16(kind) + _u16(len(body)) + body


def _record(kind: int, version: int, body: bytes) -> bytes:
    return _u8(kind) + _u16(version) + _u16(len(body)) + body


def build_client_hello(sni: str, profile: ClientProfile, rng: random.Random) -> bytes:
    """A complete TLS record containing a ClientHello for `sni`."""
    body = b""
    for kind in profile.extensions:
        if kind == EXT_SNI:
            name = sni.encode()
            body += _ext(kind, _u16(len(name) + 3) + _u8(0) + _u16(len(name)) + name)
        elif kind == EXT_SUPPORTED_GROUPS:
            g = b"".join(_u16(x) for x in profile.groups)
            body += _ext(kind, _u16(len(g)) + g)
        elif kind == EXT_EC_POINT_FORMATS:
            p = bytes(profile.point_formats)
            body += _ext(kind, _u8(len(p)) + p)
        elif kind == EXT_SIG_ALGS:
            s = b"".join(_u16(x) for x in profile.sig_algs)
            body += _ext(kind, _u16(len(s)) + s)
        elif kind == EXT_ALPN:
            if not profile.alpn:
                continue
            protos = b"".join(_u8(len(a)) + a.encode() for a in profile.alpn)
            body += _ext(kind, _u16(len(protos)) + protos)
        elif kind == EXT_SUPPORTED_VERSIONS:
            v = b"".join(_u16(x) for x in profile.versions)
            body += _ext(kind, _u8(len(v)) + v)
        elif kind == EXT_KEY_SHARE:
            key = bytes(rng.randrange(256) for _ in range(32))
            share = _u16(0x001D) + _u16(32) + key
            body += _ext(kind, _u16(len(share)) + share)
        elif kind == EXT_PSK_MODES:
            body += _ext(kind, _u8(1) + _u8(1))
        elif kind == EXT_STATUS_REQUEST:
            body += _ext(kind, _u8(1) + _u16(0) + _u16(0))
        elif kind == EXT_RENEG:
            body += _ext(kind, _u8(0))
        else:  # EMS, session_ticket: empty
            body += _ext(kind, b"")

    ciphers = b"".join(_u16(c) for c in profile.ciphers)
    session_id = bytes(rng.randrange(256) for _ in range(32)) if profile.session_id else b""
    hello = (
        _u16(0x0303)
        + bytes(rng.randrange(256) for _ in range(32))
        + _u8(len(session_id)) + session_id
        + _u16(len(ciphers)) + ciphers
        + _u8(1) + _u8(0)
        + _u16(len(body)) + body
    )
    hs = _u8(HS_CLIENT_HELLO) + _u24(len(hello)) + hello
    return _record(REC_HANDSHAKE, 0x0301, hs)


def build_server_hello(profile: ClientProfile, rng: random.Random, *, tls13: bool = True) -> bytes:
    """ServerHello (+ ChangeCipherSpec) as sent by a modern server."""
    cipher = 0x1301 if tls13 and 0x1301 in profile.ciphers else 0xC02F
    session_id = bytes(rng.randrange(256) for _ in range(32))
    exts = b""
    if tls13:
        exts += _ext(EXT_SUPPORTED_VERSIONS, _u16(0x0304))
        key = bytes(rng.randrange(256) for _ in range(32))
        exts += _ext(EXT_KEY_SHARE, _u16(0x001D) + _u16(32) + key)
    else:
        exts += _ext(EXT_RENEG, _u8(0))
        exts += _ext(EXT_EMS, b"")
        if profile.alpn:
            a = profile.alpn[0].encode()
            exts += _ext(EXT_ALPN, _u16(len(a) + 1) + _u8(len(a)) + a)
    hello = (
        _u16(0x0303)
        + bytes(rng.randrange(256) for _ in range(32))
        + _u8(len(session_id)) + session_id
        + _u16(cipher) + _u8(0)
        + _u16(len(exts)) + exts
    )
    hs = _u8(HS_SERVER_HELLO) + _u24(len(hello)) + hello
    return _record(REC_HANDSHAKE, 0x0303, hs) + _record(REC_CCS, 0x0303, b"\x01")


def app_data(size: int, rng: random.Random) -> bytes:
    """An opaque TLS application-data record of `size` ciphertext bytes."""
    return _record(REC_APPDATA, 0x0303, bytes(rng.randrange(256) for _ in range(size)))


def change_cipher_spec() -> bytes:
    return _record(REC_CCS, 0x0303, b"\x01")


# --------------------------------------------------------------------------- parse

@dataclass
class ClientHelloInfo:
    version: str
    sni: str
    ciphers: list[int]
    extensions: list[int]
    groups: list[int]
    point_formats: list[int]
    alpn: list[str]
    ja3: str
    ja3_hash: str


_VERSION_NAMES = {0x0301: "TLS 1.0", 0x0302: "TLS 1.1", 0x0303: "TLS 1.2", 0x0304: "TLS 1.3"}


def parse_client_hello(payload: bytes) -> ClientHelloInfo | None:
    """Parse a ClientHello from the start of a TCP payload; None if it isn't one."""
    try:
        if len(payload) < 43 or payload[0] != REC_HANDSHAKE or payload[5] != HS_CLIENT_HELLO:
            return None
        hs_len = int.from_bytes(payload[6:9], "big")
        p = payload[9:9 + hs_len]
        if len(p) < 34:
            return None
        version = int.from_bytes(p[0:2], "big")
        off = 34
        sid_len = p[off]; off += 1 + sid_len
        cs_len = int.from_bytes(p[off:off + 2], "big"); off += 2
        ciphers = [int.from_bytes(p[i:i + 2], "big") for i in range(off, off + cs_len, 2)]
        off += cs_len
        comp_len = p[off]; off += 1 + comp_len
        sni, groups, formats, alpn, exts = "", [], [], [], []
        supported_versions: list[int] = []
        if off + 2 <= len(p):
            ext_len = int.from_bytes(p[off:off + 2], "big"); off += 2
            end = min(len(p), off + ext_len)
            while off + 4 <= end:
                kind = int.from_bytes(p[off:off + 2], "big")
                elen = int.from_bytes(p[off + 2:off + 4], "big")
                body = p[off + 4:off + 4 + elen]
                off += 4 + elen
                exts.append(kind)
                if kind == EXT_SNI and len(body) >= 5:
                    nlen = int.from_bytes(body[3:5], "big")
                    # SNI is sent as A-label (ASCII) bytes; the idna codec
                    # rejects an errors= argument, so decode as plain ASCII.
                    sni = body[5:5 + nlen].decode("ascii", errors="replace")
                elif kind == EXT_SUPPORTED_GROUPS and len(body) >= 2:
                    glen = int.from_bytes(body[0:2], "big")
                    groups = [int.from_bytes(body[i:i + 2], "big") for i in range(2, 2 + glen, 2)]
                elif kind == EXT_EC_POINT_FORMATS and body:
                    formats = list(body[1:1 + body[0]])
                elif kind == EXT_ALPN and len(body) >= 2:
                    i = 2
                    while i < len(body):
                        n = body[i]
                        alpn.append(body[i + 1:i + 1 + n].decode("ascii", errors="replace"))
                        i += 1 + n
                elif kind == EXT_SUPPORTED_VERSIONS and body:
                    supported_versions = [int.from_bytes(body[i:i + 2], "big") for i in range(1, 1 + body[0], 2)]
        ja3_ciphers = [c for c in ciphers if not _is_grease(c)]
        ja3_exts = [e for e in exts if not _is_grease(e)]
        ja3_groups = [g for g in groups if not _is_grease(g)]
        ja3 = ",".join([
            str(version),
            "-".join(map(str, ja3_ciphers)),
            "-".join(map(str, ja3_exts)),
            "-".join(map(str, ja3_groups)),
            "-".join(map(str, formats)),
        ])
        shown = max(supported_versions) if supported_versions else version
        return ClientHelloInfo(
            version=_VERSION_NAMES.get(shown, f"0x{shown:04x}"),
            sni=sni, ciphers=ciphers, extensions=exts, groups=groups, point_formats=formats,
            alpn=alpn, ja3=ja3, ja3_hash=hashlib.md5(ja3.encode()).hexdigest(),
        )
    except Exception:
        return None
