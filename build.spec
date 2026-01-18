# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec file for KeyMuse client.

This builds a lightweight client-only application (~70MB) that spawns
the backend as a separate Python subprocess. The backend runs from the
user's Python installation with torch/CUDA support.
"""

import os
from pathlib import Path

block_cipher = None

repo_root = Path(os.getcwd())

# Only include client and shared modules (no backend/torch/nemo)
a = Analysis(
    [str(repo_root / "client" / "src" / "keymuse_client" / "launcher.py")],
    pathex=[
        str(repo_root / "shared" / "src"),
        str(repo_root / "client" / "src"),
    ],
    binaries=[],
    datas=[],
    hiddenimports=[
        # Client modules
        "keymuse_client",
        "keymuse_client.app",
        "keymuse_client.config",
        "keymuse_client.orchestrator",
        "keymuse_client.grpc_client",
        "keymuse_client.python_finder",
        "keymuse_client.audio",
        "keymuse_client.audio.capture",
        "keymuse_client.audio.devices",
        "keymuse_client.hotkeys",
        "keymuse_client.hotkeys.state_machine",
        "keymuse_client.hotkeys.win32_hook",
        "keymuse_client.insertion",
        "keymuse_client.insertion.keyboard",
        "keymuse_client.insertion.clipboard",
        "keymuse_client.insertion.window",
        # Proto modules (shared)
        "keymuse_proto",
        "keymuse_proto.dictation_pb2",
        "keymuse_proto.dictation_pb2_grpc",
        # Core dependencies
        "sounddevice",
        "grpc",
        "grpc._cython",
        "grpc._cython.cygrpc",
        # Win32 support
        "win32api",
        "win32con",
        "win32gui",
        "win32clipboard",
        "pywintypes",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude ML packages (handled by backend subprocess)
        "torch",
        "torchaudio",
        "torchvision",
        "nemo",
        "nemo_toolkit",
        "pytorch_lightning",
        "lightning",
        "lightning_fabric",
        "transformers",
        "huggingface_hub",
        "sentencepiece",
        "hydra",
        "omegaconf",
        # Exclude backend module
        "keymuse_backend",
        # Exclude other unnecessary packages
        "cv2",
        "opencv",
        "PIL",
        "matplotlib",
        "pandas",
        "numpy.testing",
        "scipy",
        "sklearn",
        "jupyter",
        "notebook",
        "IPython",
        "pytest",
        "sphinx",
        "docutils",
        "setuptools",
        "pip",
        "wheel",
        "tkinter",
        "_tkinter",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="KeyMuse",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="KeyMuse",
)
