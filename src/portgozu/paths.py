from __future__ import annotations

import sys
from pathlib import Path


def static_dir() -> Path:
    """PyInstaller tek-dosya paketinde static dosyaları _MEIPASS altındadır."""
    candidates: list[Path] = []
    if getattr(sys, "frozen", False):
        meipass = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
        candidates.extend(
            [
                meipass / "portgozu" / "static",
                meipass / "static",
                Path(sys.executable).resolve().parent / "portgozu" / "static",
            ]
        )
    candidates.append(Path(__file__).resolve().parent / "static")
    for path in candidates:
        if (path / "index.html").is_file():
            return path
    return candidates[-1]
