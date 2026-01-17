"""Hotkey state machine and controller for KeyMuse.

This module provides:
- HotkeyState: Immutable state object tracking modifier keys
- HotkeyController: High-level controller that manages the keyboard hook
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Callable, Optional

from keymuse_client.hotkeys.win32_hook import (
    MockKeyboardHook,
    Win32KeyboardHook,
    create_keyboard_hook,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class HotkeyState:
    """Immutable hotkey state."""

    ctrl_down: bool = False
    alt_down: bool = False

    def is_active(self) -> bool:
        """Return True if the hotkey chord is active (Ctrl+Alt pressed)."""
        return self.ctrl_down and self.alt_down


def update_state(
    state: HotkeyState, ctrl_down: bool, alt_down: bool
) -> HotkeyState:
    """Create a new state with updated modifier values.

    Args:
        state: The current state.
        ctrl_down: Whether Ctrl is pressed.
        alt_down: Whether Alt is pressed.

    Returns:
        A new HotkeyState with the updated values.
    """
    return HotkeyState(ctrl_down=ctrl_down, alt_down=alt_down)


class HotkeyController:
    """High-level controller for hotkey detection.

    This controller wraps the low-level keyboard hook and provides
    async callbacks for hotkey state changes.
    """

    def __init__(
        self,
        on_activate: Optional[Callable[[], None]] = None,
        on_deactivate: Optional[Callable[[], None]] = None,
        debounce_ms: float = 40.0,
        use_mock: bool = False,
    ) -> None:
        """Initialize the hotkey controller.

        Args:
            on_activate: Callback when Ctrl+Alt chord is pressed.
            on_deactivate: Callback when chord is released.
            debounce_ms: Debounce window in milliseconds.
            use_mock: Use mock hook for testing.
        """
        self._on_activate = on_activate
        self._on_deactivate = on_deactivate
        self._state = HotkeyState()
        self._loop: Optional[asyncio.AbstractEventLoop] = None

        # Create the keyboard hook
        self._hook = create_keyboard_hook(
            on_chord_change=self._handle_chord_change,
            use_mock=use_mock,
            debounce_ms=debounce_ms,
        )

    @property
    def state(self) -> HotkeyState:
        """Get the current hotkey state."""
        return self._state

    @property
    def is_active(self) -> bool:
        """Return True if the hotkey is currently active."""
        return self._hook.chord_active

    @property
    def is_running(self) -> bool:
        """Return True if the controller is running."""
        return self._hook.is_running

    def _handle_chord_change(self, active: bool) -> None:
        """Handle chord state change from the hook.

        This is called from the hook thread, so we need to schedule
        callbacks to run in the main async event loop.
        """
        # Update state
        self._state = HotkeyState(
            ctrl_down=self._hook.ctrl_down,
            alt_down=self._hook.alt_down,
        )

        # Invoke the appropriate callback
        if active:
            logger.debug("Hotkey chord activated")
            if self._on_activate:
                self._schedule_callback(self._on_activate)
        else:
            logger.debug("Hotkey chord deactivated")
            if self._on_deactivate:
                self._schedule_callback(self._on_deactivate)

    def _schedule_callback(self, callback: Callable[[], None]) -> None:
        """Schedule a callback to run in the event loop."""
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(callback)
        else:
            # No event loop, call directly (for sync usage)
            try:
                callback()
            except Exception as e:
                logger.error(f"Error in hotkey callback: {e}")

    def start(self, loop: Optional[asyncio.AbstractEventLoop] = None) -> None:
        """Start listening for hotkeys.

        Args:
            loop: The event loop to schedule callbacks on.
                  If None, tries to get the running loop.
        """
        if loop is None:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                pass

        self._loop = loop
        self._hook.start()
        logger.info("Hotkey controller started")

    def stop(self) -> None:
        """Stop listening for hotkeys."""
        self._hook.stop()
        self._state = HotkeyState()
        logger.info("Hotkey controller stopped")

    def get_mock_hook(self) -> Optional[MockKeyboardHook]:
        """Get the mock hook for testing, if using mock mode.

        Returns:
            The MockKeyboardHook if using mock mode, None otherwise.
        """
        if isinstance(self._hook, MockKeyboardHook):
            return self._hook
        return None


__all__ = [
    "HotkeyState",
    "HotkeyController",
    "update_state",
]
