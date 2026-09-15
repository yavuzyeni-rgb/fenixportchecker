from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class Neighbor:
    protocol: str
    switch_name: str = ""
    switch_description: str = ""
    port_id: str = ""
    port_description: str = ""
    vlan_id: int | None = None
    mgmt_ips: list[str] = field(default_factory=list)
    ttl: int | None = None
    platform: str = ""
    chassis_id: str = ""

    def as_dict(self) -> dict:
        return {
            "protocol": self.protocol,
            "switch_name": self.switch_name,
            "switch_description": self.switch_description,
            "port_id": self.port_id,
            "port_description": self.port_description,
            "vlan_id": self.vlan_id,
            "mgmt_ips": self.mgmt_ips,
            "ttl": self.ttl,
            "platform": self.platform,
            "chassis_id": self.chassis_id,
        }


def _mac(raw: bytes) -> str:
    return ":".join(f"{b:02x}" for b in raw)


def parse_lldp(payload: bytes) -> Neighbor | None:
    if not payload:
        return None
    nb = Neighbor(protocol="LLDP")
    offset = 0
    found = False
    while offset + 2 <= len(payload):
        header = int.from_bytes(payload[offset : offset + 2], "big")
        kind = header >> 9
        length = header & 0x1FF
        offset += 2
        if kind == 0:
            break
        if offset + length > len(payload):
            break
        value = payload[offset : offset + length]
        offset += length
        found = True
        if kind == 1 and value:
            subtype = value[0]
            rest = value[1:]
            if subtype == 4 and len(rest) >= 6:
                nb.chassis_id = _mac(rest[:6])
            else:
                nb.chassis_id = rest.decode("utf-8", "replace")
        elif kind == 2 and value:
            rest = value[1:] if value[0] in range(1, 8) else value
            nb.port_id = rest.decode("utf-8", "replace").strip("\x00")
        elif kind == 3 and len(value) >= 2:
            nb.ttl = int.from_bytes(value[:2], "big")
        elif kind == 4:
            nb.port_description = value.decode("utf-8", "replace")
        elif kind == 5:
            nb.switch_name = value.decode("utf-8", "replace")
        elif kind == 6:
            nb.switch_description = value.decode("utf-8", "replace")
        elif kind == 8:
            ip = _mgmt_ip(value)
            if ip:
                nb.mgmt_ips.append(ip)
        elif kind == 127 and len(value) >= 4:
            oui = int.from_bytes(value[0:3], "big")
            subtype = value[3]
            data = value[4:]
            if oui == 0x0080C2 and subtype == 1 and len(data) >= 2:
                nb.vlan_id = int.from_bytes(data[:2], "big")
    if not found:
        return None
    if not nb.switch_name and nb.chassis_id:
        nb.switch_name = nb.chassis_id
    return nb


def _mgmt_ip(value: bytes) -> str | None:
    if len(value) < 6:
        return None
    addr_len = value[0]
    if addr_len < 2 or 1 + addr_len > len(value):
        return None
    subtype = value[1]
    addr = value[2 : 1 + addr_len]
    if subtype == 1 and len(addr) >= 4:
        return ".".join(str(b) for b in addr[:4])
    return None
