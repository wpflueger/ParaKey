"""KeyMuse launcher - spawns backend subprocess and runs client.

This module starts the backend gRPC server as a separate Python subprocess
and runs the client in the main process. This hybrid architecture allows
the client to be bundled as a lightweight exe while the backend uses the
user's Python installation with torch/CUDA.
"""

from __future__ import annotations

import argparse
import asyncio
import atexit
import logging
import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Optional

# Support PyInstaller frozen apps
if getattr(sys, "frozen", False):
    import multiprocessing

    multiprocessing.freeze_support()

from keymuse_client.app import run_interactive, run_once
from keymuse_client.config import ClientConfig
from keymuse_client.grpc_client import DictationClient
from keymuse_client.python_finder import (
    BackendDepsError,
    PythonInfo,
    PythonNotFoundError,
    find_python,
)

logger = logging.getLogger("keymuse")

# Global reference to backend process for cleanup
_backend_process: Optional[subprocess.Popen] = None
_output_thread: Optional[threading.Thread] = None
_stop_output_thread = False


def _get_repo_root() -> Path:
    """Get the repository root directory."""
    if getattr(sys, "frozen", False):
        # Running as PyInstaller bundle - look for backend relative to exe
        exe_dir = Path(sys.executable).parent
        # Check several levels up for the repo structure
        for parent in [exe_dir, exe_dir.parent, exe_dir.parent.parent]:
            if (parent / "backend" / "src").exists():
                return parent
        return exe_dir
    else:
        # Running as script - find repo root from this file
        return Path(__file__).parent.parent.parent.parent.parent


def _build_pythonpath(repo_root: Path) -> str:
    """Build PYTHONPATH for the backend subprocess."""
    paths = [
        str(repo_root / "shared" / "src"),
        str(repo_root / "backend" / "src"),
        str(repo_root / "client" / "src"),
    ]

    existing_path = os.environ.get("PYTHONPATH", "")
    if existing_path:
        paths.append(existing_path)

    return os.pathsep.join(paths)


def _cleanup_backend() -> None:
    """Clean up backend process on exit."""
    global _backend_process, _stop_output_thread
    _stop_output_thread = True

    if _backend_process is not None:
        logger.info("Shutting down backend process...")
        try:
            _backend_process.terminate()
            try:
                _backend_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning("Backend did not terminate gracefully, killing...")
                _backend_process.kill()
                _backend_process.wait(timeout=2)
        except Exception as e:
            logger.warning(f"Error cleaning up backend: {e}")
        finally:
            _backend_process = None


def _stream_backend_output(process: subprocess.Popen) -> None:
    """Stream backend output to console in a background thread."""
    global _stop_output_thread

    if process.stdout is None:
        return

    try:
        for line in iter(process.stdout.readline, ""):
            if _stop_output_thread:
                break
            if line:
                # Print backend output with prefix
                print(f"[backend] {line.rstrip()}")
                sys.stdout.flush()
    except Exception:
        pass  # Process closed


def start_backend_subprocess(
    python_info: PythonInfo,
    host: str = "127.0.0.1",
    port: int = 50051,
    mode: Optional[str] = None,
    device: Optional[str] = None,
    model: Optional[str] = None,
) -> subprocess.Popen:
    """Start the backend as a subprocess.

    Args:
        python_info: Python installation to use.
        host: Backend host address.
        port: Backend port number.
        mode: Backend mode (mock, nemo).
        device: Device to use (cuda, cpu).
        model: Model name override.

    Returns:
        The subprocess.Popen object.

    Raises:
        RuntimeError: If backend fails to start.
    """
    global _backend_process, _output_thread, _stop_output_thread

    repo_root = _get_repo_root()
    pythonpath = _build_pythonpath(repo_root)

    # Build environment
    env = os.environ.copy()
    env["PYTHONPATH"] = pythonpath
    env["KEYMUSE_HOST"] = host
    env["KEYMUSE_PORT"] = str(port)

    # Enable unbuffered output for real-time streaming
    env["PYTHONUNBUFFERED"] = "1"

    if mode:
        env["KEYMUSE_MODE"] = mode
    if device:
        env["KEYMUSE_DEVICE"] = device
    if model:
        env["KEYMUSE_MODEL"] = model

    # Build command
    cmd = [str(python_info.executable), "-m", "keymuse_backend.server"]

    logger.info(f"Starting backend: {' '.join(cmd)}")
    logger.debug(f"PYTHONPATH: {pythonpath}")

    try:
        # Start subprocess with output pipes
        creationflags = 0
        if sys.platform == "win32":
            # CREATE_NEW_PROCESS_GROUP allows sending CTRL_BREAK_EVENT
            creationflags = subprocess.CREATE_NEW_PROCESS_GROUP

        process = subprocess.Popen(
            cmd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            creationflags=creationflags,
        )

        _backend_process = process
        _stop_output_thread = False

        # Start background thread to stream output
        _output_thread = threading.Thread(
            target=_stream_backend_output, args=(process,), daemon=True
        )
        _output_thread.start()

        # Register cleanup
        atexit.register(_cleanup_backend)

        return process

    except Exception as e:
        raise RuntimeError(f"Failed to start backend: {e}")


async def wait_for_backend_health(
    host: str,
    port: int,
    timeout_s: float = 180.0,
    poll_s: float = 0.5,
    process: Optional[subprocess.Popen] = None,
) -> None:
    """Wait for backend to respond to health checks.

    Args:
        host: Backend host.
        port: Backend port.
        timeout_s: Maximum time to wait.
        poll_s: Time between health checks.
        process: Optional backend process to monitor.

    Raises:
        RuntimeError: If backend is not ready within timeout.
    """
    deadline = time.monotonic() + timeout_s
    last_error: Optional[str] = None
    check_count = 0

    while time.monotonic() < deadline:
        # Check if process died
        if process is not None:
            ret = process.poll()
            if ret is not None:
                # Process exited - try to get error output
                stderr_output = ""
                if process.stdout:
                    try:
                        stderr_output = process.stdout.read()
                    except Exception:
                        pass
                raise RuntimeError(
                    f"Backend process exited with code {ret}\n{stderr_output}"
                )

        # Try health check
        client = DictationClient(host, port)
        try:
            health = await client.health()
            if health.ready:
                logger.info(f"Backend ready: {health.mode} - {health.detail}")
                return
            last_error = health.detail
        except Exception as e:
            last_error = str(e)
            check_count += 1
            if check_count % 10 == 0:
                logger.debug(f"Waiting for backend... ({last_error})")
        finally:
            await client.close()

        await asyncio.sleep(poll_s)

    raise RuntimeError(f"Backend not ready after {timeout_s}s: {last_error or 'timeout'}")


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="KeyMuse - Speech to text dictation",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Backend host")
    parser.add_argument("--port", type=int, default=50051, help="Backend port")
    parser.add_argument(
        "--mode",
        choices=["nemo", "mock"],
        default="nemo",
        help="Backend mode: nemo (default, AI transcription) or mock (testing)",
    )
    parser.add_argument("--device", help="Backend device (cuda, cpu)")
    parser.add_argument("--model", help="Model name override")
    parser.add_argument(
        "--client-mode",
        choices=["interactive", "once"],
        default="interactive",
        help="Client mode",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=180.0,
        help="Backend startup timeout in seconds",
    )
    parser.add_argument(
        "--python",
        help="Path to Python executable for backend (overrides auto-detect)",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose logging")
    return parser.parse_args()


async def run_app() -> None:
    """Run the KeyMuse application."""
    args = parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    print("=" * 50)
    print("KeyMuse - Speech to Text")
    print("=" * 50)
    print()

    # Find Python for backend
    print("Locating Python environment...")
    try:
        if args.python:
            # Use specified Python
            from keymuse_client.python_finder import check_backend_deps

            python_info = check_backend_deps(Path(args.python))
        else:
            python_info = find_python(check_deps=True)

        print(f"Using Python {python_info.version}: {python_info.executable}")
        if python_info.has_cuda:
            print("CUDA: available")
        else:
            print("CUDA: not available (will use CPU)")
        print()

    except PythonNotFoundError as e:
        print(f"Error: {e}")
        print()
        print("To fix this:")
        print("1. Install Python 3.11+ from https://www.python.org/downloads/")
        print("2. Or set KEYMUSE_PYTHON environment variable to your Python path")
        sys.exit(1)

    except BackendDepsError as e:
        print(f"Error: {e}")
        print()
        print("To fix this, run:")
        print(f"  {e.python_path} -m pip install -r backend/requirements.txt")
        sys.exit(1)

    # Start backend subprocess
    print("Starting backend server...")
    try:
        process = start_backend_subprocess(
            python_info,
            host=args.host,
            port=args.port,
            mode=args.mode,
            device=args.device,
            model=args.model,
        )
    except RuntimeError as e:
        print(f"Error: {e}")
        sys.exit(1)

    print("Loading speech recognition model...")
    print("(This may take a moment on first run)")
    print()

    try:
        # Wait for backend to be ready
        await wait_for_backend_health(
            args.host, args.port, timeout_s=args.timeout, process=process
        )

        # Create client config
        config = ClientConfig(
            backend_host=args.host,
            backend_port=args.port,
        )

        # Run the client
        if args.client_mode == "once":
            await run_once(config)
        else:
            await run_interactive(config)

    except KeyboardInterrupt:
        print("\nShutting down...")
    except RuntimeError as e:
        # Backend startup failure - show output
        print(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error: {e}")
        print(f"Error: {e}")
        sys.exit(1)
    finally:
        _cleanup_backend()


def main() -> None:
    """Main entry point."""
    # Handle Ctrl+C gracefully
    def signal_handler(*_args):
        print("\nInterrupted, cleaning up...")
        _cleanup_backend()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    if sys.platform == "win32":
        signal.signal(signal.SIGBREAK, signal_handler)

    try:
        asyncio.run(run_app())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
