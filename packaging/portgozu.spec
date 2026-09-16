from pathlib import Path

from PyInstaller.utils.hooks import collect_all

datas: list = []
binaries: list = []
hiddenimports: list = []
for pkg in (
    "fastapi",
    "starlette",
    "uvicorn",
    "pydantic",
    "pydantic_core",
    "anyio",
):
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h
try:
    d, b, h = collect_all("webview")
    datas += d
    binaries += b
    hiddenimports += h
except Exception:
    hiddenimports.append("webview")

root = Path(SPECPATH).resolve().parent
datas += [(str(root / "src" / "portgozu" / "static"), "portgozu/static")]
ico_src = root / "packaging" / "portgozu.ico"
if ico_src.is_file():
    datas += [(str(ico_src), "packaging")]

icon = root / "packaging" / "portgozu.ico"
icon_arg = str(icon) if icon.is_file() else None

a = Analysis(
    [str(root / "packaging" / "launch.py")],
    pathex=[str(root / "src")],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports
    + [
        "uvicorn.logging",
        "uvicorn.loops",
        "uvicorn.loops.auto",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan",
        "uvicorn.lifespan.on",
        "portgozu",
        "portgozu.app",
        "portgozu.engine",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["uvloop", "watchfiles", "IPython"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="FenixPortChecker",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_arg,
)
