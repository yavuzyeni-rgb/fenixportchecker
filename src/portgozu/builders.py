from __future__ import annotations

from dataclasses import dataclass, field


def _tlv(kind: int, value: bytes) -> bytes:
    n = len(value)
    if kind > 127 or n > 511:
        raise ValueError("LLDP TLV çok büyük")
    header = (kind << 9) | n
    return header.to_bytes(2, "big") + value


def build_lldp_payload(
    *,
    chassis_mac: bytes,
    port_id: str,
    ttl: int = 120,
    system_name: str = "",
    port_desc: str = "",
    system_desc: str = "",
    vlan_id: int | None = None,
    mgmt_ip: str | None = None,
) -> bytes:
    parts = [
        _tlv(1, bytes([4]) + chassis_mac),  # chassis MAC
        _tlv(2, bytes([5]) + port_id.encode("ascii", "replace")),  # interface name
        _tlv(3, ttl.to_bytes(2, "big")),
    ]
    if port_desc:
        parts.append(_tlv(4, port_desc.encode("utf-8", "replace")))
    if system_name:
        parts.append(_tlv(5, system_name.encode("utf-8", "replace")))
    if system_desc:
        parts.append(_tlv(6, system_desc.encode("utf-8", "replace")))
    if mgmt_ip:
        ip = bytes(int(x) for x in mgmt_ip.split("."))
        # subtype 1 = IPv4, ifIndex, no OID
        mgmt = bytes([5, 1]) + ip + bytes([1, 0, 0, 0, 0, 0])
        parts.append(_tlv(8, mgmt))
    if vlan_id is not None:
        # IEEE 802.1 Organizationally Specific: Port VLAN ID
        parts.append(_tlv(127, bytes.fromhex("0080c2") + bytes([1]) + vlan_id.to_bytes(2, "big")))
    parts.append(_tlv(0, b""))
    return b"".join(parts)


def ethernet_ii(dst: bytes, src: bytes, ethertype: int, payload: bytes, vlan: int | None = None) -> bytes:
    head = dst + src
    if vlan is not None:
        head += bytes.fromhex("8100") + vlan.to_bytes(2, "big")
    return head + ethertype.to_bytes(2, "big") + payload


def build_lldp_frame(**kwargs) -> bytes:
    chassis = kwargs.pop("chassis_mac")
    src = kwargs.pop("src_mac", chassis)
    vlan = kwargs.pop("outer_vlan", None)
    payload = build_lldp_payload(chassis_mac=chassis, **kwargs)
    dst = bytes.fromhex("0180c200000e")
    return ethernet_ii(dst, src, 0x88CC, payload, vlan=vlan)


def _cdp_tlv(kind: int, value: bytes) -> bytes:
    length = 4 + len(value)
    return kind.to_bytes(2, "big") + length.to_bytes(2, "big") + value


def build_cdp_payload(
    *,
    device_id: str,
    port_id: str,
    platform: str = "cisco WS-C2960",
    native_vlan: int | None = 120,
    version: str = "Cisco IOS",
    mgmt_ip: str | None = None,
) -> bytes:
    body = b"".join(
        [
            _cdp_tlv(0x0001, device_id.encode("ascii", "replace")),
            _cdp_tlv(0x0003, port_id.encode("ascii", "replace")),
            _cdp_tlv(0x0005, version.encode("ascii", "replace")),
            _cdp_tlv(0x0006, platform.encode("ascii", "replace")),
        ]
    )
    if native_vlan is not None:
        body += _cdp_tlv(0x000A, native_vlan.to_bytes(2, "big"))
    if mgmt_ip:
        ip = bytes(int(x) for x in mgmt_ip.split("."))
        # 1 address, NLPID, proto 0xcc (IP)
        addr = (1).to_bytes(4, "big") + bytes([1, 1, 0xCC]) + (4).to_bytes(2, "big") + ip
        body += _cdp_tlv(0x0002, addr)
    header = bytes([2, 180]) + b"\x00\x00"  # version, ttl, checksum placeholder
    return header + body


def build_cdp_frame(
    *,
    src_mac: bytes,
    device_id: str,
    port_id: str,
    **kwargs,
) -> bytes:
    payload = build_cdp_payload(device_id=device_id, port_id=port_id, **kwargs)
    dst = bytes.fromhex("01000ccccccc")
    llc = bytes.fromhex("aaaa0300000c2000")
    length = len(llc) + len(payload)
    return dst + src_mac + length.to_bytes(2, "big") + llc + payload


def build_ipv4_udp_frame(
    *,
    src_mac: bytes,
    dst_mac: bytes,
    src_ip: str,
    dst_ip: str,
    src_port: int,
    dst_port: int,
    vlan: int | None = None,
) -> bytes:
    sip = bytes(int(x) for x in src_ip.split("."))
    dip = bytes(int(x) for x in dst_ip.split("."))
    udp = src_port.to_bytes(2, "big") + dst_port.to_bytes(2, "big") + (8).to_bytes(2, "big") + b"\x00\x00"
    total = 20 + len(udp)
    iph = bytearray(20)
    iph[0] = 0x45
    iph[2:4] = total.to_bytes(2, "big")
    iph[8] = 64
    iph[9] = 17
    iph[12:16] = sip
    iph[16:20] = dip
    return ethernet_ii(dst_mac, src_mac, 0x0800, bytes(iph) + udp, vlan=vlan)


def build_ipv4_tcp_frame(
    *,
    src_mac: bytes,
    dst_mac: bytes,
    src_ip: str,
    dst_ip: str,
    src_port: int,
    dst_port: int,
    vlan: int | None = None,
) -> bytes:
    sip = bytes(int(x) for x in src_ip.split("."))
    dip = bytes(int(x) for x in dst_ip.split("."))
    tcp = bytearray(20)
    tcp[0:2] = src_port.to_bytes(2, "big")
    tcp[2:4] = dst_port.to_bytes(2, "big")
    tcp[12] = 0x50  # header length 20, flags 0
    tcp[13] = 0x02  # SYN
    tcp[14:16] = (64240).to_bytes(2, "big")
    total = 20 + len(tcp)
    iph = bytearray(20)
    iph[0] = 0x45
    iph[2:4] = total.to_bytes(2, "big")
    iph[8] = 64
    iph[9] = 6
    iph[12:16] = sip
    iph[16:20] = dip
    return ethernet_ii(dst_mac, src_mac, 0x0800, bytes(iph) + bytes(tcp), vlan=vlan)


def build_arp_frame(
    *,
    src_mac: bytes,
    src_ip: str,
    target_ip: str,
    vlan: int | None = None,
) -> bytes:
    sip = bytes(int(x) for x in src_ip.split("."))
    tip = bytes(int(x) for x in target_ip.split("."))
    payload = (
        bytes.fromhex("0001080006040001")
        + src_mac
        + sip
        + bytes(6)
        + tip
    )
    return ethernet_ii(bytes.fromhex("ffffffffffff"), src_mac, 0x0806, payload, vlan=vlan)


@dataclass(slots=True)
class DemoWorld:
    switch_name: str = "SW-KAT3-01"
    port_id: str = "GigabitEthernet1/0/24"
    vlan: int = 120
    mgmt_ip: str = "10.12.1.10"
    pc_ip: str = "10.12.120.45"
    gateway: str = "10.12.120.1"
    frames: list[bytes] = field(default_factory=list)


def demo_world() -> DemoWorld:
    sw_mac = bytes.fromhex("00e0fc001122")
    pc_mac = bytes.fromhex("a4bb6d778899")
    gw_mac = bytes.fromhex("00000c334455")
    world = DemoWorld()
    world.frames = [
        build_lldp_frame(
            chassis_mac=sw_mac,
            port_id=world.port_id,
            system_name=world.switch_name,
            port_desc="Kullanıcı-PC / VLAN 120",
            system_desc="Cisco IOS Software, C2960X",
            vlan_id=world.vlan,
            mgmt_ip=world.mgmt_ip,
        ),
        build_cdp_frame(
            src_mac=sw_mac,
            device_id=world.switch_name,
            port_id=world.port_id,
            native_vlan=world.vlan,
            mgmt_ip=world.mgmt_ip,
        ),
        build_arp_frame(src_mac=pc_mac, src_ip=world.pc_ip, target_ip=world.gateway, vlan=world.vlan),
        build_ipv4_udp_frame(
            src_mac=pc_mac,
            dst_mac=gw_mac,
            src_ip=world.pc_ip,
            dst_ip="8.8.8.8",
            src_port=53531,
            dst_port=53,
            vlan=world.vlan,
        ),
        build_ipv4_udp_frame(
            src_mac=pc_mac,
            dst_mac=bytes.fromhex("ffffffffffff"),
            src_ip=world.pc_ip,
            dst_ip="255.255.255.255",
            src_port=68,
            dst_port=67,
            vlan=world.vlan,
        ),
        build_ipv4_udp_frame(
            src_mac=bytes.fromhex("b827eb112233"),
            dst_mac=bytes.fromhex("ffffffffffff"),
            src_ip="10.12.120.88",
            dst_ip="224.0.0.251",
            src_port=5353,
            dst_port=5353,
            vlan=world.vlan,
        ),
        build_ipv4_tcp_frame(
            src_mac=bytes.fromhex("001122aabbcc"),
            dst_mac=gw_mac,
            src_ip="10.12.130.20",
            dst_ip="1.1.1.1",
            src_port=51234,
            dst_port=443,
            vlan=130,
        ),
    ]
    return world
