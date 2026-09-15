from portgozu.paths import static_dir
from portgozu.win_fallback import _port_name


def test_static_dir_has_index():
    assert (static_dir() / "index.html").is_file()


def test_win_port_names():
    assert _port_name(443) == "HTTPS"
    assert _port_name(22) == "SSH"
    assert _port_name(9999) == "TCP"
