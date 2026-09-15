"""Salt-okunur SNMPv2c GET. SET yoktur."""

from __future__ import annotations

import random
import socket
from dataclasses import dataclass


@dataclass(slots=True)
class SnmpResult:
    ok: bool
    host: str
    bindings: dict[str, str]
    error: str = ""

    def as_dict(self) -> dict:
        return {
            "ok": self.ok,
            "host": self.host,
            "bindings": self.bindings,
            "error": self.error,
        }


SYS_DESCR = "1.3.6.1.2.1.1.1.0"
SYS_UPTIME = "1.3.6.1.2.1.1.3.0"
SYS_NAME = "1.3.6.1.2.1.1.5.0"


def snmp_get(
    host: str,
    community: str = "public",
    oids: list[str] | None = None,
    port: int = 161,
    timeout: float = 2.0,
) -> SnmpResult:
    host = host.strip()
    if not host:
        return SnmpResult(False, host, {}, "SNMP adresi boş")
    community = (community or "public").encode("ascii", "replace")
    oids = oids or [SYS_NAME, SYS_DESCR, SYS_UPTIME]
    req_id = random.randint(1, 0x7FFFFFFF)
    packet = _build_get(community, req_id, oids)
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(timeout)
        sock.sendto(packet, (host, port))
        data, _addr = sock.recvfrom(4096)
    except OSError as exc:
        return SnmpResult(False, host, {}, f"SNMP yanıtı yok: {exc}")
    finally:
        try:
            sock.close()
        except Exception:
            pass
    try:
        bindings = _parse_response(data)
    except ValueError as exc:
        return SnmpResult(False, host, {}, str(exc))
    return SnmpResult(True, host, bindings)


def _build_get(community: bytes, req_id: int, oids: list[str]) -> bytes:
    varbinds = b"".join(_seq(_oid(o) + _null()) for o in oids)
    pdu_body = _int(req_id) + _int(0) + _int(0) + _seq(varbinds)
    pdu = bytes([0xA0]) + _len(len(pdu_body)) + pdu_body
    body = _int(1) + _octet(community) + pdu  # version 1 = v2c
    return _seq(body)


def _oid(dotted: str) -> bytes:
    parts = [int(x) for x in dotted.split(".")]
    if len(parts) < 2:
        raise ValueError("OID kısa")
    head = 40 * parts[0] + parts[1]
    out = bytearray([head])
    for n in parts[2:]:
        if n < 0:
            raise ValueError("OID negatif")
        stack = [n & 0x7F]
        n >>= 7
        while n:
            stack.append(0x80 | (n & 0x7F))
            n >>= 7
        out.extend(reversed(stack))
    return bytes([0x06]) + _len(len(out)) + bytes(out)


def _parse_response(data: bytes) -> dict[str, str]:
    tag, body, _rest = _read_tlv(data)
    if tag != 0x30:
        raise ValueError("SNMP SEQUENCE değil")
    _ver, rest = _skip(body)
    _comm, rest = _skip(rest)
    tag, pdu, _ = _read_tlv(rest)
    if tag not in (0xA2, 0xA0):  # GetResponse / GetRequest
        raise ValueError(f"beklenmeyen PDU 0x{tag:02x}")
    _rid, rest = _skip(pdu)
    err, rest = _read_int_field(rest)
    _idx, rest = _skip(rest)
    if err:
        raise ValueError(f"SNMP error-status {err}")
    tag, vblist, _ = _read_tlv(rest)
    if tag != 0x30:
        raise ValueError("varbind listesi yok")
    bindings: dict[str, str] = {}
    cursor = vblist
    while cursor:
        tag, vb, cursor = _read_tlv(cursor)
        if tag != 0x30:
            break
        oid_tag, oid_body, after = _read_tlv(vb)
        if oid_tag != 0x06:
            continue
        oid = _decode_oid(oid_body)
        val_tag, val_body, _ = _read_tlv(after)
        bindings[oid] = _decode_value(val_tag, val_body)
    return bindings


def _decode_value(tag: int, body: bytes) -> str:
    if tag in (0x04, 0x44):  # octet / hex
        try:
            text = body.decode("utf-8")
            if text.isprintable() or all(c in "\r\n\t" or c.isprintable() for c in text):
                return text.strip()
        except UnicodeDecodeError:
            pass
        return body.hex()
    if tag == 0x02:
        return str(_decode_int(body))
    if tag == 0x06:
        return _decode_oid(body)
    if tag == 0x43:  # TimeTicks
        return str(_decode_int(body))
    if tag == 0x05:
        return ""
    return f"tag:{tag:02x}:{body.hex()}"


def _decode_oid(body: bytes) -> str:
    if not body:
        return ""
    first = body[0]
    parts = [str(first // 40), str(first % 40)]
    acc = 0
    for b in body[1:]:
        acc = (acc << 7) | (b & 0x7F)
        if not b & 0x80:
            parts.append(str(acc))
            acc = 0
    return ".".join(parts)


def _decode_int(body: bytes) -> int:
    if not body:
        return 0
    val = int.from_bytes(body, "big", signed=False)
    if body[0] & 0x80:
        val -= 1 << (8 * len(body))
    return val


def _read_int_field(data: bytes) -> tuple[int, bytes]:
    tag, body, rest = _read_tlv(data)
    if tag != 0x02:
        raise ValueError("INTEGER bekleniyordu")
    return _decode_int(body), rest


def _skip(data: bytes) -> tuple[bytes, bytes]:
    _tag, body, rest = _read_tlv(data)
    return body, rest


def _read_tlv(data: bytes) -> tuple[int, bytes, bytes]:
    if len(data) < 2:
        raise ValueError("BER kısa")
    tag = data[0]
    length, pos = _read_len(data, 1)
    end = pos + length
    if end > len(data):
        raise ValueError("BER taşması")
    return tag, data[pos:end], data[end:]


def _read_len(data: bytes, pos: int) -> tuple[int, int]:
    first = data[pos]
    if first < 0x80:
        return first, pos + 1
    n = first & 0x7F
    val = int.from_bytes(data[pos + 1 : pos + 1 + n], "big")
    return val, pos + 1 + n


def _seq(body: bytes) -> bytes:
    return bytes([0x30]) + _len(len(body)) + body


def _int(n: int) -> bytes:
    if n == 0:
        body = b"\x00"
    else:
        length = (n.bit_length() + 8) // 8
        body = n.to_bytes(length, "big", signed=True)
        while len(body) > 1 and ((body[0] == 0 and body[1] < 0x80) or (body[0] == 0xFF and body[1] >= 0x80)):
            body = body[1:]
    return bytes([0x02]) + _len(len(body)) + body


def _octet(v: bytes) -> bytes:
    return bytes([0x04]) + _len(len(v)) + v


def _null() -> bytes:
    return b"\x05\x00"


def _len(n: int) -> bytes:
    if n < 0x80:
        return bytes([n])
    body = n.to_bytes((n.bit_length() + 7) // 8, "big")
    return bytes([0x80 | len(body)]) + body
