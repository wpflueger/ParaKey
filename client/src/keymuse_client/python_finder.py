"""Python environment detection for KeyMuse.

This module locates Python installations that can run the KeyMuse backend,
checking for required dependencies (torch, nemo).
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class PythonInfo:
    """Information about a Python installation."""

    executable: Path
    version: str
    has_torch: bool = False
    has_nemo: bool = False
    has_cuda: bool = False

    @property
    def is_valid_backend(self) -> bool:
        """Return True if this Python can run the backend."""
        return self.has_torch and self.has_nemo


class PythonNotFoundError(Exception):
    """Raised when no suitable Python installation is found."""

    pass


class BackendDepsError(Exception):
    """Raised when backend dependencies are missing."""

    def __init__(self, message: str, python_path: Path) -> None:
        super().__init__(message)
        self.python_path = python_path


def _get_exe_dir() -> Path:
    """Get directory containing the executable (or script)."""
    if getattr(sys, "frozen", False):
        # Running as PyInstaller bundle
        return Path(sys.executable).parent
    else:
        # Running as script
        return Path(__file__).parent


def _run_python_check(python_path: Path, check_code: str) -> Optional[str]:
    """Run a Python check and return stdout, or None on failure."""
    try:
        result = subprocess.run(
            [str(python_path), "-c", check_code],
            capture_output=True,
            text=True,
            timeout=30,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
        if result.returncode == 0:
            return result.stdout.strip()
        return None
    except Exception:
        logger.exception(
            "Error running Python check with interpreter '%s' and code %r",
            python_path,
            check_code,
        )
        return None


def _check_python_version(python_path: Path) -> Optional[str]:
    """Check Python version, returns version string or None."""
    return _run_python_check(
        python_path, "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
    )


def _check_torch(python_path: Path) -> bool:
    """Check if torch is installed."""
    return _run_python_check(python_path, "import torch; print('ok')") == "ok"


def _check_nemo(python_path: Path) -> bool:
    """Check if nemo is installed."""
    return _run_python_check(python_path, "import nemo; print('ok')") == "ok"


def _check_cuda(python_path: Path) -> bool:
    """Check if CUDA is available via torch."""
    return (
        _run_python_check(python_path, "import torch; print('ok' if torch.cuda.is_available() else 'no')")
        == "ok"
    )


def _get_python_info(python_path: Path, check_deps: bool = True) -> Optional[PythonInfo]:
    """Get information about a Python installation."""
    if not python_path.exists():
        return None

    version = _check_python_version(python_path)
    if not version:
        return None

    # Check version is 3.11+
    try:
        major, minor = map(int, version.split("."))
        if major < 3 or (major == 3 and minor < 11):
            logger.debug(f"Python {version} too old (need 3.11+): {python_path}")
            return None
    except ValueError:
        return None

    info = PythonInfo(executable=python_path, version=version)

    if check_deps:
        info.has_torch = _check_torch(python_path)
        info.has_nemo = _check_nemo(python_path)
        if info.has_torch:
            info.has_cuda = _check_cuda(python_path)

    return info


def _find_venv_python() -> Optional[Path]:
    """Find Python in project .venv directory."""
    exe_dir = _get_exe_dir()

    # Search paths relative to exe/script location
    # When running as script: keymuse_client -> src -> client -> repo_root
    # When running as exe: dist/KeyMuse -> repo_root
    search_paths = [
        exe_dir / ".venv" / "Scripts" / "python.exe",
        exe_dir.parent / ".venv" / "Scripts" / "python.exe",
        exe_dir.parent.parent / ".venv" / "Scripts" / "python.exe",
        exe_dir.parent.parent.parent / ".venv" / "Scripts" / "python.exe",
        exe_dir.parent.parent.parent.parent / ".venv" / "Scripts" / "python.exe",
    ]

    # Also check KEYMUSE_ROOT if set
    keymuse_root = os.environ.get("KEYMUSE_ROOT")
    if keymuse_root:
        search_paths.insert(0, Path(keymuse_root) / ".venv" / "Scripts" / "python.exe")

    # Check current working directory too
    cwd = Path.cwd()
    search_paths.append(cwd / ".venv" / "Scripts" / "python.exe")

    for path in search_paths:
        if path.exists():
            logger.debug(f"Found venv Python: {path}")
            return path

    return None


def _find_env_python() -> Optional[Path]:
    """Find Python from KEYMUSE_PYTHON environment variable."""
    env_python = os.environ.get("KEYMUSE_PYTHON")
    if env_python:
        path = Path(env_python)
        if path.exists():
            logger.debug(f"Found Python from KEYMUSE_PYTHON: {path}")
            return path
        logger.warning(f"KEYMUSE_PYTHON set but not found: {env_python}")
    return None


def _find_py_launcher_python() -> Optional[Path]:
    """Find Python using Windows py launcher."""
    if sys.platform != "win32":
        return None

    # Try specific versions first
    for version in ["3.12", "3.11"]:
        try:
            result = subprocess.run(
                ["py", f"-{version}", "-c", "import sys; print(sys.executable)"],
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            if result.returncode == 0:
                path = Path(result.stdout.strip())
                if path.exists():
                    logger.debug(f"Found Python {version} via py launcher: {path}")
                    return path
        except Exception:
            continue

    return None


def _find_path_python() -> Optional[Path]:
    """Find Python in PATH."""
    python_path = shutil.which("python")
    if python_path:
        path = Path(python_path)
        logger.debug(f"Found Python in PATH: {path}")
        return path
    return None


def _find_common_install_python() -> Optional[Path]:
    """Find Python in common Windows installation paths."""
    if sys.platform != "win32":
        return None

    search_dirs = []

    # Common installation paths
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    if local_app_data:
        search_dirs.append(Path(local_app_data) / "Programs" / "Python")

    search_dirs.extend(
        [
            Path("C:/Python312"),
            Path("C:/Python311"),
            Path("C:/Program Files/Python312"),
            Path("C:/Program Files/Python311"),
        ]
    )

    for base_dir in search_dirs:
        if base_dir.is_dir():
            # Check for python.exe directly
            python_exe = base_dir / "python.exe"
            if python_exe.exists():
                logger.debug(f"Found Python at: {python_exe}")
                return python_exe

            # Check subdirectories (e.g., Python311, Python312)
            for subdir in sorted(base_dir.iterdir(), reverse=True):
                if subdir.is_dir() and subdir.name.startswith("Python"):
                    python_exe = subdir / "python.exe"
                    if python_exe.exists():
                        logger.debug(f"Found Python at: {python_exe}")
                        return python_exe

    return None


def find_python(check_deps: bool = True) -> PythonInfo:
    """Find a suitable Python installation.

    Search order:
    1. KEYMUSE_PYTHON environment variable (user override)
    2. .venv/Scripts/python.exe relative to exe location (project venv)
    3. python in PATH (often points to active venv)
    4. Windows py launcher (py -3.12, py -3.11)
    5. Common installation paths

    Args:
        check_deps: If True, check for torch/nemo installation.

    Returns:
        PythonInfo for the found Python.

    Raises:
        PythonNotFoundError: If no suitable Python is found.
        BackendDepsError: If Python found but missing dependencies.
    """
    finders = [
        ("KEYMUSE_PYTHON env var", _find_env_python),
        ("project .venv", _find_venv_python),
        ("PATH", _find_path_python),
        ("py launcher", _find_py_launcher_python),
        ("common paths", _find_common_install_python),
    ]

    found_python: Optional[PythonInfo] = None

    for name, finder in finders:
        path = finder()
        if path:
            info = _get_python_info(path, check_deps=check_deps)
            if info:
                if not check_deps or info.is_valid_backend:
                    logger.info(f"Found Python {info.version} via {name}: {path}")
                    return info
                # Remember first valid Python even if deps missing
                logger.debug(f"Python {info.version} via {name} missing deps: {path}")
                if found_python is None:
                    found_python = info

    # If we found Python but missing deps, report that specifically
    if found_python:
        missing = []
        if not found_python.has_torch:
            missing.append("torch")
        if not found_python.has_nemo:
            missing.append("nemo")

        raise BackendDepsError(
            f"Python found but missing backend dependencies: {', '.join(missing)}.\n"
            f"Run: {found_python.executable} -m pip install -r backend/requirements.txt",
            found_python.executable,
        )

    raise PythonNotFoundError(
        "Python 3.11+ not found.\n"
        "Install Python from https://www.python.org/downloads/\n"
        "Or set KEYMUSE_PYTHON environment variable to your Python executable."
    )


def check_backend_deps(python_path: Path) -> PythonInfo:
    """Check if a Python installation has backend dependencies.

    Args:
        python_path: Path to Python executable.

    Returns:
        PythonInfo with dependency status.

    Raises:
        BackendDepsError: If dependencies are missing.
    """
    info = _get_python_info(python_path, check_deps=True)
    if info is None:
        raise PythonNotFoundError(f"Invalid Python: {python_path}")

    if not info.is_valid_backend:
        missing = []
        if not info.has_torch:
            missing.append("torch")
        if not info.has_nemo:
            missing.append("nemo")

        raise BackendDepsError(
            f"Missing backend dependencies: {', '.join(missing)}.\n"
            f"Run: {python_path} -m pip install -r backend/requirements.txt",
            python_path,
        )

    return info


__all__ = [
    "PythonInfo",
    "PythonNotFoundError",
    "BackendDepsError",
    "find_python",
    "check_backend_deps",
]
