from portgozu.builders import build_cdp_frame, build_lldp_frame, demo_world
from portgozu.cdp import parse_cdp
from portgozu.frames import classify_payload, decode_ethernet
from portgozu.lldp import parse_lldp


def test_vlan_and_qinq():
    payload = bytes(20)
    src = bytes.fromhex("001122334455")
    dst = bytes.fromhex("ffffffffffff")
    tagged = dst + src + bytes.fromhex("8100") + (120).to_bytes(2, "big") + bytes.fromhex("0800") + payload
    decoded = decode_ethernet(tagged)
    assert decoded is not None
    assert decoded.vlan_ids == [120]
    assert decoded.ethertype == 0x0800

    qinq = (
        dst
        + src
        + bytes.fromhex("88a8")
        + (100).to_bytes(2, "big")
        + bytes.fromhex("8100")
        + (200).to_bytes(2, "big")
        + bytes.fromhex("0800")
        + payload
    )
    decoded = decode_ethernet(qinq)
    assert decoded is not None
    assert decoded.vlan_ids == [100, 200]


def test_lldp_neighbor():
    frame = build_lldp_frame(
        chassis_mac=bytes.fromhex("00e0fc001122"),
        port_id="Gi1/0/24",
        system_name="SW-KAT3-01",
        port_desc="PC",
        vlan_id=120,
        mgmt_ip="10.12.1.10",
    )
    decoded = decode_ethernet(frame)
    assert decoded and decoded.is_lldp
    nb = parse_lldp(decoded.payload)
    assert nb is not None
    assert nb.switch_name == "SW-KAT3-01"
    assert nb.port_id == "Gi1/0/24"
    assert nb.vlan_id == 120
    assert "10.12.1.10" in nb.mgmt_ips


def test_cdp_neighbor():
    frame = build_cdp_frame(
        src_mac=bytes.fromhex("00e0fc001122"),
        device_id="SW-KAT3-01",
        port_id="GigabitEthernet1/0/24",
        native_vlan=120,
        mgmt_ip="10.12.1.10",
        platform="cisco WS-C2960",
    )
    decoded = decode_ethernet(frame)
    assert decoded and decoded.is_cdp
    nb = parse_cdp(decoded.payload)
    assert nb is not None
    assert nb.switch_name == "SW-KAT3-01"
    assert nb.port_id == "GigabitEthernet1/0/24"
    assert nb.vlan_id == 120
    assert "10.12.1.10" in nb.mgmt_ips
    assert nb.platform.startswith("cisco")


def test_demo_world_has_dhcp_and_dns():
    world = demo_world()
    protos = set()
    vlans = set()
    for raw in world.frames:
        decoded = decode_ethernet(raw)
        assert decoded
        vlans.update(decoded.vlan_ids)
        protos.add(classify_payload(decoded).proto)
    assert "LLDP" in protos
    assert "CDP" in protos
    assert "ARP" in protos
    assert "DHCP" in protos
    assert "DNS" in protos
    assert "HTTPS" in protos
    assert 120 in vlans
    assert 130 in vlans
