from fastapi.testclient import TestClient

from portgozu.app import app, engine
from portgozu.engine import Engine


def test_demo_scan_fills_neighbor_and_ip():
    engine.__dict__.update(Engine().__dict__)
    client = TestClient(app)
    res = client.post("/api/scan", json={"adapter": "", "demo": True, "seconds": 1})
    assert res.status_code == 200
    data = res.json()
    assert data["mode"] == "demo"
    assert data["neighbor"]["switch_name"] == "SW-KAT3-01"
    assert data["neighbor"]["port_id"] == "GigabitEthernet1/0/24"
    assert data["neighbor"]["vlan_id"] == 120
    assert data["local"]["ipv4"][0].startswith("10.12.120.45")
    assert data["traffic"]["packets"] >= 5
    assert "DHCP" in data["traffic"]["by_proto"]
    assert "120" in data["traffic"]["vlans"]


def test_state_endpoint():
    client = TestClient(app)
    res = client.get("/api/state")
    assert res.status_code == 200
    body = res.json()
    assert "adapters" in body
    assert "traffic" in body


def test_index_serves_ui():
    client = TestClient(app)
    res = client.get("/")
    assert res.status_code == 200
    assert "FenixPortChecker" in res.text
    assert "Portu Tara" in res.text


def test_demo_listen_stays_on():
    client = TestClient(app)
    res = client.post("/api/listen", json={"adapter": "", "demo": True, "on": True})
    assert res.status_code == 200
    data = res.json()
    assert data["listening"] is True
    assert data["neighbor"]["switch_name"] == "SW-KAT3-01"
