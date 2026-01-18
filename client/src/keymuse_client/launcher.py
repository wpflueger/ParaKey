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

from keymuse_client.config import ClientConfig
from keymuse_client.grpc_client import DictationClient
from keymuse_client.insertion.clipboard import (
    get_last_transcript,
    get_transcript_history,
    set_clipboard_text,
)
from keymuse_client.orchestrator import DictationOrchestrator, DictationState
from keymuse_client.python_finder import (
    BackendDepsError,
    PythonInfo,
    PythonNotFoundError,
    find_python,
)
from keymuse_client.ui.tray import SystemTray, TrayIconState

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


def start_backend_subprocess(
    python_info: PythonInfo,
    host: str = "127.0.0.1",
    port: int = 50051,
    mode: Optional[str] = None,
    device: Optional[str] = None,
    model: Optional[str] = None,
    on_output: Optional[callable] = None,
) -> subprocess.Popen:
    """Start the backend as a subprocess.

    Args:
        python_info: Python installation to use.
        host: Backend host address.
        port: Backend port number.
        mode: Backend mode (mock, nemo).
        device: Device to use (cuda, cpu).
        model: Model name override.
        on_output: Optional callback for each line of output.

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
        def stream_output():
            global _stop_output_thread
            if process.stdout is None:
                return
            try:
                for line in iter(process.stdout.readline, ""):
                    if _stop_output_thread:
                        break
                    if line:
                        line_text = line.rstrip()
                        print(f"[backend] {line_text}")
                        sys.stdout.flush()
                        if on_output:
                            on_output(line_text)
            except Exception:
                pass

        _output_thread = threading.Thread(target=stream_output, daemon=True)
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
                    except Exception as read_error:
                        logging.getLogger(__name__).warning(
                            "Failed to read backend process stdout before exit: %s",
                            read_error,
                        )
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
    parser.add_argument(
        "--no-gui",
        action="store_true",
        help="Run without GUI (console only)",
    )
    return parser.parse_args()


class KeyMuseApp:
    """Main KeyMuse application with UI."""

    def __init__(self, args: argparse.Namespace) -> None:
        """Initialize the application.

        Args:
            args: Parsed command line arguments.
        """
        self._args = args
        self._root = None
        self._startup_window = None
        self._main_window = None
        self._tray = None
        self._async_bridge = None
        self._orchestrator: Optional[DictationOrchestrator] = None
        self._shutdown_event: Optional[asyncio.Event] = None
        self._python_info: Optional[PythonInfo] = None
        self._backend_process: Optional[subprocess.Popen] = None

    def run(self) -> int:
        """Run the application.

        Returns:
            Exit code.
        """
        import tkinter as tk

        from keymuse_client.ui.async_bridge import TkAsyncBridge
        from keymuse_client.ui.main_window import MainWindow
        from keymuse_client.ui.startup_window import StartupWindow
        from keymuse_client.ui.theme import configure_ttk_style

        # Create hidden root window
        self._root = tk.Tk()
        self._root.withdraw()

        # Configure styles on root
        configure_ttk_style(self._root)

        # Show startup window
        self._startup_window = StartupWindow(
            self._root,
            on_cancel=self._handle_cancel,
        )
        self._startup_window.set_status("Initializing...")

        # Create async bridge and start event loop
        self._async_bridge = TkAsyncBridge(self._root)
        self._async_bridge.start_async_loop()

        # Schedule startup in async loop
        self._async_bridge.run_async(
            self._startup_async(),
            callback=self._on_startup_complete,
            error_callback=self._on_startup_error,
        )

        # Run tkinter main loop
        try:
            self._root.mainloop()
            return 0
        except Exception as e:
            logger.error(f"Application error: {e}")
            return 1
        finally:
            self._cleanup()

    async def _startup_async(self) -> bool:
        """Async startup sequence.

        Returns:
            True if startup succeeded.
        """
        args = self._args

        # Find Python
        self._schedule_startup_window(
            lambda: self._startup_window.set_status("Finding Python environment...")
        )

        try:
            if args.python:
                from keymuse_client.python_finder import check_backend_deps
                self._python_info = check_backend_deps(Path(args.python))
            else:
                self._python_info = find_python(check_deps=True)

            version_msg = f"Python {self._python_info.version}"
            if self._python_info.has_cuda:
                version_msg += " (CUDA)"
            else:
                version_msg += " (CPU)"

            self._schedule_startup_window(
                lambda: self._startup_window.append_log(version_msg)
            )

        except PythonNotFoundError as e:
            raise RuntimeError(f"Python not found: {e}")
        except BackendDepsError as e:
            raise RuntimeError(f"Missing dependencies: {e}")

        # Start backend
        self._schedule_startup_window(
            lambda: self._startup_window.set_status("Starting backend server...")
        )

        def on_backend_output(line: str):
            self._schedule_startup_window(
                lambda: self._startup_window.append_log(line)
            )

        self._backend_process = start_backend_subprocess(
            self._python_info,
            host=args.host,
            port=args.port,
            mode=args.mode,
            device=args.device,
            model=args.model,
            on_output=on_backend_output,
        )

        # Wait for backend health
        self._schedule_startup_window(
            lambda: self._startup_window.set_status("Loading speech recognition model...")
        )

        await wait_for_backend_health(
            args.host,
            args.port,
            timeout_s=args.timeout,
            process=self._backend_process,
        )

        return True

    def _schedule_ui(self, callback: callable) -> None:
        """Schedule a callback on the UI thread."""
        if self._async_bridge:
            self._async_bridge.schedule_ui_update(callback)

    def _schedule_startup_window(self, callback: callable) -> None:
        """Schedule a callback that requires the startup window."""
        def safe_callback():
            if self._startup_window is not None:
                callback()
        self._schedule_ui(safe_callback)

    def _on_startup_complete(self, result: bool) -> None:
        """Called when startup completes successfully."""
        if self._startup_window:
            self._startup_window.show_success()
            # Close startup window after brief delay
            self._root.after(500, self._show_main_window)

    def _on_startup_error(self, error: Exception) -> None:
        """Called when startup fails."""
        error_msg = str(error)
        logger.error(f"Startup failed: {error_msg}")

        if self._startup_window:
            self._startup_window.show_error(error_msg)

    def _show_main_window(self) -> None:
        """Show the main window and start the orchestrator."""
        from keymuse_client.ui.main_window import MainWindow
        from keymuse_client.settings import get_settings_manager

        # Close startup window
        if self._startup_window:
            self._startup_window.close()
            self._startup_window = None

        # Create main window
        self._main_window = MainWindow(
            self._root,
            on_settings=self._handle_settings,
            on_minimize_to_tray=self._handle_minimize_to_tray,
            on_quit=self._handle_quit,
        )
        self._main_window.set_on_copy(self._handle_copy)

        # Create system tray
        self._tray = SystemTray(
            on_quit=self._handle_quit,
            on_settings=self._handle_settings,
            on_copy_last=self._handle_copy_last,
            on_show_window=self._handle_show_window,
            get_history=get_transcript_history,
            on_copy_history_item=self._handle_copy,
        )
        self._tray.start()

        # Start orchestrator
        self._async_bridge.run_async(
            self._start_orchestrator(),
            error_callback=lambda e: logger.error(f"Orchestrator error: {e}"),
        )

        # Check if should start minimized
        settings = get_settings_manager().settings
        if settings.start_minimized:
            self._main_window.hide()
        else:
            self._main_window.show()

    async def _start_orchestrator(self) -> None:
        """Start the dictation orchestrator."""
        args = self._args

        config = ClientConfig(
            backend_host=args.host,
            backend_port=args.port,
        )

        self._orchestrator = DictationOrchestrator(config)
        self._shutdown_event = asyncio.Event()

        # Set up callbacks (wrapped for thread safety)
        def on_state(state: DictationState):
            self._schedule_ui(lambda: self._update_state(state))

        def on_partial(text: str):
            pass  # Could update UI with partial text

        def on_final(text: str):
            self._schedule_ui(lambda: self._on_transcript(text))

        def on_error(error: str):
            self._schedule_ui(lambda: self._on_error(error))

        self._orchestrator.set_callbacks(
            on_state_change=on_state,
            on_partial=on_partial,
            on_final=on_final,
            on_error=on_error,
        )

        await self._orchestrator.start()

        # Update UI to ready state
        self._schedule_ui(lambda: self._main_window.set_all_ready() if self._main_window else None)

        # Wait for shutdown
        await self._shutdown_event.wait()

        # Stop orchestrator
        await self._orchestrator.stop()

    def _update_state(self, state: DictationState) -> None:
        """Update UI state from orchestrator state."""
        if self._main_window:
            self._main_window.update_dictation_state(state.name)

        # Map to tray icon state
        tray_state_map = {
            DictationState.IDLE: TrayIconState.IDLE,
            DictationState.RECORDING: TrayIconState.RECORDING,
            DictationState.PROCESSING: TrayIconState.PROCESSING,
            DictationState.INSERTING: TrayIconState.PROCESSING,
            DictationState.ERROR: TrayIconState.ERROR,
        }
        if self._tray:
            self._tray.set_state(tray_state_map.get(state, TrayIconState.IDLE))

    def _on_transcript(self, text: str) -> None:
        """Handle new transcript."""
        if self._main_window:
            self._main_window.add_transcript(text)

    def _on_error(self, error: str) -> None:
        """Handle error."""
        logger.error(f"Dictation error: {error}")
        if self._tray:
            self._tray.show_notification("KeyMuse Error", error)

    def _handle_settings(self) -> None:
        """Handle settings button/menu."""
        from keymuse_client.settings import show_settings_dialog
        # Schedule on main thread
        self._root.after(0, lambda: show_settings_dialog(self._main_window))

    def _handle_minimize_to_tray(self) -> None:
        """Handle minimize to tray."""
        if self._tray:
            self._tray.show_notification("KeyMuse", "Minimized to tray")

    def _handle_show_window(self) -> None:
        """Handle show window request from tray."""
        self._schedule_ui(lambda: self._main_window.show() if self._main_window else None)

    def _handle_copy(self, text: str) -> None:
        """Handle copy request."""
        if set_clipboard_text(text):
            if self._tray:
                self._tray.show_notification("KeyMuse", "Copied to clipboard")

    def _handle_copy_last(self) -> None:
        """Handle copy last transcript."""
        last = get_last_transcript()
        if last:
            self._handle_copy(last)

    def _handle_cancel(self) -> None:
        """Handle cancel during startup."""
        self._handle_quit()

    def _handle_quit(self) -> None:
        """Handle quit request."""
        logger.info("Quit requested")

        # Signal shutdown
        if self._shutdown_event:
            if self._async_bridge and self._async_bridge.loop:
                self._async_bridge.loop.call_soon_threadsafe(self._shutdown_event.set)

        # Stop tray
        if self._tray:
            self._tray.stop()

        # Quit tkinter
        if self._root:
            self._root.after(100, self._root.quit)

    def _cleanup(self) -> None:
        """Clean up resources."""
        logger.info("Cleaning up...")

        # Stop async loop
        if self._async_bridge:
            self._async_bridge.stop_async_loop()

        # Clean up backend
        _cleanup_backend()


async def run_app_console() -> None:
    """Run the KeyMuse application in console mode (no GUI)."""
    from keymuse_client.app import run_interactive, run_once

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
    args = parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Handle Ctrl+C gracefully
    def signal_handler(*_args):
        print("\nInterrupted, cleaning up...")
        _cleanup_backend()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    if sys.platform == "win32":
        signal.signal(signal.SIGBREAK, signal_handler)

    # Check for GUI mode
    if args.no_gui:
        try:
            asyncio.run(run_app_console())
        except KeyboardInterrupt:
            pass
    else:
        try:
            app = KeyMuseApp(args)
            sys.exit(app.run())
        except ImportError as e:
            # Fall back to console mode if tkinter not available
            logger.warning(f"GUI not available ({e}), falling back to console mode")
            try:
                asyncio.run(run_app_console())
            except KeyboardInterrupt:
                pass


if __name__ == "__main__":
    main()
