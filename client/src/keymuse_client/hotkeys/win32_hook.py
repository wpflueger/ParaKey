"""Low-level Windows keyboard hook for hotkey detection.

This module provides a Windows-specific keyboard hook that captures
key events at the system level using SetWindowsHookEx with WH_KEYBOARD_LL.
"""

from __future__ import annotations

import ctypes
import logging
import sys
import threading
import time
from ctypes import wintypes
from dataclasses import dataclass
from typing import Callable, Optional

logger = logging.getLogger(__name__)

# Only import win32 modules on Windows
if sys.platform == "win32":
    import win32api
    import win32con

    # Low-level keyboard hook constants
    WH_KEYBOARD_LL = 13
    WM_KEYDOWN = 0x0100
    WM_KEYUP = 0x0101
    WM_SYSKEYDOWN = 0x0104
    WM_SYSKEYUP = 0x0105

    # Virtual key codes
    VK_LCONTROL = 0xA2
    VK_RCONTROL = 0xA3
    VK_LMENU = 0xA4  # Left Alt
    VK_RMENU = 0xA5  # Right Alt

    # KBDLLHOOKSTRUCT flags
    LLKHF_INJECTED = 0x10
    LLKHF_LOWER_IL_INJECTED = 0x02


# Hook callback type - use pointer-sized integers for 64-bit compatibility
# LRESULT is pointer-sized (64-bit on x64 Windows)
LRESULT = ctypes.c_ssize_t
HOOKPROC = ctypes.CFUNCTYPE(
    LRESULT,
    ctypes.c_int,
    ctypes.c_size_t,  # WPARAM is pointer-sized
    ctypes.c_ssize_t,  # LPARAM is pointer-sized
)


@dataclass
class KeyEvent:
    """A keyboard event."""

    vk_code: int
    is_down: bool
    is_injected: bool
    timestamp: float


class Win32KeyboardHook:
    """Low-level keyboard hook for Windows.

    This class uses SetWindowsHookEx to capture keyboard events at the
    system level. It tracks Ctrl and Alt modifier keys and invokes a
    callback when the chord state changes.
    """

    def __init__(
        self,
        on_chord_change: Optional[Callable[[bool], None]] = None,
        debounce_ms: float = 40.0,
    ) -> None:
        """Initialize the keyboard hook.

        Args:
            on_chord_change: Callback invoked when Ctrl+Alt chord state changes.
                             Called with True when chord is pressed, False when released.
            debounce_ms: Debounce window in milliseconds.
        """
        self._on_chord_change = on_chord_change
        self._debounce_ms = debounce_ms

        # Modifier state tracking
        self._lctrl_down = False
        self._rctrl_down = False
        self._lalt_down = False
        self._ralt_down = False

        # Chord state
        self._chord_active = False
        self._last_transition_time = 0.0

        # Hook handle and thread
        self._hook_handle: Optional[int] = None
        self._hook_thread: Optional[threading.Thread] = None
        self._running = False

        # Keep reference to callback to prevent garbage collection
        self._hook_proc: Optional[HOOKPROC] = None

    @property
    def ctrl_down(self) -> bool:
        """Return True if either Ctrl key is pressed."""
        return self._lctrl_down or self._rctrl_down

    @property
    def alt_down(self) -> bool:
        """Return True if either Alt key is pressed."""
        return self._lalt_down or self._ralt_down

    @property
    def chord_active(self) -> bool:
        """Return True if Ctrl+Alt chord is currently active."""
        return self._chord_active

    @property
    def is_running(self) -> bool:
        """Return True if the hook is currently running."""
        return self._running

    def _call_next_hook(self, nCode: int, wParam: int, lParam: int) -> int:
        """Call the next hook in the chain with proper 64-bit types."""
        # Set up CallNextHookEx with proper types for 64-bit Windows
        CallNextHookEx = ctypes.windll.user32.CallNextHookEx
        CallNextHookEx.argtypes = [
            wintypes.HHOOK,
            ctypes.c_int,
            ctypes.c_size_t,   # WPARAM - pointer-sized unsigned
            ctypes.c_ssize_t,  # LPARAM - pointer-sized signed
        ]
        CallNextHookEx.restype = ctypes.c_ssize_t  # LRESULT
        return CallNextHookEx(self._hook_handle, nCode, wParam, lParam)

    def _low_level_handler(
        self,
        nCode: int,
        wParam: int,
        lParam: int,
    ) -> int:
        """Low-level keyboard hook callback.

        This is called for every keyboard event in the system.
        """
        if nCode < 0:
            return self._call_next_hook(nCode, wParam, lParam)

        # Extract key info from KBDLLHOOKSTRUCT
        # struct layout: vkCode, scanCode, flags, time, dwExtraInfo
        kbd_struct = ctypes.cast(
            lParam, ctypes.POINTER(ctypes.c_ulong * 5)
        ).contents
        vk_code = kbd_struct[0]
        flags = kbd_struct[2]

        # Check if this is an injected keystroke (from SendInput, etc.)
        is_injected = bool(flags & (LLKHF_INJECTED | LLKHF_LOWER_IL_INJECTED))

        # Ignore injected keystrokes to prevent self-triggering
        if is_injected:
            return self._call_next_hook(nCode, wParam, lParam)

        # Determine if key is down or up
        is_down = wParam in (WM_KEYDOWN, WM_SYSKEYDOWN)

        # Update modifier state
        if vk_code == VK_LCONTROL:
            self._lctrl_down = is_down
        elif vk_code == VK_RCONTROL:
            self._rctrl_down = is_down
        elif vk_code == VK_LMENU:
            self._lalt_down = is_down
        elif vk_code == VK_RMENU:
            self._ralt_down = is_down

        # Check chord state
        new_chord_active = self.ctrl_down and self.alt_down

        # Handle state transition with debouncing
        if new_chord_active != self._chord_active:
            now = time.perf_counter() * 1000  # Convert to ms
            elapsed = now - self._last_transition_time

            if elapsed >= self._debounce_ms:
                self._chord_active = new_chord_active
                self._last_transition_time = now

                if self._on_chord_change:
                    try:
                        self._on_chord_change(new_chord_active)
                    except Exception as e:
                        logger.error(f"Error in chord change callback: {e}")

        return self._call_next_hook(nCode, wParam, lParam)

    def _message_loop(self) -> None:
        """Run the Windows message loop for the hook."""
        # Create the hook callback (must keep reference)
        self._hook_proc = HOOKPROC(self._low_level_handler)

        # Install the hook
        self._hook_handle = ctypes.windll.user32.SetWindowsHookExW(
            WH_KEYBOARD_LL,
            self._hook_proc,
            None,  # Use calling thread's module
            0,  # Hook all threads
        )

        if not self._hook_handle:
            error = ctypes.get_last_error()
            logger.error(f"Failed to install keyboard hook: error {error}")
            self._running = False
            return

        logger.info("Keyboard hook installed successfully")

        # Message loop - required for the hook to receive events
        msg = wintypes.MSG()
        while self._running:
            result = ctypes.windll.user32.GetMessageW(
                ctypes.byref(msg), None, 0, 0
            )
            if result == 0:  # WM_QUIT
                break
            if result == -1:  # Error
                break
            ctypes.windll.user32.TranslateMessage(ctypes.byref(msg))
            ctypes.windll.user32.DispatchMessageW(ctypes.byref(msg))

        # Unhook
        if self._hook_handle:
            ctypes.windll.user32.UnhookWindowsHookEx(self._hook_handle)
            self._hook_handle = None
            logger.info("Keyboard hook removed")

    def start(self) -> None:
        """Start the keyboard hook.

        This starts a background thread that runs the Windows message loop
        and processes keyboard events.
        """
        if sys.platform != "win32":
            logger.warning("Keyboard hook only supported on Windows")
            return

        if self._running:
            return

        self._running = True
        self._hook_thread = threading.Thread(
            target=self._message_loop,
            daemon=True,
            name="KeyboardHookThread",
        )
        self._hook_thread.start()
        logger.info("Keyboard hook thread started")

    def stop(self) -> None:
        """Stop the keyboard hook."""
        if not self._running:
            return

        self._running = False

        # Post WM_QUIT to break the message loop
        if self._hook_thread and self._hook_thread.is_alive():
            # Post a quit message to the hook thread
            thread_id = self._hook_thread.ident
            if thread_id:
                ctypes.windll.user32.PostThreadMessageW(
                    thread_id, 0x0012, 0, 0  # WM_QUIT
                )
            self._hook_thread.join(timeout=1.0)

        # Reset state
        self._lctrl_down = False
        self._rctrl_down = False
        self._lalt_down = False
        self._ralt_down = False
        self._chord_active = False

        logger.info("Keyboard hook stopped")


class MockKeyboardHook:
    """Mock keyboard hook for testing (cross-platform)."""

    def __init__(
        self,
        on_chord_change: Optional[Callable[[bool], None]] = None,
        debounce_ms: float = 40.0,
    ) -> None:
        self._on_chord_change = on_chord_change
        self._debounce_ms = debounce_ms
        self._lctrl_down = False
        self._rctrl_down = False
        self._lalt_down = False
        self._ralt_down = False
        self._chord_active = False
        self._running = False

    @property
    def ctrl_down(self) -> bool:
        return self._lctrl_down or self._rctrl_down

    @property
    def alt_down(self) -> bool:
        return self._lalt_down or self._ralt_down

    @property
    def chord_active(self) -> bool:
        return self._chord_active

    @property
    def is_running(self) -> bool:
        return self._running

    def start(self) -> None:
        self._running = True

    def stop(self) -> None:
        self._running = False
        self._lctrl_down = False
        self._rctrl_down = False
        self._lalt_down = False
        self._ralt_down = False
        self._chord_active = False

    def simulate_key(self, key: str, is_down: bool) -> None:
        """Simulate a key press/release for testing.

        Args:
            key: One of 'lctrl', 'rctrl', 'lalt', 'ralt'
            is_down: True for key down, False for key up
        """
        if key == "lctrl":
            self._lctrl_down = is_down
        elif key == "rctrl":
            self._rctrl_down = is_down
        elif key == "lalt":
            self._lalt_down = is_down
        elif key == "ralt":
            self._ralt_down = is_down

        new_chord_active = self.ctrl_down and self.alt_down
        if new_chord_active != self._chord_active:
            self._chord_active = new_chord_active
            if self._on_chord_change:
                self._on_chord_change(new_chord_active)


def create_keyboard_hook(
    on_chord_change: Optional[Callable[[bool], None]] = None,
    use_mock: bool = False,
    debounce_ms: float = 40.0,
) -> Win32KeyboardHook | MockKeyboardHook:
    """Create a keyboard hook instance.

    Args:
        on_chord_change: Callback for chord state changes.
        use_mock: If True, use mock hook (for testing).
        debounce_ms: Debounce window in milliseconds.

    Returns:
        A keyboard hook instance.
    """
    if use_mock or sys.platform != "win32":
        return MockKeyboardHook(on_chord_change, debounce_ms)
    return Win32KeyboardHook(on_chord_change, debounce_ms)


__all__ = [
    "KeyEvent",
    "Win32KeyboardHook",
    "MockKeyboardHook",
    "create_keyboard_hook",
]
