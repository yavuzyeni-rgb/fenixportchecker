from __future__ import annotations

import platform
import threading
import time
from datetime import datetime, timezone

from .builders import demo_world
from .capture import listen_frames
from .cdp import parse_cdp
from .frames import DecodedFrame, TrafficStats, classify_payload
from .lldp import Neighbor, parse_lldp
from .nic import Adapter, list_adapters
from .snmp import SnmpResult, snmp_get
from .win_fallback import fill_from_windows_connections


def _now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


class Engine:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.adapters: list[Adapter] = []
        self.selected: str = ""
        self.demo = False
        self.listening = False
        self.notes: list[str] = []
        self.neighbor: Neighbor | None = None
        self.stats = TrafficStats()
        self.local: Adapter | None = None
        self.last_scan: str = ""
        self.snmp: SnmpResult | None = None
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._last_adapter_refresh: float | None = None

    def refresh_adapters(self, *, force: bool = False) -> list[Adapter]:
        # Avoid hammering PowerShell on every /api/state poll when the list is empty.
        now = time.monotonic()
        if (
            not force
            and self._last_adapter_refresh is not None
            and (now - self._last_adapter_refresh) < 20.0
        ):
            with self._lock:
                return list(self.adapters)
        adapters = list_adapters()
        self._last_adapter_refresh = now
        with self._lock:
            self.adapters = adapters
            if not self.selected and adapters:
                up = next((a for a in adapters if a.status.lower() in {"up", "yes"}), adapters[0])
                self.selected = up.name
        return adapters

    def snapshot(self) -> dict:
        with self._lock:
            adapters = [a.as_dict() for a in self.adapters]
            local = self.local.as_dict() if self.local else None
            return {
                "collected_at": self.last_scan or _now(),
                "mode": "demo" if self.demo else "live",
                "listening": self.listening,
                "selected": self.selected,
                "adapters": adapters,
                "local": local,
                "neighbor": self.neighbor.as_dict() if self.neighbor else None,
                "traffic": self.stats.as_dict(),
                "notes": list(self.notes),
                "snmp": self.snmp.as_dict() if self.snmp else None,
            }

    def scan(self, adapter_name: str, demo: bool, seconds: float = 4.0) -> dict:
        self.stop_listen()
        seconds = min(max(seconds, 0.5), 12.0)
        if demo:
            self._load_demo()
            return self.snapshot()

        self.refresh_adapters(force=True)
        adapter = next((a for a in self.adapters if a.name == adapter_name), None)
        notes: list[str] = []
        stats = TrafficStats()
        neighbor: Neighbor | None = None

        def on_frame(_raw: bytes, decoded: DecodedFrame) -> None:
            nonlocal neighbor
            ip = classify_payload(decoded)
            stats.add(decoded, ip)
            if decoded.is_lldp:
                parsed = parse_lldp(decoded.payload)
                if parsed:
                    neighbor = parsed
            elif decoded.is_cdp:
                parsed = parse_cdp(decoded.payload)
                if parsed:
                    neighbor = parsed

        capture_note = listen_frames(adapter_name, seconds, on_frame)
        if capture_note:
            notes.append(capture_note)
            if platform.system() == "Windows" and stats.packets == 0:
                extra = fill_from_windows_connections(stats)
                if extra:
                    notes.append(extra)
        if not neighbor:
            notes.append(
                "LLDP/CDP komşusu yok. Switch’te protokol kapalı olabilir veya "
                "kablo dinlenemedi. IP ve kart VLAN bilgisi yine de yerel ağ yığınından gelir."
            )
        if adapter and not adapter.ipv4:
            notes.append("Bu kartta IPv4 adresi yok. DHCP bekleniyor veya VLAN uyumsuz olabilir.")

        with self._lock:
            self.demo = False
            self.selected = adapter_name
            self.local = adapter
            self.neighbor = neighbor
            self.stats = stats
            self.notes = notes
            self.last_scan = _now()
        return self.snapshot()

    def start_listen(self, adapter_name: str, demo: bool) -> dict:
        self.stop_listen()
        if demo:
            self._load_demo()
            with self._lock:
                self.listening = True
                self.notes.append("Demo'da canlı kablo yok; örnek kareler gösteriliyor.")
            return self.snapshot()
        self._stop = threading.Event()
        self.listening = True
        self.demo = False
        self.selected = adapter_name

        def run() -> None:
            def on_frame(_raw: bytes, decoded: DecodedFrame) -> None:
                ip = classify_payload(decoded)
                with self._lock:
                    self.stats.add(decoded, ip)
                    if decoded.is_lldp:
                        parsed = parse_lldp(decoded.payload)
                        if parsed:
                            self.neighbor = parsed
                    elif decoded.is_cdp:
                        parsed = parse_cdp(decoded.payload)
                        if parsed:
                            self.neighbor = parsed

            note = listen_frames(adapter_name, 300, on_frame, self._stop)
            with self._lock:
                self.listening = False
                if note:
                    self.notes.append(note)

        self._thread = threading.Thread(target=run, daemon=True)
        self._thread.start()
        return self.snapshot()

    def stop_listen(self) -> None:
        self._stop.set()
        thread = self._thread
        if thread and thread.is_alive():
            thread.join(timeout=1.2)
        self.listening = False
        self._thread = None

    def query_snmp(self, host: str, community: str) -> dict:
        result = snmp_get(host, community)
        with self._lock:
            self.snmp = result
            if result.ok:
                name = result.bindings.get("1.3.6.1.2.1.1.5.0")
                if name and not (self.neighbor and self.neighbor.switch_name):
                    self.notes.append(f"SNMP sysName: {name}")
            else:
                self.notes.append(result.error)
        return result.as_dict()

    def _load_demo(self) -> None:
        world = demo_world()
        stats = TrafficStats()
        neighbor: Neighbor | None = None
        from .frames import decode_ethernet

        for raw in world.frames:
            decoded = decode_ethernet(raw)
            if not decoded:
                continue
            stats.add(decoded, classify_payload(decoded))
            if decoded.is_lldp:
                neighbor = parse_lldp(decoded.payload) or neighbor
            elif decoded.is_cdp and neighbor is None:
                neighbor = parse_cdp(decoded.payload)

        adapter = Adapter(
            name="Ethernet (Demo)",
            description="Örnek kat-3 kullanıcı portu",
            mac="a4:bb:6d:77:88:99",
            status="Up",
            speed="1 Gb/s",
            vlan_id=world.vlan,
            ipv4=[f"{world.pc_ip}/24"],
            gateway=world.gateway,
            dhcp="DHCP",
            dns=["10.12.1.2", "1.1.1.1"],
        )
        with self._lock:
            self.demo = True
            self.selected = adapter.name
            self.adapters = [adapter]
            self.local = adapter
            self.neighbor = neighbor
            self.stats = stats
            self.last_scan = _now()
            self.notes = [
                "Demo modu: gerçek kablo yok. Sahada Demo’yu kapatıp kendi kartınızı tarayın.",
                "Örnek switch LLDP ile Gi1/0/24 ve VLAN 120 ilan ediyor.",
            ]
            self.listening = False
            self.snmp = None
