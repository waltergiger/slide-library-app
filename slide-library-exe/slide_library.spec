# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for Slide Library.
#   Windows:   build.bat            -> dist\SlideLibrary.exe   (single file)
#              build.bat onedir     -> dist\SlideLibrary\      (folder; starts faster, fewer AV false positives)
# Sources are taken from the repository root (one level up); nothing is copied.
import os
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

ROOT = Path(SPECPATH).parent
ONEDIR = os.environ.get("SLIDELIB_ONEDIR") == "1"
ICON = str(Path(SPECPATH) / "icon.ico") if sys.platform == "win32" else None

datas = [(str(ROOT / "static"), "static")]
datas += collect_data_files("pptx")  # python-pptx's default template deck is loaded at runtime by exports

hiddenimports = (
    collect_submodules("uvicorn")        # protocol/loop/lifespan implementations are chosen by name at runtime
    + ["anyio._backends._asyncio", "h11"]
)

a = Analysis(
    [str(Path(SPECPATH) / "launcher.py")],
    pathex=[str(ROOT)],
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=["tkinter", "pytest", "matplotlib", "IPython", "tests"],
    noarchive=False,
)
pyz = PYZ(a.pure)

if ONEDIR:
    exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="SlideLibrary", console=True,
              icon=ICON, upx=False)
    coll = COLLECT(exe, a.binaries, a.datas, name="SlideLibrary", upx=False)
else:
    exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name="SlideLibrary", console=True,
              icon=ICON, upx=False)  # UPX-packed binaries trigger far more antivirus false positives
