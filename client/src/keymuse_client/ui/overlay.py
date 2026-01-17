"""Recording overlay/toast notifications for KeyMuse.

This module provides visual feedback during dictation:
- Small overlay showing "Listening..." during recording
- Toast notifications for completed/failed insertions
"""

from __future__ import annotations

import ctypes
import logging
import sys
import threading
import time
from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional

logger = logging.getLogger(__name__)


class OverlayType(Enum):
    """Type of overlay to display."""

    LISTENING = auto()
    PROCESSING = auto()
    INSERTED = auto()
    ERROR = auto()


@dataclass
class OverlayConfig:
    """Configuration for overlay display."""

    # Position from screen edge
    x_offset: int = 20
    y_offset: int = 20

    # Size
    width: int = 200
    height: int = 40

    # Timing
    auto_hide_ms: int = 2000  # Auto-hide after this duration (0 = manual)

    # Colors (ABGR format for Windows)
    background_color: int = 0x80000000  # Semi-transparent black
    text_color: int = 0xFFFFFFFF  # White


if sys.platform == "win32":
    # Windows overlay implementation using layered windows

    # Window styles
    WS_EX_LAYERED = 0x00080000
    WS_EX_TRANSPARENT = 0x00000020
    WS_EX_TOPMOST = 0x00000008
    WS_EX_TOOLWINDOW = 0x00000080
    WS_EX_NOACTIVATE = 0x08000000
    WS_POPUP = 0x80000000

    # Layered window attributes
    LWA_COLORKEY = 0x00000001
    LWA_ALPHA = 0x00000002

    # System metrics
    SM_CXSCREEN = 0
    SM_CYSCREEN = 1


class OverlayWindow:
    """A semi-transparent overlay window for visual feedback.

    This creates a small, always-on-top window that displays
    status messages during dictation without stealing focus.
    """

    def __init__(self, config: Optional[OverlayConfig] = None) -> None:
        """Initialize the overlay window.

        Args:
            config: Overlay configuration.
        """
        self._config = config or OverlayConfig()
        self._hwnd: Optional[int] = None
        self._visible = False
        self._current_text = ""
        self._hide_timer: Optional[threading.Timer] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False

    @property
    def is_visible(self) -> bool:
        """Return True if overlay is currently visible."""
        return self._visible

    def show(
        self,
        text: str,
        overlay_type: OverlayType = OverlayType.LISTENING,
        auto_hide: bool = True,
    ) -> None:
        """Show the overlay with given text.

        Args:
            text: Text to display.
            overlay_type: Type of overlay (affects styling).
            auto_hide: If True, auto-hide after configured duration.
        """
        self._current_text = text

        if sys.platform == "win32":
            self._show_windows(text, overlay_type)
        else:
            # Fallback: just log
            logger.info(f"Overlay: {text}")

        if auto_hide and self._config.auto_hide_ms > 0:
            self._schedule_hide(self._config.auto_hide_ms / 1000)

        self._visible = True

    def hide(self) -> None:
        """Hide the overlay."""
        if self._hide_timer:
            self._hide_timer.cancel()
            self._hide_timer = None

        if sys.platform == "win32" and self._hwnd:
            try:
                ctypes.windll.user32.ShowWindow(self._hwnd, 0)  # SW_HIDE
            except Exception as e:
                logger.debug(f"Error hiding overlay: {e}")

        self._visible = False

    def update_text(self, text: str) -> None:
        """Update the overlay text without hiding/showing.

        Args:
            text: New text to display.
        """
        self._current_text = text
        if self._visible and self._hwnd:
            # Invalidate window to trigger repaint
            try:
                ctypes.windll.user32.InvalidateRect(self._hwnd, None, True)
            except Exception as e:
                logger.debug(f"Error updating overlay: {e}")

    def _schedule_hide(self, delay_seconds: float) -> None:
        """Schedule auto-hide after delay."""
        if self._hide_timer:
            self._hide_timer.cancel()

        self._hide_timer = threading.Timer(delay_seconds, self.hide)
        self._hide_timer.daemon = True
        self._hide_timer.start()

    def _show_windows(self, text: str, overlay_type: OverlayType) -> None:
        """Show overlay on Windows using Win32 API."""
        # For now, we'll use a simple console output approach
        # A full implementation would create a layered window

        # Type-specific styling
        prefix = {
            OverlayType.LISTENING: "🎤",
            OverlayType.PROCESSING: "⏳",
            OverlayType.INSERTED: "✓",
            OverlayType.ERROR: "❌",
        }.get(overlay_type, "")

        logger.info(f"{prefix} {text}")

    def destroy(self) -> None:
        """Destroy the overlay window."""
        self.hide()

        if self._hwnd:
            try:
                ctypes.windll.user32.DestroyWindow(self._hwnd)
            except Exception:
                pass
            self._hwnd = None


class ToastNotification:
    """Toast notification manager using Windows notifications."""

    def __init__(self) -> None:
        self._app_id = "KeyMuse"

    def show(
        self,
        title: str,
        message: str,
        duration_ms: int = 3000,
    ) -> None:
        """Show a toast notification.

        Args:
            title: Notification title.
            message: Notification body.
            duration_ms: How long to show (Windows may ignore this).
        """
        if sys.platform == "win32":
            self._show_windows_toast(title, message)
        else:
            # Fallback: console output
            logger.info(f"Toast: {title} - {message}")

    def _show_windows_toast(self, title: str, message: str) -> None:
        """Show toast using Windows notification system."""
        try:
            # Try using win10toast if available
            from win10toast import ToastNotifier

            toaster = ToastNotifier()
            toaster.show_toast(
                title,
                message,
                duration=3,
                threaded=True,
            )
        except ImportError:
            # Fallback to simple balloon tip via shell
            logger.info(f"Toast: {title} - {message}")


class OverlayManager:
    """Manages overlay and toast notifications.

    This provides a unified interface for showing visual feedback
    during dictation operations.
    """

    def __init__(self, config: Optional[OverlayConfig] = None) -> None:
        """Initialize the overlay manager.

        Args:
            config: Overlay configuration.
        """
        self._overlay = OverlayWindow(config)
        self._toast = ToastNotification()

    def show_listening(self) -> None:
        """Show the listening indicator."""
        self._overlay.show(
            "Listening...",
            OverlayType.LISTENING,
            auto_hide=False,
        )

    def show_processing(self) -> None:
        """Show the processing indicator."""
        self._overlay.show(
            "Processing...",
            OverlayType.PROCESSING,
            auto_hide=False,
        )

    def show_inserted(self, text: str) -> None:
        """Show insertion success notification.

        Args:
            text: Preview of inserted text.
        """
        preview = text[:30] + "..." if len(text) > 30 else text
        self._overlay.show(
            f"Inserted: {preview}",
            OverlayType.INSERTED,
            auto_hide=True,
        )

    def show_error(self, message: str) -> None:
        """Show error notification.

        Args:
            message: Error message.
        """
        self._overlay.show(
            f"Error: {message}",
            OverlayType.ERROR,
            auto_hide=True,
        )

    def update_partial(self, text: str) -> None:
        """Update with partial transcription.

        Args:
            text: Partial transcription text.
        """
        self._overlay.update_text(text or "Listening...")

    def hide(self) -> None:
        """Hide any visible overlay."""
        self._overlay.hide()

    def destroy(self) -> None:
        """Clean up resources."""
        self._overlay.destroy()


class MockOverlayManager:
    """Mock overlay manager for testing."""

    def __init__(self, config: Optional[OverlayConfig] = None) -> None:
        self.shown: list[tuple[str, OverlayType]] = []
        self.partials: list[str] = []

    def show_listening(self) -> None:
        self.shown.append(("Listening...", OverlayType.LISTENING))

    def show_processing(self) -> None:
        self.shown.append(("Processing...", OverlayType.PROCESSING))

    def show_inserted(self, text: str) -> None:
        self.shown.append((f"Inserted: {text}", OverlayType.INSERTED))

    def show_error(self, message: str) -> None:
        self.shown.append((f"Error: {message}", OverlayType.ERROR))

    def update_partial(self, text: str) -> None:
        self.partials.append(text)

    def hide(self) -> None:
        pass

    def destroy(self) -> None:
        pass


__all__ = [
    "OverlayType",
    "OverlayConfig",
    "OverlayWindow",
    "ToastNotification",
    "OverlayManager",
    "MockOverlayManager",
]
