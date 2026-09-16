"""Npcap olmadan Windows’ta IP dışı ek bilgi: açık TCP bağlantıları."""

from __future__ import annotations

import json
import subprocess

from .frames import TrafficStats
from .procutil import powershell_hidden


def fill_from_windows_connections(stats: TrafficStats) -> str | None:
    script = r"""
$ErrorActionPreference = 'SilentlyContinue'
Get-NetTCPConnection -State Established,Listen |
  Select-Object State, LocalAddress, RemoteAddress, RemotePort |
  ConvertTo-Json -Compress
"""
    try:
        proc = powershell_hidden(script, timeout=12)
    except (OSError, subprocess.TimeoutExpired):
        return None
    raw = (proc.stdout or "").strip()
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if isinstance(data, dict):
        data = [data]
    count = 0
    for row in data:
        remote = str(row.get("RemoteAddress") or "")
        port = int(row.get("RemotePort") or 0)
        local = str(row.get("LocalAddress") or "")
        proto = _port_name(port)
        stats.packets += 1
        stats.by_proto[proto] = stats.by_proto.get(proto, 0) + 1
        key = remote if remote and remote not in {"0.0.0.0", "::", "::1"} else local
        if key:
            stats.talkers[key] = stats.talkers.get(key, 0) + 1
        stats.recent.append(
            {
                "src_mac": local or "—",
                "dst_mac": f"{remote}:{port}" if remote else "—",
                "vlans": [],
                "proto": proto,
                "summary": f"{row.get('State')} {local} → {remote}:{port}",
                "bytes": 0,
            }
        )
        count += 1
        if count >= 40:
            break
    if len(stats.recent) > 80:
        stats.recent = stats.recent[-80:]
    return f"Npcap yok; {count} açık TCP bağlantısı gösterildi (L2/LLDP değil)."


def _port_name(port: int) -> str:
    return {
        443: "HTTPS",
        80: "HTTP",
        22: "SSH",
        3389: "RDP",
        53: "DNS",
        67: "DHCP",
        68: "DHCP",
        161: "SNMP",
        123: "NTP",
        445: "SMB",
        135: "RPC",
        25: "SMTP",
        587: "SMTP",
        993: "IMAPS",
        8080: "HTTP",
        8443: "HTTPS",
    }.get(port, "TCP")
