"""Tests for keyboard injection helpers."""

from __future__ import annotations

import sys

import pytest

from keymuse_client.insertion import keyboard


def test_send_ctrl_v_non_windows_returns_false():
    if sys.platform == "win32":
        pytest.skip("Non-Windows behavior only")

    assert keyboard.send_ctrl_v() is False


def test_send_unicode_string_non_windows_returns_false():
    if sys.platform == "win32":
        pytest.skip("Non-Windows behavior only")

    assert keyboard.send_unicode_string("hello") is False


def test_mock_keyboard_records_events():
    mock = keyboard.MockKeyboard()

    assert mock.send_key_down(keyboard.VK_CONTROL)
    assert mock.send_key_up(keyboard.VK_CONTROL)
    assert mock.send_ctrl_v()

    assert mock.events == [
        ("down", keyboard.VK_CONTROL),
        ("up", keyboard.VK_CONTROL),
        ("combo", keyboard.VK_CONTROL),
        ("combo", keyboard.VK_V),
    ]
