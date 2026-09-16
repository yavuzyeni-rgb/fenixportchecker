from __future__ import annotations

import argparse
import os
import socket
import sys
import threading
import time
import webbrowser


def main() -> None:
    parser = argparse.ArgumentParser(description="FenixPortChecker — switch port gözlem aracı")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=0, help="0 = boş bir yerel port seç")
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--server", action="store_true", help="Pencere açma, yalnız HTTP sunucu")
    args = parser.parse_args()

    if getattr(sys, "frozen", False):
        _redirect_frozen_log()

    try:
        import uvicorn
        from portgozu.app import app
    except ImportError:
        print("uvicorn yok. Şunu çalıştırın: python -m pip install -r requirements.txt", file=sys.stderr)
        raise SystemExit(1) from None

    host = args.host
    port = args.port or _free_port(host)
    os.environ.setdefault("PORTGOZU_HOST", host)

    config = uvicorn.Config(app, host=host, port=port, log_level="warning", access_log=False)
    server = uvicorn.Server(config)
    server.install_signal_handlers = lambda: None
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    url = f"http://{host}:{port}"
    if not _wait_ready(url):
        print(f"Sunucu başlamadı: {url}", file=sys.stderr)
        raise SystemExit(1)
    print(f"FenixPortChecker {url}")

    frozen = getattr(sys, "frozen", False)
    if args.server or args.no_browser:
        thread.join()
        return

    if _open_window(url):
        server.should_exit = True
        return
    webbrowser.open(url)
    if frozen:
        _alert(f"Pencere açılamadı. Tarayıcıda açın:\n{url}")
    thread.join()


def _free_port(host: str) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        return int(sock.getsockname()[1])


def _wait_ready(url: str, timeout: float = 15.0) -> bool:
    import urllib.request

    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=0.4) as resp:
                if resp.status == 200:
                    return True
        except OSError:
            time.sleep(0.15)
    return False


def _window_icon() -> str | None:
    from pathlib import Path

    frozen = getattr(sys, "frozen", False)
    if frozen:
        base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
        for rel in (
            Path("packaging") / "portgozu.ico",
            Path("portgozu") / "static" / "anka-mark.png",
            Path("portgozu") / "static" / "favicon.svg",
        ):
            candidate = base / rel
            if candidate.is_file():
                return str(candidate)
    root = Path(__file__).resolve().parents[2]
    for candidate in (
        root / "packaging" / "portgozu.ico",
        Path(__file__).resolve().parent / "static" / "anka-mark.png",
        Path(__file__).resolve().parent / "static" / "favicon.svg",
    ):
        if candidate.is_file():
            return str(candidate)
    return None


def _open_window(url: str) -> bool:
    try:
        import webview
    except ImportError:
        return False
    try:
        kwargs = {"width": 1180, "height": 800, "min_size": (900, 600)}
        icon = _window_icon()
        if icon:
            kwargs["icon"] = icon
        try:
            webview.create_window("FenixPortChecker", url, **kwargs)
        except TypeError:
            kwargs.pop("icon", None)
            webview.create_window("FenixPortChecker", url, **kwargs)
        webview.start()
        return True
    except Exception:
        return False


def _alert(message: str) -> None:
    if sys.platform == "win32":
        try:
            import ctypes

            ctypes.windll.user32.MessageBoxW(0, message, "FenixPortChecker", 0x40)
            return
        except Exception:
            pass
    print(message, file=sys.stderr)


def _redirect_frozen_log() -> None:
    try:
        from pathlib import Path

        base = Path(os.environ.get("LOCALAPPDATA") or Path.home())
        log_dir = base / "FenixPortChecker"
        log_dir.mkdir(parents=True, exist_ok=True)
        handle = open(log_dir / "fenixportchecker.log", "a", encoding="utf-8")
        sys.stdout = handle
        sys.stderr = handle
    except Exception:
        pass


if __name__ == "__main__":
    main()
