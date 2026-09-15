"""16x16 ve 32x32 mavi kare .ico üretir (PIL gerekmez)."""

from __future__ import annotations

import struct
from pathlib import Path


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


def write_ico(path: Path) -> None:
    images = [(16, _bitmap(16, (255, 132, 10))), (32, _bitmap(32, (255, 132, 10)))]
    count = len(images)
    offset = 6 + 16 * count
    entries = b""
    payloads = b""
    for size, data in images:
        entries += struct.pack("<BBBBHHII", size, size, 0, 0, 1, 32, len(data), offset)
        payloads += data
        offset += len(data)
    path.write_bytes(struct.pack("<HHH", 0, 1, count) + entries + payloads)


if __name__ == "__main__":
    out = Path(__file__).resolve().parent / "portgozu.ico"
    write_ico(out)
    print(out)
