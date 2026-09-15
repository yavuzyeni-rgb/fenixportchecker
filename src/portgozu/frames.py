from __future__ import annotations

from dataclasses import dataclass, field


def mac_str(raw: bytes) -> str:
    return ":".join(f"{b:02x}" for b in raw)


def parse_mac(text: str) -> bytes:
    hexed = text.replace(":", "").replace("-", "").replace(".", "").strip()
    if len(hexed) != 12:
        raise ValueError(f"geçersiz MAC: {text}")
    return bytes.fromhex(hexed)


@dataclass(slots=True)
class DecodedFrame:
    dst_mac: str
    src_mac: str
    ethertype: int
    vlan_ids: list[int]
    payload: bytes
    length: int
    llc_snap: bool = False
    snap_oui: int = 0
    snap_type: int = 0

    @property
    def is_lldp(self) -> bool:
        return self.ethertype == 0x88CC

    @property
    def is_cdp(self) -> bool:
        return self.llc_snap and self.snap_oui == 0x00000C and self.snap_type == 0x2000

    @property
    def is_arp(self) -> bool:
        return self.ethertype == 0x0806

    @property
    def is_ipv4(self) -> bool:
        return self.ethertype == 0x0800

    @property
    def is_ipv6(self) -> bool:
        return self.ethertype == 0x86DD


def decode_ethernet(frame: bytes) -> DecodedFrame | None:
    """Ethernet II, 802.1Q / QinQ ve Cisco CDP SNAP karelerini çözer."""
    if len(frame) < 14:
        return None
    dst = mac_str(frame[0:6])
    src = mac_str(frame[6:12])
    offset = 12
    vlans: list[int] = []
    ethertype = int.from_bytes(frame[offset : offset + 2], "big")
    offset += 2

    # 802.1Q (0x8100) ve QinQ (0x88a8 / 0x9100)
    while ethertype in (0x8100, 0x88A8, 0x9100) and offset + 4 <= len(frame):
        tci = int.from_bytes(frame[offset : offset + 2], "big")
        vlans.append(tci & 0x0FFF)
        ethertype = int.from_bytes(frame[offset + 2 : offset + 4], "big")
        offset += 4

    llc_snap = False
    snap_oui = 0
    snap_type = 0
    payload = frame[offset:]

    # 802.3 length + LLC/SNAP (CDP)
    if ethertype <= 1500 and len(payload) >= 8:
        dsap, ssap, ctrl = payload[0], payload[1], payload[2]
        if dsap == 0xAA and ssap == 0xAA and ctrl == 0x03:
            llc_snap = True
            snap_oui = int.from_bytes(payload[3:6], "big")
            snap_type = int.from_bytes(payload[6:8], "big")
            payload = payload[8:]
            ethertype = snap_type

    return DecodedFrame(
        dst_mac=dst,
        src_mac=src,
        ethertype=ethertype,
        vlan_ids=vlans,
        payload=payload,
        length=len(frame),
        llc_snap=llc_snap,
        snap_oui=snap_oui,
        snap_type=snap_type,
    )


@dataclass(slots=True)
class IpInfo:
    src: str | None = None
    dst: str | None = None
    proto: str = "other"
    l4_src: int | None = None
    l4_dst: int | None = None
    summary: str = ""


def _ipv4(n: bytes) -> str:
    return ".".join(str(b) for b in n)


def classify_payload(decoded: DecodedFrame) -> IpInfo:
    info = IpInfo()
    if decoded.is_arp and len(decoded.payload) >= 28:
        op = int.from_bytes(decoded.payload[6:8], "big")
        sha = mac_str(decoded.payload[8:14])
        spa = _ipv4(decoded.payload[14:18])
        tpa = _ipv4(decoded.payload[24:28])
        info.src = spa
        info.dst = tpa
        info.proto = "ARP"
        info.summary = f"{'istek' if op == 1 else 'yanıt'} {spa} → {tpa} ({sha})"
        return info

    if decoded.is_lldp:
        info.proto = "LLDP"
        info.summary = "LLDP komşu ilanı"
        return info

    if decoded.is_cdp:
        info.proto = "CDP"
        info.summary = "CDP komşu ilanı"
        return info

    if decoded.is_ipv4 and len(decoded.payload) >= 20:
        ihl = (decoded.payload[0] & 0x0F) * 4
        proto = decoded.payload[9]
        info.src = _ipv4(decoded.payload[12:16])
        info.dst = _ipv4(decoded.payload[16:20])
        body = decoded.payload[ihl:]
        if proto == 1:
            info.proto = "ICMP"
            info.summary = f"ICMP {info.src} → {info.dst}"
            return info
        if proto == 6 and len(body) >= 4:
            info.l4_src = int.from_bytes(body[0:2], "big")
            info.l4_dst = int.from_bytes(body[2:4], "big")
            info.proto = _tcp_name(info.l4_src, info.l4_dst)
            info.summary = f"TCP {info.src}:{info.l4_src} → {info.dst}:{info.l4_dst}"
            return info
        if proto == 17 and len(body) >= 4:
            info.l4_src = int.from_bytes(body[0:2], "big")
            info.l4_dst = int.from_bytes(body[2:4], "big")
            info.proto = _udp_name(info.l4_src, info.l4_dst)
            info.summary = f"UDP {info.src}:{info.l4_src} → {info.dst}:{info.l4_dst}"
            return info
        info.proto = f"IPv4/{proto}"
        info.summary = f"IPv4 {info.src} → {info.dst}"
        return info

    if decoded.is_ipv6:
        info.proto = "IPv6"
        info.summary = "IPv6 karesi"
        return info

    info.summary = f"ethertype 0x{decoded.ethertype:04x}"
    return info


def _tcp_name(src: int, dst: int) -> str:
    ports = {src, dst}
    if 443 in ports:
        return "HTTPS"
    if 80 in ports:
        return "HTTP"
    if 22 in ports:
        return "SSH"
    if 3389 in ports:
        return "RDP"
    return "TCP"


def _udp_name(src: int, dst: int) -> str:
    ports = {src, dst}
    if ports & {67, 68}:
        return "DHCP"
    if 53 in ports:
        return "DNS"
    if 5353 in ports:
        return "mDNS"
    if 161 in ports:
        return "SNMP"
    if 123 in ports:
        return "NTP"
    return "UDP"


@dataclass(slots=True)
class TrafficStats:
    packets: int = 0
    bytes: int = 0
    by_proto: dict[str, int] = field(default_factory=dict)
    vlans: dict[int, int] = field(default_factory=dict)
    talkers: dict[str, int] = field(default_factory=dict)
    recent: list[dict] = field(default_factory=list)

    def add(self, decoded: DecodedFrame, ip: IpInfo) -> None:
        self.packets += 1
        self.bytes += decoded.length
        self.by_proto[ip.proto] = self.by_proto.get(ip.proto, 0) + 1
        for vlan in decoded.vlan_ids:
            self.vlans[vlan] = self.vlans.get(vlan, 0) + 1
        key = ip.src or decoded.src_mac
        self.talkers[key] = self.talkers.get(key, 0) + 1
        row = {
            "src_mac": decoded.src_mac,
            "dst_mac": decoded.dst_mac,
            "vlans": decoded.vlan_ids,
            "proto": ip.proto,
            "summary": ip.summary,
            "bytes": decoded.length,
        }
        self.recent.append(row)
        if len(self.recent) > 80:
            self.recent = self.recent[-80:]

    def as_dict(self) -> dict:
        top = sorted(self.talkers.items(), key=lambda kv: kv[1], reverse=True)[:8]
        return {
            "packets": self.packets,
            "bytes": self.bytes,
            "by_proto": dict(sorted(self.by_proto.items(), key=lambda kv: kv[1], reverse=True)),
            "vlans": {str(k): v for k, v in sorted(self.vlans.items())},
            "talkers": [{"addr": a, "packets": n} for a, n in top],
            "recent": list(reversed(self.recent[-25:])),
        }
