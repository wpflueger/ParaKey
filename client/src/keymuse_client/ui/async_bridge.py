"""Async bridge for thread-safe tkinter/asyncio communication.

This module provides utilities for safely communicating between
tkinter's main thread and asyncio background threads.
"""

from __future__ import annotations

import asyncio
import logging
import threading
from concurrent.futures import Future
from typing import Any, Callable, Coroutine, Optional, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class TkAsyncBridge:
    """Bridge between tkinter main thread and asyncio background thread.

    This class provides thread-safe methods for:
    - Running asyncio coroutines from the UI thread
    - Scheduling UI updates from async code
    - Managing the background async event loop
    """

    def __init__(self, root) -> None:
        """Initialize the async bridge.

        Args:
            root: The tkinter root window.
        """
        self._root = root
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False

    @property
    def loop(self) -> Optional[asyncio.AbstractEventLoop]:
        """Get the background event loop."""
        return self._loop

    @property
    def is_running(self) -> bool:
        """Check if the async loop is running."""
        return self._running and self._loop is not None

    def start_async_loop(self) -> asyncio.AbstractEventLoop:
        """Start the background asyncio event loop.

        Returns:
            The event loop running in the background thread.
        """
        if self._running:
            raise RuntimeError("Async loop already running")

        ready_event = threading.Event()
        loop_holder: list[asyncio.AbstractEventLoop] = []

        def run_loop():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop_holder.append(loop)
            self._loop = loop
            self._running = True
            ready_event.set()

            try:
                loop.run_forever()
            finally:
                try:
                    # Cancel all pending tasks
                    pending = asyncio.all_tasks(loop)
                    for task in pending:
                        task.cancel()

                    # Wait for cancellation
                    if pending:
                        loop.run_until_complete(
                            asyncio.gather(*pending, return_exceptions=True)
                        )

                    loop.run_until_complete(loop.shutdown_asyncgens())
                finally:
                    loop.close()
                    self._running = False
                    self._loop = None

        self._thread = threading.Thread(
            target=run_loop,
            daemon=True,
            name="AsyncLoopThread",
        )
        self._thread.start()

        # Wait for loop to be ready
        ready_event.wait(timeout=5.0)
        if not loop_holder:
            raise RuntimeError("Failed to start async loop")

        logger.debug("Async event loop started")
        return loop_holder[0]

    def stop_async_loop(self) -> None:
        """Stop the background asyncio event loop."""
        if not self._running or self._loop is None:
            return

        logger.debug("Stopping async event loop")
        self._loop.call_soon_threadsafe(self._loop.stop)

        if self._thread is not None:
            self._thread.join(timeout=5.0)
            self._thread = None

    def run_async(
        self,
        coro: Coroutine[Any, Any, T],
        callback: Optional[Callable[[T], None]] = None,
        error_callback: Optional[Callable[[Exception], None]] = None,
    ) -> Future[T]:
        """Schedule a coroutine to run in the async loop.

        Args:
            coro: The coroutine to run.
            callback: Optional callback with result (called in UI thread).
            error_callback: Optional callback for errors (called in UI thread).

        Returns:
            A Future that will hold the result.
        """
        if not self._running or self._loop is None:
            raise RuntimeError("Async loop not running")

        future = asyncio.run_coroutine_threadsafe(coro, self._loop)

        if callback is not None or error_callback is not None:
            def on_done(f: Future):
                try:
                    result = f.result()
                    if callback is not None:
                        self.schedule_ui_update(lambda: callback(result))
                except Exception as e:
                    if error_callback is not None:
                        self.schedule_ui_update(lambda: error_callback(e))
                    else:
                        logger.error(f"Async operation failed: {e}")

            future.add_done_callback(on_done)

        return future

    def schedule_ui_update(self, callback: Callable[[], None]) -> None:
        """Schedule a callback to run in the tkinter main thread.

        This is safe to call from any thread.

        Args:
            callback: Function to call in the UI thread.
        """
        try:
            self._root.after(0, callback)
        except Exception as e:
            logger.debug(f"Failed to schedule UI update: {e}")

    def create_threadsafe_callback(
        self,
        callback: Callable[..., None],
    ) -> Callable[..., None]:
        """Create a thread-safe wrapper for a callback.

        The wrapper can be called from any thread and will execute
        the callback in the tkinter main thread.

        Args:
            callback: The callback to wrap.

        Returns:
            A thread-safe wrapper function.
        """
        def wrapper(*args, **kwargs):
            self.schedule_ui_update(lambda: callback(*args, **kwargs))

        return wrapper


class CallbackWrapper:
    """Wraps callbacks for thread-safe execution.

    Use this to create callbacks that can be safely passed to
    async code but will execute in the UI thread.
    """

    def __init__(self, bridge: TkAsyncBridge) -> None:
        """Initialize the wrapper.

        Args:
            bridge: The async bridge to use.
        """
        self._bridge = bridge

    def wrap(self, callback: Callable[..., None]) -> Callable[..., None]:
        """Wrap a callback for thread-safe execution.

        Args:
            callback: The callback to wrap.

        Returns:
            A thread-safe wrapper.
        """
        return self._bridge.create_threadsafe_callback(callback)


__all__ = [
    "TkAsyncBridge",
    "CallbackWrapper",
]
