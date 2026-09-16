from pathlib import Path

from portgozu.paths import static_dir
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
