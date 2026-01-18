"""Keyboard input injection using Windows SendInput API.

This module provides functions to simulate keyboard input, primarily
for sending Ctrl+V to paste clipboard contents.
"""

from __future__ import annotations

import ctypes
import logging
import sys
import time
from ctypes import wintypes
from typing import Optional

logger = logging.getLogger(__name__)

# Virtual key codes
VK_CONTROL = 0x11
VK_V = 0x56
VK_SHIFT = 0x10
VK_MENU = 0x12  # Alt

# Scan codes
SCAN_CONTROL = 0x1D
SCAN_V = 0x2F

# Input type constants
INPUT_KEYBOARD = 1

# Key event flags
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_SCANCODE = 0x0008
KEYEVENTF_UNICODE = 0x0004


if sys.platform == "win32":
    # Define INPUT structure for SendInput

    ULONG_PTR = getattr(wintypes, "ULONG_PTR", ctypes.c_size_t)

    class KEYBDINPUT(ctypes.Structure):
        _fields_ = [
            ("wVk", wintypes.WORD),
            ("wScan", wintypes.WORD),
            ("dwFlags", wintypes.DWORD),
            ("time", wintypes.DWORD),
            ("dwExtraInfo", ULONG_PTR),
        ]

    class INPUT(ctypes.Structure):
        class _INPUT_UNION(ctypes.Union):
            _fields_ = [
                ("ki", KEYBDINPUT),
            ]

        _anonymous_ = ("_input",)
        _fields_ = [
            ("type", wintypes.DWORD),
            ("_input", _INPUT_UNION),
        ]


def _create_key_input(
    vk: int,
    scan: int = 0,
    flags: int = 0,
) -> "INPUT":
    """Create an INPUT structure for a key event."""
    if sys.platform != "win32":
        raise RuntimeError("Keyboard injection only available on Windows")

    input_struct = INPUT()
    input_struct.type = INPUT_KEYBOARD
    input_struct.ki.wVk = vk
    input_struct.ki.wScan = scan
    input_struct.ki.dwFlags = flags
    input_struct.ki.time = 0
    input_struct.ki.dwExtraInfo = 0

    return input_struct


def _send_input(inputs: "INPUT", count: int) -> bool:
    ctypes.windll.user32.SendInput.argtypes = [
        wintypes.UINT,
        ctypes.POINTER(INPUT),
        ctypes.c_int,
    ]
    ctypes.windll.user32.SendInput.restype = wintypes.UINT

    result = ctypes.windll.user32.SendInput(
        count,
        inputs,
        ctypes.sizeof(INPUT),
    )
    if result != count:
        error = ctypes.get_last_error()
        logger.error("SendInput failed (sent=%s, error=%s)", result, error)
        return False
    return True


def send_key_down(vk: int, scan: int = 0) -> bool:
    """Send a key down event.

    Args:
        vk: Virtual key code.
        scan: Scan code (optional).

    Returns:
        True if successful.
    """
    if sys.platform != "win32":
        logger.warning("Keyboard injection not available on this platform")
        return False

    if scan == 0:
        try:
            ctypes.windll.user32.keybd_event(vk, 0, 0, 0)
            return True
        except Exception as e:
            logger.error("keybd_event failed: %s", e)
            return False

    flags = KEYEVENTF_SCANCODE
    input_struct = _create_key_input(0, scan, flags)
    inputs = (INPUT * 1)(input_struct)

    return _send_input(inputs, 1)


def send_key_up(vk: int, scan: int = 0) -> bool:
    """Send a key up event.

    Args:
        vk: Virtual key code.
        scan: Scan code (optional).

    Returns:
        True if successful.
    """
    if sys.platform != "win32":
        logger.warning("Keyboard injection not available on this platform")
        return False

    if scan == 0:
        try:
            ctypes.windll.user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)
            return True
        except Exception as e:
            logger.error("keybd_event failed: %s", e)
            return False

    flags = KEYEVENTF_SCANCODE | KEYEVENTF_KEYUP
    input_struct = _create_key_input(0, scan, flags)
    inputs = (INPUT * 1)(input_struct)

    return _send_input(inputs, 1)


def send_key_press(vk: int, scan: int = 0, delay_ms: float = 10) -> bool:
    """Send a key press (down + up) event.

    Args:
        vk: Virtual key code.
        scan: Scan code (optional).
        delay_ms: Delay between down and up in milliseconds.

    Returns:
        True if both events were successful.
    """
    down_ok = send_key_down(vk, scan)
    if delay_ms > 0:
        time.sleep(delay_ms / 1000)
    up_ok = send_key_up(vk, scan)
    return down_ok and up_ok


def send_ctrl_v(delay_ms: float = 10) -> bool:
    """Send Ctrl+V keyboard shortcut to paste from clipboard.

    Args:
        delay_ms: Delay between key events in milliseconds.

    Returns:
        True if all events were successful.
    """
    if sys.platform != "win32":
        logger.warning("Keyboard injection not available on this platform")
        return False

    try:
        # Press Ctrl
        if not send_key_down(VK_CONTROL):
            logger.error("Failed to send Ctrl down")
            return False

        time.sleep(delay_ms / 1000)

        # Press V
        if not send_key_down(VK_V):
            logger.error("Failed to send V down")
            send_key_up(VK_CONTROL)  # Release Ctrl
            return False

        time.sleep(delay_ms / 1000)

        # Release V
        if not send_key_up(VK_V):
            logger.error("Failed to send V up")

        time.sleep(delay_ms / 1000)

        # Release Ctrl
        if not send_key_up(VK_CONTROL):
            logger.error("Failed to send Ctrl up")
            return False

        return True

    except Exception as e:
        logger.error(f"Error sending Ctrl+V: {e}")
        # Try to release any held keys
        send_key_up(VK_V)
        send_key_up(VK_CONTROL)
        return False


def send_unicode_string(text: str, delay_ms: float = 5) -> bool:
    """Send a string of Unicode characters as keyboard input.

    This uses the KEYEVENTF_UNICODE flag to send characters directly,
    bypassing virtual key codes. Useful for special characters.

    Args:
        text: The text to send.
        delay_ms: Delay between characters in milliseconds.

    Returns:
        True if all characters were sent successfully.
    """
    if sys.platform != "win32":
        logger.warning("Keyboard injection not available on this platform")
        return False

    success = True

    for char in text:
        # Create down event
        down_input = INPUT()
        down_input.type = INPUT_KEYBOARD
        down_input.ki.wVk = 0
        down_input.ki.wScan = ord(char)
        down_input.ki.dwFlags = KEYEVENTF_UNICODE
        down_input.ki.time = 0
        down_input.ki.dwExtraInfo = 0

        # Create up event
        up_input = INPUT()
        up_input.type = INPUT_KEYBOARD
        up_input.ki.wVk = 0
        up_input.ki.wScan = ord(char)
        up_input.ki.dwFlags = KEYEVENTF_UNICODE | KEYEVENTF_KEYUP
        up_input.ki.time = 0
        up_input.ki.dwExtraInfo = 0

        inputs = (INPUT * 2)(down_input, up_input)

        if not _send_input(inputs, 2):
            success = False

        if delay_ms > 0:
            time.sleep(delay_ms / 1000)

    return success


class MockKeyboard:
    """Mock keyboard for testing on non-Windows platforms."""

    def __init__(self):
        self.events: list[tuple[str, int]] = []

    def send_key_down(self, vk: int) -> bool:
        self.events.append(("down", vk))
        return True

    def send_key_up(self, vk: int) -> bool:
        self.events.append(("up", vk))
        return True

    def send_ctrl_v(self) -> bool:
        self.events.append(("combo", VK_CONTROL))
        self.events.append(("combo", VK_V))
        return True

    def clear(self):
        self.events.clear()


__all__ = [
    "VK_CONTROL",
    "VK_V",
    "VK_SHIFT",
    "VK_MENU",
    "send_key_down",
    "send_key_up",
    "send_key_press",
    "send_ctrl_v",
    "send_unicode_string",
]
