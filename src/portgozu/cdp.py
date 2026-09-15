from __future__ import annotations

from .lldp import Neighbor


def parse_cdp(payload: bytes) -> Neighbor | None:
    if len(payload) < 4:
        return None
    ttl = payload[1]
    offset = 4
    nb = Neighbor(protocol="CDP", ttl=ttl)
    found = False
    while offset + 4 <= len(payload):
        kind = int.from_bytes(payload[offset : offset + 2], "big")
        length = int.from_bytes(payload[offset + 2 : offset + 4], "big")
        if length < 4 or offset + length > len(payload):
            break
        value = payload[offset + 4 : offset + length]
        offset += length
        found = True
        if kind == 0x0001:
            nb.switch_name = value.decode("utf-8", "replace")
        elif kind == 0x0002:
            ip = _cdp_address(value)
            if ip:
                nb.mgmt_ips.append(ip)
        elif kind == 0x0003:
            nb.port_id = value.decode("utf-8", "replace")
        elif kind == 0x0005:
            nb.switch_description = value.decode("utf-8", "replace")
        elif kind == 0x0006:
            nb.platform = value.decode("utf-8", "replace")
        elif kind == 0x000A and len(value) >= 2:
            nb.vlan_id = int.from_bytes(value[:2], "big")
    return nb if found else None


def _cdp_address(value: bytes) -> str | None:
    if len(value) < 8:
        return None
    count = int.from_bytes(value[0:4], "big")
    if count < 1:
        return None
    pos = 4
    proto_type = value[pos]
    proto_len = value[pos + 1]
    pos += 2
    if pos + proto_len + 2 > len(value):
        return None
    pos += proto_len
    addr_len = int.from_bytes(value[pos : pos + 2], "big")
    pos += 2
    addr = value[pos : pos + addr_len]
    if proto_type == 1 and addr_len >= 4:
        return ".".join(str(b) for b in addr[:4])
    return None
