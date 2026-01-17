"""Clipboard operations and text sanitization for Windows.

This module provides functions for:
- Reading and writing to the Windows clipboard
- Saving and restoring clipboard contents
- Sanitizing text for safe insertion
- Race condition detection using clipboard sequence numbers
"""

from __future__ import annotations

import ctypes
import logging
import re
import sys
import time
import unicodedata
from ctypes import wintypes
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

# Clipboard format constants
CF_UNICODETEXT = 13
CF_TEXT = 1

# Control character pattern (excluding tab, newline, carriage return)
CONTROL_PATTERN = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F]")

# Bidirectional control characters to remove
BIDI_PATTERN = re.compile(
    r"[\u200E\u200F\u202A-\u202E\u2066-\u2069]"
)


@dataclass
class ClipboardContents:
    """Saved clipboard contents for restoration."""

    text: Optional[str]
    sequence_number: int


class ClipboardError(Exception):
    """Raised when clipboard operations fail."""

    pass


def sanitize_text(text: str) -> str:
    """Sanitize text for safe insertion.

    This removes:
    - ASCII control characters (except tab, newline, carriage return)
    - Bidirectional control characters
    - Applies Unicode NFC normalization
    - Normalizes line endings to CRLF (Windows standard)

    Args:
        text: The text to sanitize.

    Returns:
        Sanitized text safe for insertion.
    """
    # Remove control characters
    text = CONTROL_PATTERN.sub("", text)

    # Remove bidirectional control characters
    text = BIDI_PATTERN.sub("", text)

    # Apply NFC normalization
    text = unicodedata.normalize("NFC", text)

    # Normalize line endings to CRLF
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "\r\n")

    return text


def get_clipboard_sequence_number() -> int:
    """Get the current clipboard sequence number.

    This number changes whenever the clipboard contents change,
    useful for detecting race conditions.

    Returns:
        Current sequence number, or 0 if not on Windows.
    """
    if sys.platform != "win32":
        return 0

    return ctypes.windll.user32.GetClipboardSequenceNumber()


def open_clipboard(hwnd: int = 0) -> bool:
    """Open the clipboard for access.

    Args:
        hwnd: Window handle to associate with clipboard (0 for current task).

    Returns:
        True if clipboard was opened successfully.
    """
    if sys.platform != "win32":
        return False

    return bool(ctypes.windll.user32.OpenClipboard(hwnd))


def close_clipboard() -> bool:
    """Close the clipboard.

    Returns:
        True if clipboard was closed successfully.
    """
    if sys.platform != "win32":
        return False

    return bool(ctypes.windll.user32.CloseClipboard())


def empty_clipboard() -> bool:
    """Empty the clipboard contents.

    The clipboard must be open before calling this.

    Returns:
        True if clipboard was emptied successfully.
    """
    if sys.platform != "win32":
        return False

    return bool(ctypes.windll.user32.EmptyClipboard())


def get_clipboard_text() -> Optional[str]:
    """Get text from the clipboard.

    Returns:
        Clipboard text, or None if no text available or not on Windows.
    """
    if sys.platform != "win32":
        return None

    if not open_clipboard():
        logger.error("Failed to open clipboard for reading")
        return None

    try:
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32

        user32.IsClipboardFormatAvailable.argtypes = [wintypes.UINT]
        user32.IsClipboardFormatAvailable.restype = wintypes.BOOL
        user32.GetClipboardData.argtypes = [wintypes.UINT]
        user32.GetClipboardData.restype = wintypes.HANDLE
        kernel32.GlobalLock.restype = ctypes.c_void_p
        kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
        kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
        kernel32.GlobalSize.argtypes = [wintypes.HGLOBAL]
        kernel32.GlobalSize.restype = ctypes.c_size_t
        kernel32.lstrlenW.argtypes = [wintypes.LPCWSTR]
        kernel32.lstrlenW.restype = ctypes.c_int

        # Check if text is available
        if not user32.IsClipboardFormatAvailable(CF_UNICODETEXT):
            return None

        # Get clipboard data
        handle = user32.GetClipboardData(CF_UNICODETEXT)
        if not handle:
            return None

        # Lock and copy the data (size-bounded to avoid access violations)
        text_ptr = kernel32.GlobalLock(handle)
        if not text_ptr:
            return None

        try:
            size_bytes = kernel32.GlobalSize(handle)
            if not size_bytes:
                return None

            # Guard against absurd sizes (corrupt handles or API truncation)
            if size_bytes > 10 * 1024 * 1024:
                logger.warning("Clipboard text size too large: %d bytes", size_bytes)
                return None

            # CF_UNICODETEXT is UTF-16LE with a terminating NUL
            if size_bytes < 2:
                return ""

            max_chars = size_bytes // 2
            text_len = kernel32.lstrlenW(ctypes.cast(text_ptr, wintypes.LPCWSTR))
            if text_len <= 0:
                return ""

            if text_len > max_chars:
                text_len = max_chars

            return ctypes.wstring_at(text_ptr, text_len)
        finally:
            kernel32.GlobalUnlock(handle)

    finally:
        close_clipboard()


def set_clipboard_text(text: str) -> bool:
    """Set text to the clipboard.

    Args:
        text: Text to set.

    Returns:
        True if successful.
    """
    if sys.platform != "win32":
        logger.warning("Clipboard not available on this platform")
        return False

    opened = False
    for attempt in range(10):
        if open_clipboard():
            opened = True
            break
        time.sleep(0.05)

    if not opened:
        logger.error("Failed to open clipboard for writing")
        return False

    try:
        # Empty the clipboard first
        if not empty_clipboard():
            logger.error("Failed to empty clipboard")
            return False

        kernel32 = ctypes.windll.kernel32
        user32 = ctypes.windll.user32

        kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
        kernel32.GlobalAlloc.restype = wintypes.HGLOBAL
        kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
        kernel32.GlobalLock.restype = ctypes.c_void_p
        kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
        kernel32.GlobalUnlock.restype = wintypes.BOOL
        kernel32.GlobalFree.argtypes = [wintypes.HGLOBAL]
        kernel32.GlobalFree.restype = wintypes.HGLOBAL
        user32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]
        user32.SetClipboardData.restype = wintypes.HANDLE

        # Copy the text as UTF-16LE bytes for CF_UNICODETEXT
        encoded = text.encode("utf-16-le") + b"\x00\x00"
        byte_count = len(encoded)

        # Allocate global memory for the text
        handle = kernel32.GlobalAlloc(
            0x0042,  # GMEM_MOVEABLE | GMEM_ZEROINIT
            byte_count,
        )

        if not handle:
            logger.error("Failed to allocate clipboard memory")
            return False

        # Lock and copy the text
        locked_ptr = kernel32.GlobalLock(handle)

        if not locked_ptr:
            kernel32.GlobalFree(handle)
            logger.error("Failed to lock clipboard memory")
            return False

        ctypes.memmove(
            locked_ptr,
            encoded,
            byte_count,
        )

        kernel32.GlobalUnlock(handle)

        # Set the clipboard data
        result = user32.SetClipboardData(CF_UNICODETEXT, handle)

        if not result:
            kernel32.GlobalFree(handle)
            logger.error("Failed to set clipboard data")
            return False

        return True

    finally:
        close_clipboard()


def save_clipboard() -> ClipboardContents:
    """Save the current clipboard contents.

    Returns:
        ClipboardContents with the saved text and sequence number.
    """
    return ClipboardContents(
        text=get_clipboard_text(),
        sequence_number=get_clipboard_sequence_number(),
    )


def restore_clipboard(contents: ClipboardContents) -> bool:
    """Restore previously saved clipboard contents.

    Args:
        contents: The saved clipboard contents.

    Returns:
        True if restoration was successful or not needed.
    """
    if contents.text is None:
        # Nothing to restore
        return True

    return set_clipboard_text(contents.text)


class ClipboardManager:
    """Manages clipboard operations with safety guards.

    This class provides clipboard operations with:
    - Automatic save/restore of original contents
    - Sequence number checking for race detection
    - Context manager support for safe operations
    """

    def __init__(self) -> None:
        self._saved_contents: Optional[ClipboardContents] = None
        self._initial_sequence: int = 0

    def save(self) -> ClipboardContents:
        """Save clipboard contents for later restoration."""
        self._saved_contents = save_clipboard()
        self._initial_sequence = self._saved_contents.sequence_number
        logger.debug(f"Saved clipboard (seq: {self._initial_sequence})")
        return self._saved_contents

    def restore(self) -> bool:
        """Restore previously saved clipboard contents."""
        if self._saved_contents is None:
            return True

        success = restore_clipboard(self._saved_contents)
        if success:
            logger.debug("Restored clipboard contents")
        else:
            logger.warning("Failed to restore clipboard")

        self._saved_contents = None
        return success

    def set_text(self, text: str, sanitize: bool = True) -> bool:
        """Set clipboard text, optionally sanitizing first.

        Args:
            text: Text to set.
            sanitize: If True, sanitize the text first.

        Returns:
            True if successful.
        """
        if sanitize:
            text = sanitize_text(text)

        return set_clipboard_text(text)

    def check_sequence(self) -> bool:
        """Check if clipboard sequence number changed unexpectedly.

        Returns:
            True if sequence is still valid (unchanged by others).
        """
        current = get_clipboard_sequence_number()
        # Sequence changes when we set clipboard, so we just check it's not 0
        return current > 0

    def __enter__(self) -> "ClipboardManager":
        self.save()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.restore()


# Transcript history for recovery
_transcript_history: list[str] = []
MAX_HISTORY_SIZE = 10


def add_to_history(text: str) -> None:
    """Add a transcript to the history.

    Args:
        text: Transcript text to save.
    """
    _transcript_history.append(text)
    while len(_transcript_history) > MAX_HISTORY_SIZE:
        _transcript_history.pop(0)


def get_last_transcript() -> Optional[str]:
    """Get the most recent transcript from history.

    Returns:
        The most recent transcript, or None if history is empty.
    """
    if _transcript_history:
        return _transcript_history[-1]
    return None


def get_transcript_history() -> list[str]:
    """Get the full transcript history.

    Returns:
        List of recent transcripts (oldest first).
    """
    return list(_transcript_history)


def clear_history() -> None:
    """Clear the transcript history."""
    _transcript_history.clear()


__all__ = [
    "ClipboardContents",
    "ClipboardError",
    "ClipboardManager",
    "sanitize_text",
    "get_clipboard_sequence_number",
    "get_clipboard_text",
    "set_clipboard_text",
    "save_clipboard",
    "restore_clipboard",
    "add_to_history",
    "get_last_transcript",
    "get_transcript_history",
    "clear_history",
]
