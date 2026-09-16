from pathlib import Path

from portgozu.paths import static_dir
from portgozu.procutil import windows_hidden_kwargs
from portgozu.win_fallback import _port_name

ROOT = Path(__file__).resolve().parents[1]


def test_static_dir_has_index():
    assert (static_dir() / "index.html").is_file()


def test_anka_branding_assets():
    static = static_dir()
    assert (static / "favicon.svg").is_file()
    assert b"ember" in (static / "favicon.svg").read_bytes()
    assert (static / "anka-mark.png").is_file()
    ico = ROOT / "packaging" / "portgozu.ico"
    assert ico.is_file() and ico.stat().st_size > 1024
    assert (ROOT / "packaging" / "anka-icon.png").is_file()


def test_win_port_names():
    assert _port_name(443) == "HTTPS"
    assert _port_name(22) == "SSH"
    assert _port_name(9999) == "TCP"


def test_spec_is_windowed():
    spec = (ROOT / "packaging" / "portgozu.spec").read_text(encoding="utf-8")
    assert "console=False" in spec
    assert "console=True" not in spec


def test_windows_hidden_kwargs_shape():
    import sys

    kwargs = windows_hidden_kwargs()
    if sys.platform == "win32":
        assert "creationflags" in kwargs
        assert kwargs["creationflags"] != 0
        assert "startupinfo" in kwargs
    else:
        assert kwargs == {}


def test_windows_build_bundles_scapy():
    """Packaged EXE must include scapy or LLDP/CDP capture can never run."""
    build = (ROOT / "packaging" / "build-windows.ps1").read_text(encoding="utf-8")
    assert "scapy" in build.lower()
    spec = (ROOT / "packaging" / "portgozu.spec").read_text(encoding="utf-8")
    assert '"scapy"' in spec or "'scapy'" in spec
