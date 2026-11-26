# PyInstaller build configuration; invoke with scripts/build_windows.py.
from pathlib import Path

root = Path(SPECPATH)
a = Analysis(
    [str(root / "app_main.py")],
    pathex=[str(root)],
    binaries=[],
    datas=[
        (str(root / "imagens"), "imagens"),
        (str(root / "LICENSE"), "."),
        (str(root / "NOTICE"), "."),
        (str(root / "build" / "THIRD_PARTY_NOTICES.txt"), "."),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={"matplotlib": {"backends": ["TkAgg"]}},
    runtime_hooks=[],
    excludes=["pytest", "ruff"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name="BatSignal",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon=str(root / "imagens" / "logo.ico"),
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="BatSignal")
