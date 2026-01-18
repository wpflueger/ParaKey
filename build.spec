# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec file for KeyMuse Windows app."""

import sys
import os
from pathlib import Path

block_cipher = None

# Add source paths to sys.path for imports
repo_root = Path(os.getcwd())
sys.path.insert(0, str(repo_root / "shared" / "src"))
sys.path.insert(0, str(repo_root / "backend" / "src"))
sys.path.insert(0, str(repo_root / "client" / "src"))

a = Analysis(
    [str(repo_root / "client" / "src" / "keymuse_client" / "launcher.py")],
    pathex=[
        str(repo_root / "shared" / "src"),
        str(repo_root / "backend" / "src"),
        str(repo_root / "client" / "src"),
    ],
    binaries=[],
    datas=[],
    hiddenimports=[
        "sounddevice",
        "pywin32",
        "grpc",
        "keymuse_client",
        "keymuse_client.audio",
        "keymuse_client.audio.capture",
        "keymuse_client.hotkeys",
        "keymuse_client.hotkeys.win32_hook",
        "keymuse_client.insertion",
        "keymuse_client.insertion.keyboard",
        "keymuse_backend",
        "keymuse_backend.server",
        "keymuse_backend.service",
        "keymuse_backend.engine",
        "keymuse_proto",
        "torch",
        "nemo",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludedimports=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Include Windows SDK DLLs and audio libraries
try:
    import sounddevice
    sd_path = sounddevice.__path__[0]
    a.binaries += [(
        "sounddevice/_sounddevice_platform_windows.pyd",
        sd_path + "/_sounddevice_platform_windows.pyd",
        "BINARY",
    )]
except Exception:
    pass

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="KeyMuse",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
