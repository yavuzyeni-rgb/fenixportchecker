from __future__ import annotations

import platform
import socket
import threading
import time
from collections.abc import Callable

from .frames import DecodedFrame, decode_ethernet


OnFrame = Callable[[bytes, DecodedFrame], None]


def listen_frames(
    adapter_name: str,
    seconds: float,
    on_frame: OnFrame,
    stop_event: threading.Event | None = None,
) -> str | None:
    """Seçilen kartta kare dinle. Başarısızsa kullanıcı notu döner."""
    if seconds <= 0:
        return None
    system = platform.system()
    if system == "Windows":
        return _listen_scapy(adapter_name, seconds, on_frame, stop_event)
    return _listen_afpacket(adapter_name, seconds, on_frame, stop_event) or _listen_scapy(
        adapter_name, seconds, on_frame, stop_event
    )


def _emit(raw: bytes, on_frame: OnFrame) -> None:
    decoded = decode_ethernet(raw)
    if decoded:
        on_frame(raw, decoded)


def _listen_afpacket(
    adapter_name: str,
    seconds: float,
    on_frame: OnFrame,
    stop_event: threading.Event | None,
) -> str | None:
    if not hasattr(socket, "AF_PACKET"):
        return "Bu platformda ham Ethernet soketi yok."
    try:
        sock = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.ntohs(0x0003))
        sock.bind((adapter_name, 0))
        sock.settimeout(0.3)
    except PermissionError:
        return "Ham kare dinlemek için yönetici / root yetkisi gerekir (LLDP/CDP)."
    except OSError as exc:
        return f"Kart açılamadı: {exc}"
    deadline = time.time() + seconds
    try:
        while time.time() < deadline:
            if stop_event and stop_event.is_set():
                break
            try:
                data = sock.recv(65535)
            except socket.timeout:
                continue
            except OSError:
                break
            _emit(data, on_frame)
    finally:
        sock.close()
    return None


def _listen_scapy(
    adapter_name: str,
    seconds: float,
    on_frame: OnFrame,
    stop_event: threading.Event | None,
) -> str | None:
    try:
        from scapy.all import sniff  # type: ignore
    except Exception:
        if platform.system() == "Windows":
            return (
                "LLDP/CDP dinleme motoru (scapy) bu kurulumda yok. "
                "IP, VLAN ve açık TCP bağlantıları yine de çalışır; "
                "L2 komşu için güncel EXE/MSI kullanın ve Npcap kurun."
            )
        return None
    try:
        sniff(
            iface=adapter_name,
            timeout=max(seconds, 0.2),
            store=False,
            prn=lambda pkt: _emit(bytes(pkt), on_frame),
            stop_filter=lambda _pkt: bool(stop_event and stop_event.is_set()),
        )
    except Exception as exc:
        text = str(exc).lower()
        if platform.system() == "Windows" and any(
            tip in text for tip in ("npcap", "winpcap", "no libpcap", "pcap", "permission")
        ):
            return (
                "Kablo üzerindeki LLDP/CDP kareleri için Npcap gerekir "
                "(ve genelde yönetici olarak çalıştırma). "
                "IP, VLAN ve açık TCP bağlantıları Npcap olmadan da çalışır."
            )
        return f"Kare dinleme başarısız: {exc}"
    return None
