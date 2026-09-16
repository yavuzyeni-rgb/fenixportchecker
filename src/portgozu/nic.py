from __future__ import annotations

import json
import platform
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from .procutil import powershell_hidden, run_hidden


@dataclass(slots=True)
class Adapter:
    name: str
    description: str = ""
    mac: str = ""
    status: str = ""
    speed: str = ""
    vlan_id: int | None = None
    ipv4: list[str] = field(default_factory=list)
    gateway: str = ""
    dhcp: str = ""
    dns: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "mac": self.mac,
            "status": self.status,
            "speed": self.speed,
            "vlan_id": self.vlan_id,
            "ipv4": self.ipv4,
            "gateway": self.gateway,
            "dhcp": self.dhcp,
            "dns": self.dns,
        }


def list_adapters() -> list[Adapter]:
    system = platform.system()
    if system == "Windows":
        found = _windows_adapters()
        if found:
            return found
    if system != "Windows":
        found = _linux_adapters()
        if found:
            return found
    return []


def _windows_adapters() -> list[Adapter]:
    script = r"""
$ErrorActionPreference = 'SilentlyContinue'
$adapters = @()
Get-NetAdapter | ForEach-Object {
  $cfg = Get-NetIPConfiguration -InterfaceIndex $_.ifIndex
  $addrs = @()
  foreach ($a in $cfg.IPv4Address) {
    if ($a.IPAddress) { $addrs += ($a.IPAddress + '/' + $a.PrefixLength) }
  }
  $gw = ''
  if ($cfg.IPv4DefaultGateway) { $gw = $cfg.IPv4DefaultGateway.NextHop }
  $dns = @()
  foreach ($d in $cfg.DNSServer) { if ($d.ServerAddresses) { $dns += $d.ServerAddresses } }
  $vlan = $null
  if ($_.VlanID -and $_.VlanID -gt 0) { $vlan = [int]$_.VlanID }
  $adapters += [ordered]@{
    name = $_.Name
    description = $_.InterfaceDescription
    mac = $_.MacAddress
    status = [string]$_.Status
    speed = [string]$_.LinkSpeed
    vlan_id = $vlan
    ipv4 = $addrs
    gateway = $gw
    dhcp = if ($cfg.NetIPv4Interface.Dhcp -eq 'Enabled') { 'DHCP' } else { 'Statik' }
    dns = $dns
  }
}
$adapters | ConvertTo-Json -Depth 5 -Compress
"""
    try:
        proc = powershell_hidden(script, timeout=20)
    except (OSError, subprocess.TimeoutExpired):
        return []
    raw = (proc.stdout or "").strip()
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if isinstance(data, dict):
        data = [data]
    out: list[Adapter] = []
    for row in data:
        mac = str(row.get("mac") or "").replace("-", ":").lower()
        vlan = row.get("vlan_id")
        try:
            vlan_id = int(vlan) if vlan not in (None, "", 0, "0") else None
        except (TypeError, ValueError):
            vlan_id = None
        dns = row.get("dns") or []
        if isinstance(dns, str):
            dns = [dns]
        flat_dns: list[str] = []
        for item in dns:
            if isinstance(item, list):
                flat_dns.extend(str(x) for x in item)
            elif item:
                flat_dns.append(str(item))
        out.append(
            Adapter(
                name=str(row.get("name") or ""),
                description=str(row.get("description") or ""),
                mac=mac,
                status=str(row.get("status") or ""),
                speed=str(row.get("speed") or ""),
                vlan_id=vlan_id,
                ipv4=list(row.get("ipv4") or []),
                gateway=str(row.get("gateway") or ""),
                dhcp=str(row.get("dhcp") or ""),
                dns=flat_dns,
            )
        )
    return [a for a in out if a.name]


def _linux_adapters() -> list[Adapter]:
    net = Path("/sys/class/net")
    if not net.exists():
        return []
    ip_map = _linux_ip_addr()
    gw_map, dns = _linux_routes_dns()
    out: list[Adapter] = []
    for path in sorted(net.iterdir()):
        name = path.name
        if name == "lo":
            continue
        mac = _read(path / "address").lower()
        oper = _read(path / "operstate")
        speed = _read(path / "speed")
        speed_s = f"{speed} Mb/s" if speed.isdigit() else ""
        vlan = _linux_vlan(name)
        info = ip_map.get(name, {})
        out.append(
            Adapter(
                name=name,
                description=name,
                mac=mac,
                status=oper or "unknown",
                speed=speed_s,
                vlan_id=vlan,
                ipv4=info.get("ipv4") or [],
                gateway=gw_map.get(name, ""),
                dhcp=_linux_dhcp_guess(name, info.get("ipv4") or []),
                dns=dns,
            )
        )
    return out


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def _linux_vlan(name: str) -> int | None:
    m = re.search(r"\.(\d+)$", name)
    if m:
        return int(m.group(1))
    raw = _read(Path("/proc/net/vlan") / name)
    if not raw:
        return None
    m = re.search(r"VID:\s*(\d+)", raw)
    return int(m.group(1)) if m else None


def _linux_ip_addr() -> dict[str, dict]:
    try:
        proc = run_hidden(
            ["ip", "-j", "addr"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            data = json.loads(proc.stdout)
            result: dict[str, dict] = {}
            for item in data:
                addrs = []
                for a in item.get("addr_info") or []:
                    if a.get("family") == "inet":
                        addrs.append(f"{a.get('local')}/{a.get('prefixlen')}")
                result[item.get("ifname", "")] = {"ipv4": addrs}
            return result
    except (OSError, json.JSONDecodeError, subprocess.TimeoutExpired):
        pass
    return {}


def _linux_routes_dns() -> tuple[dict[str, str], list[str]]:
    gw: dict[str, str] = {}
    try:
        proc = run_hidden(
            ["ip", "-j", "route"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            for item in json.loads(proc.stdout):
                if item.get("dst") == "default" and item.get("gateway") and item.get("dev"):
                    gw[item["dev"]] = item["gateway"]
    except (OSError, json.JSONDecodeError, subprocess.TimeoutExpired):
        pass
    dns: list[str] = []
    resolv = Path("/etc/resolv.conf")
    if resolv.exists():
        for line in resolv.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith("nameserver"):
                parts = line.split()
                if len(parts) >= 2:
                    dns.append(parts[1])
    return gw, dns


def _linux_dhcp_guess(name: str, addrs: list[str]) -> str:
    if Path(f"/var/lib/dhcp/dhclient.{name}.leases").exists():
        return "DHCP"
    return ""
