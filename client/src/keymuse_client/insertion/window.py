"""Foreground window detection and management for Windows.

This module provides functions to detect and validate the foreground
window before text insertion, to ensure text goes to the intended target.
"""

from __future__ import annotations

import ctypes
import logging
import sys
from ctypes import wintypes
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class WindowInfo:
    """Information about a window."""

    hwnd: int
    title: str
    class_name: str
    pid: int


def _get_window_text(hwnd: int) -> str:
    """Get the title text of a window."""
    if sys.platform != "win32":
        return ""

    length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
    if length == 0:
        return ""

    buffer = ctypes.create_unicode_buffer(length + 1)
    ctypes.windll.user32.GetWindowTextW(hwnd, buffer, length + 1)
    return buffer.value


def _get_window_class(hwnd: int) -> str:
    """Get the class name of a window."""
    if sys.platform != "win32":
        return ""

    buffer = ctypes.create_unicode_buffer(256)
    ctypes.windll.user32.GetClassNameW(hwnd, buffer, 256)
    return buffer.value


def _get_window_pid(hwnd: int) -> int:
    """Get the process ID of a window."""
    if sys.platform != "win32":
        return 0

    pid = wintypes.DWORD()
    ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return pid.value


def get_foreground_window() -> Optional[WindowInfo]:
    """Get information about the current foreground window.

    Returns:
        WindowInfo for the foreground window, or None if not on Windows
        or no window is in focus.
    """
    if sys.platform != "win32":
        logger.debug("Window detection not available on this platform")
        return None

    hwnd = ctypes.windll.user32.GetForegroundWindow()
    if hwnd == 0:
        return None

    return WindowInfo(
        hwnd=hwnd,
        title=_get_window_text(hwnd),
        class_name=_get_window_class(hwnd),
        pid=_get_window_pid(hwnd),
    )


def is_same_window(window1: Optional[WindowInfo], window2: Optional[WindowInfo]) -> bool:
    """Check if two WindowInfo objects refer to the same window.

    Args:
        window1: First window.
        window2: Second window.

    Returns:
        True if both refer to the same window handle.
    """
    if window1 is None or window2 is None:
        return False
    return window1.hwnd == window2.hwnd


def set_foreground_window(hwnd: int) -> bool:
    """Attempt to bring a window to the foreground.

    Args:
        hwnd: Window handle.

    Returns:
        True if successful.
    """
    if sys.platform != "win32":
        return False

    return bool(ctypes.windll.user32.SetForegroundWindow(hwnd))


def is_text_input_window(window: Optional[WindowInfo]) -> bool:
    """Heuristically check if a window can accept text input.

    This checks for common edit control class names and window properties
    that indicate the window can receive text.

    Args:
        window: Window to check.

    Returns:
        True if the window appears to accept text input.
    """
    if window is None:
        return False

    # Common class names for text input controls
    text_input_classes = {
        "edit",
        "richedit",
        "richedit20a",
        "richedit20w",
        "scintilla",
        "notepad",
        "msftedit",
    }

    class_lower = window.class_name.lower()

    # Check if it's a known text input class
    for input_class in text_input_classes:
        if input_class in class_lower:
            return True

    # Most windows with editable content will accept paste
    # This is a permissive check - actual paste may still fail
    return True


class ForegroundWindowGuard:
    """Context manager to verify foreground window hasn't changed.

    This captures the foreground window on entry and verifies it's
    still the same on exit, useful for ensuring paste operations
    go to the intended window.
    """

    def __init__(self) -> None:
        self._initial_window: Optional[WindowInfo] = None
        self._window_changed = False

    @property
    def initial_window(self) -> Optional[WindowInfo]:
        """Get the window that was active when the guard was entered."""
        return self._initial_window

    @property
    def window_changed(self) -> bool:
        """Return True if the foreground window changed."""
        return self._window_changed

    def __enter__(self) -> "ForegroundWindowGuard":
        self._initial_window = get_foreground_window()
        self._window_changed = False
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        current_window = get_foreground_window()
        self._window_changed = not is_same_window(
            self._initial_window, current_window
        )
        if self._window_changed:
            logger.warning(
                f"Foreground window changed from '{self._initial_window}' "
                f"to '{current_window}'"
            )


class MockWindowInfo:
    """Mock window info for testing on non-Windows platforms."""

    def __init__(self, hwnd: int = 12345, title: str = "Mock Window"):
        self.hwnd = hwnd
        self.title = title
        self.class_name = "MockClass"
        self.pid = 1000


__all__ = [
    "WindowInfo",
    "get_foreground_window",
    "is_same_window",
    "set_foreground_window",
    "is_text_input_window",
    "ForegroundWindowGuard",
]
