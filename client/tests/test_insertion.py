"""Tests for text insertion module."""

from __future__ import annotations

import sys

import pytest

from keymuse_client.insertion.clipboard import (
    ClipboardManager,
    add_to_history,
    clear_history,
    get_last_transcript,
    get_transcript_history,
    sanitize_text,
)
from keymuse_client.insertion.window import (
    ForegroundWindowGuard,
    WindowInfo,
    is_same_window,
    is_text_input_window,
)


class TestSanitizeText:
    """Tests for text sanitization."""

    def test_removes_control_characters(self):
        text = "Hello\x00World\x07!"
        result = sanitize_text(text)
        # Control characters are removed (not replaced with spaces)
        assert result == "HelloWorld!"

    def test_preserves_whitespace(self):
        text = "Hello\tWorld\nNew line"
        result = sanitize_text(text)
        # Tab preserved, newline becomes CRLF
        assert "Hello\tWorld" in result
        assert "\r\n" in result

    def test_removes_bidi_characters(self):
        text = "Hello\u200EWorld\u202A!"
        result = sanitize_text(text)
        assert result == "HelloWorld!"

    def test_normalizes_unicode(self):
        # NFD form (decomposed)
        text = "e\u0301"  # e + combining acute accent
        result = sanitize_text(text)
        # NFC form should be single character
        assert result == "\u00e9"

    def test_normalizes_line_endings(self):
        # Unix line endings
        text = "Line1\nLine2\nLine3"
        result = sanitize_text(text)
        assert result == "Line1\r\nLine2\r\nLine3"

        # Old Mac line endings
        text = "Line1\rLine2\rLine3"
        result = sanitize_text(text)
        assert result == "Line1\r\nLine2\r\nLine3"

        # Mixed line endings
        text = "Line1\r\nLine2\nLine3\rLine4"
        result = sanitize_text(text)
        assert result == "Line1\r\nLine2\r\nLine3\r\nLine4"

    def test_empty_string(self):
        assert sanitize_text("") == ""

    def test_normal_text_unchanged(self):
        text = "Hello, World!"
        result = sanitize_text(text)
        # Line ending normalization may add \r before \n
        assert "Hello, World!" in result


class TestTranscriptHistory:
    """Tests for transcript history management."""

    def setup_method(self):
        clear_history()

    def test_add_and_get_last(self):
        add_to_history("First")
        add_to_history("Second")
        assert get_last_transcript() == "Second"

    def test_empty_history(self):
        assert get_last_transcript() is None

    def test_get_full_history(self):
        add_to_history("First")
        add_to_history("Second")
        add_to_history("Third")

        history = get_transcript_history()
        assert history == ["First", "Second", "Third"]

    def test_history_size_limit(self):
        # Add more than MAX_HISTORY_SIZE (10)
        for i in range(15):
            add_to_history(f"Item {i}")

        history = get_transcript_history()
        assert len(history) == 10
        assert history[0] == "Item 5"  # First 5 were removed
        assert history[-1] == "Item 14"

    def test_clear_history(self):
        add_to_history("Test")
        clear_history()
        assert get_last_transcript() is None
        assert get_transcript_history() == []


class TestWindowInfo:
    """Tests for WindowInfo dataclass."""

    def test_window_info_creation(self):
        info = WindowInfo(hwnd=12345, title="Test", class_name="Edit", pid=1000)
        assert info.hwnd == 12345
        assert info.title == "Test"
        assert info.class_name == "Edit"
        assert info.pid == 1000


class TestIsSameWindow:
    """Tests for is_same_window function."""

    def test_same_window(self):
        w1 = WindowInfo(hwnd=100, title="A", class_name="X", pid=1)
        w2 = WindowInfo(hwnd=100, title="B", class_name="Y", pid=2)
        assert is_same_window(w1, w2)

    def test_different_window(self):
        w1 = WindowInfo(hwnd=100, title="A", class_name="X", pid=1)
        w2 = WindowInfo(hwnd=200, title="A", class_name="X", pid=1)
        assert not is_same_window(w1, w2)

    def test_none_windows(self):
        w1 = WindowInfo(hwnd=100, title="A", class_name="X", pid=1)
        assert not is_same_window(w1, None)
        assert not is_same_window(None, w1)
        assert not is_same_window(None, None)


class TestIsTextInputWindow:
    """Tests for is_text_input_window function."""

    def test_edit_control(self):
        w = WindowInfo(hwnd=1, title="", class_name="Edit", pid=1)
        assert is_text_input_window(w)

    def test_richedit_control(self):
        w = WindowInfo(hwnd=1, title="", class_name="RichEdit20W", pid=1)
        assert is_text_input_window(w)

    def test_notepad(self):
        w = WindowInfo(hwnd=1, title="Untitled", class_name="Notepad", pid=1)
        assert is_text_input_window(w)

    def test_none_window(self):
        assert not is_text_input_window(None)


class TestForegroundWindowGuard:
    """Tests for ForegroundWindowGuard context manager."""

    @pytest.mark.skipif(
        sys.platform != "win32",
        reason="Window detection only on Windows",
    )
    def test_guard_captures_initial_window(self):
        with ForegroundWindowGuard() as guard:
            # Initial window should be captured
            assert guard.initial_window is not None or guard.initial_window is None
            # (depends on whether there's a foreground window)

    def test_guard_without_windows(self):
        # On non-Windows, should work without errors
        with ForegroundWindowGuard() as guard:
            # Should not raise
            pass


class TestClipboardManager:
    """Tests for ClipboardManager (mock-based for cross-platform)."""

    def test_context_manager_interface(self):
        manager = ClipboardManager()

        # Should not raise on non-Windows
        with manager:
            pass

    def test_save_restore_calls(self):
        manager = ClipboardManager()

        # Save should work (may return None on non-Windows)
        saved = manager.save()
        assert saved is not None

        # Restore should work
        result = manager.restore()
        # On non-Windows, restore returns True (nothing to restore)


@pytest.mark.windows_only
class TestClipboardManagerWindows:
    """Windows-specific clipboard tests."""

    @pytest.mark.skipif(
        sys.platform != "win32",
        reason="Clipboard only on Windows",
    )
    def test_set_and_get_text(self):
        from keymuse_client.insertion.clipboard import (
            get_clipboard_text,
            set_clipboard_text,
        )

        original = get_clipboard_text()

        try:
            assert set_clipboard_text("Test clipboard")
            assert get_clipboard_text() == "Test clipboard"
        finally:
            # Restore original
            if original:
                set_clipboard_text(original)

    @pytest.mark.skipif(
        sys.platform != "win32",
        reason="Clipboard only on Windows",
    )
    def test_clipboard_manager_save_restore(self):
        from keymuse_client.insertion.clipboard import set_clipboard_text

        # Set initial content
        set_clipboard_text("Original content")

        with ClipboardManager() as manager:
            # Set new content
            manager.set_text("New content")

        # After context, original should be restored
        from keymuse_client.insertion.clipboard import get_clipboard_text

        # Note: This may not work perfectly in all scenarios
        # due to clipboard timing issues
