"""Anka Kuşu .ico üretir: packaging/anka-icon.* kaynağından (Pillow varsa), aksi halde gömülü ICO kalır."""

from __future__ import annotations

import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "portgozu.ico"
SOURCE_CANDIDATES = (
    ROOT / "anka-icon.png",
    ROOT / "anka-icon.jpg",
    ROOT / "anka-icon.jpeg",
)


def _bitmap(size: int, bgr: tuple[int, int, int]) -> bytes:
    header = struct.pack(
        "<IIIHHIIIIII",
        40,
        size,
        size * 2,
        1,
        32,
        0,
        0,
        0,
        0,
        0,
        0,
    )
    pixel = bytes((bgr[0], bgr[1], bgr[2], 255))
    xor = pixel * (size * size)
    and_row = ((size + 31) // 32) * 4
    and_mask = b"\x00" * (and_row * size)
    return header + xor + and_mask


def write_fallback_ico(path: Path) -> None:
    """Pillow yoksa turuncu kare (eski davranış) — kaynak ICO zaten commit'liyse dokunma."""
    if path.is_file() and path.stat().st_size > 1024:
        return
    images = [(16, _bitmap(16, (26, 106, 255))), (32, _bitmap(32, (26, 106, 255)))]
    count = len(images)
    offset = 6 + 16 * count
    entries = b""
    payloads = b""
    for size, data in images:
        entries += struct.pack("<BBBBHHII", size, size, 0, 0, 1, 32, len(data), offset)
        payloads += data
        offset += len(data)
    path.write_bytes(struct.pack("<HHH", 0, 1, count) + entries + payloads)


def write_ico_from_image(src: Path, path: Path) -> None:
    from PIL import Image, ImageDraw

    img = Image.open(src).convert("RGBA")
    w, h = img.size
    radius = int(min(w, h) * 0.18)
    alpha = img.split()[-1]
    rounded = Image.new("L", (w, h), 0)
    ImageDraw.Draw(rounded).rounded_rectangle((0, 0, w - 1, h - 1), radius=radius, fill=255)
    img.putalpha(Image.composite(alpha, Image.new("L", (w, h), 0), rounded))

    sizes = [16, 24, 32, 48, 64, 128, 256]
    icons = [img.resize((s, s), Image.Resampling.LANCZOS) for s in sizes]
    icons[-1].save(path, format="ICO", sizes=[(s, s) for s in sizes], append_images=icons[:-1])


def main() -> None:
    src = next((p for p in SOURCE_CANDIDATES if p.is_file()), None)
    if src is not None:
        try:
            write_ico_from_image(src, OUT)
            print(OUT)
            return
        except Exception as exc:  # noqa: BLE001 — build script should not fail hard on icon polish
            print(f"Pillow ICO üretimi atlandı ({exc}); mevcut/yedek ICO kullanılacak", file=sys.stderr)
    write_fallback_ico(OUT)
    print(OUT)


if __name__ == "__main__":
    main()
