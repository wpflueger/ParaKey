"""System tray icon for KeyMuse.

This module provides a system tray icon that shows the current
dictation state and provides a menu for common actions.
"""

from __future__ import annotations

import logging
import threading
from enum import Enum, auto
from typing import Callable, Optional

from PIL import Image, ImageDraw

logger = logging.getLogger(__name__)


class TrayIconState(Enum):
    """Visual state of the tray icon."""

    IDLE = auto()  # Gray - ready
    RECORDING = auto()  # Red - actively recording
    PROCESSING = auto()  # Orange - processing audio
    ERROR = auto()  # Red X - error occurred


# Icon colors
COLORS = {
    TrayIconState.IDLE: "#808080",  # Gray
    TrayIconState.RECORDING: "#FF0000",  # Red
    TrayIconState.PROCESSING: "#FFA500",  # Orange
    TrayIconState.ERROR: "#FF0000",  # Red
}


def create_icon_image(state: TrayIconState, size: int = 64) -> Image.Image:
    """Create an icon image for the given state.

    Args:
        state: The state to visualize.
        size: Icon size in pixels.

    Returns:
        PIL Image of the icon.
    """
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    # Get color for state
    color = COLORS.get(state, COLORS[TrayIconState.IDLE])

    # Draw main circle
    padding = size // 8
    draw.ellipse(
        [padding, padding, size - padding, size - padding],
        fill=color,
    )

    # Draw state-specific elements
    if state == TrayIconState.RECORDING:
        # Inner white circle to make it look like a recording indicator
        inner_padding = size // 3
        draw.ellipse(
            [inner_padding, inner_padding, size - inner_padding, size - inner_padding],
            fill="#FFFFFF",
        )
        # Red center
        center_padding = size // 2.5
        draw.ellipse(
            [center_padding, center_padding, size - center_padding, size - center_padding],
            fill="#FF0000",
        )

    elif state == TrayIconState.ERROR:
        # Draw X overlay
        line_width = max(2, size // 16)
        offset = size // 4
        draw.line(
            [offset, offset, size - offset, size - offset],
            fill="#FFFFFF",
            width=line_width,
        )
        draw.line(
            [size - offset, offset, offset, size - offset],
            fill="#FFFFFF",
            width=line_width,
        )

    elif state == TrayIconState.PROCESSING:
        # Draw spinning indicator (static for now)
        inner_padding = size // 4
        draw.arc(
            [inner_padding, inner_padding, size - inner_padding, size - inner_padding],
            start=0,
            end=270,
            fill="#FFFFFF",
            width=max(2, size // 16),
        )

    return image


class SystemTray:
    """System tray icon manager.

    This class manages the system tray icon, updating it based on
    dictation state and providing a context menu for user actions.
    """

    def __init__(
        self,
        on_quit: Optional[Callable[[], None]] = None,
        on_settings: Optional[Callable[[], None]] = None,
        on_copy_last: Optional[Callable[[], None]] = None,
    ) -> None:
        """Initialize the system tray.

        Args:
            on_quit: Callback when user selects Quit from menu.
            on_settings: Callback when user selects Settings from menu.
            on_copy_last: Callback when user selects Copy Last Transcript.
        """
        self._on_quit = on_quit
        self._on_settings = on_settings
        self._on_copy_last = on_copy_last
        self._state = TrayIconState.IDLE
        self._icon = None
        self._thread: Optional[threading.Thread] = None
        self._running = False

    @property
    def state(self) -> TrayIconState:
        """Get the current icon state."""
        return self._state

    def set_state(self, state: TrayIconState) -> None:
        """Update the tray icon state.

        Args:
            state: New state to display.
        """
        if self._state != state:
            self._state = state
            self._update_icon()

    def _update_icon(self) -> None:
        """Update the tray icon image."""
        if self._icon is None:
            return

        try:
            self._icon.icon = create_icon_image(self._state)
            logger.debug(f"Tray icon updated to {self._state.name}")
        except Exception as e:
            logger.error(f"Failed to update tray icon: {e}")

    def _create_menu(self):
        """Create the tray icon menu."""
        try:
            import pystray

            menu_items = []

            # Status item (disabled, shows current state)
            state_text = {
                TrayIconState.IDLE: "Ready",
                TrayIconState.RECORDING: "Recording...",
                TrayIconState.PROCESSING: "Processing...",
                TrayIconState.ERROR: "Error",
            }.get(self._state, "Unknown")

            menu_items.append(
                pystray.MenuItem(f"Status: {state_text}", None, enabled=False)
            )
            menu_items.append(pystray.Menu.SEPARATOR)

            # Copy Last Transcript
            if self._on_copy_last:
                menu_items.append(
                    pystray.MenuItem("Copy Last Transcript", self._handle_copy_last)
                )

            # Settings
            if self._on_settings:
                menu_items.append(
                    pystray.MenuItem("Settings...", self._handle_settings)
                )

            menu_items.append(pystray.Menu.SEPARATOR)

            # Quit
            menu_items.append(pystray.MenuItem("Quit", self._handle_quit))

            return pystray.Menu(*menu_items)

        except ImportError:
            logger.warning("pystray not available")
            return None

    def _handle_quit(self, icon, item):
        """Handle Quit menu item."""
        if self._on_quit:
            self._on_quit()
        self.stop()

    def _handle_settings(self, icon, item):
        """Handle Settings menu item."""
        if self._on_settings:
            self._on_settings()

    def _handle_copy_last(self, icon, item):
        """Handle Copy Last Transcript menu item."""
        if self._on_copy_last:
            self._on_copy_last()

    def _run_icon(self) -> None:
        """Run the tray icon (in separate thread)."""
        try:
            import pystray

            # Create icon
            self._icon = pystray.Icon(
                "KeyMuse",
                create_icon_image(self._state),
                "KeyMuse - Press Ctrl+Alt to dictate",
                menu=self._create_menu(),
            )

            logger.info("System tray icon starting")
            self._icon.run()
            logger.info("System tray icon stopped")

        except ImportError:
            logger.warning("pystray not installed, system tray disabled")
        except Exception as e:
            logger.error(f"System tray error: {e}")

    def start(self) -> None:
        """Start the system tray icon."""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(
            target=self._run_icon,
            daemon=True,
            name="TrayIconThread",
        )
        self._thread.start()
        logger.info("System tray started")

    def stop(self) -> None:
        """Stop the system tray icon."""
        if not self._running:
            return

        self._running = False

        if self._icon is not None:
            try:
                self._icon.stop()
            except Exception as e:
                logger.debug(f"Error stopping tray icon: {e}")

        self._icon = None
        logger.info("System tray stopped")

    def show_notification(
        self,
        title: str,
        message: str,
    ) -> None:
        """Show a notification balloon/toast.

        Args:
            title: Notification title.
            message: Notification message.
        """
        if self._icon is None:
            return

        try:
            self._icon.notify(message, title)
        except Exception as e:
            logger.debug(f"Failed to show notification: {e}")


class MockSystemTray:
    """Mock system tray for testing."""

    def __init__(self, **kwargs) -> None:
        self._state = TrayIconState.IDLE
        self._running = False
        self._notifications: list[tuple[str, str]] = []

    @property
    def state(self) -> TrayIconState:
        return self._state

    def set_state(self, state: TrayIconState) -> None:
        self._state = state

    def start(self) -> None:
        self._running = True

    def stop(self) -> None:
        self._running = False

    def show_notification(self, title: str, message: str) -> None:
        self._notifications.append((title, message))


__all__ = [
    "TrayIconState",
    "SystemTray",
    "MockSystemTray",
    "create_icon_image",
]
