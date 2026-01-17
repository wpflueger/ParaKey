"""Tests for hotkey system."""

from __future__ import annotations

import sys

import pytest

from keymuse_client.hotkeys.state_machine import (
    HotkeyController,
    HotkeyState,
    update_state,
)
from keymuse_client.hotkeys.win32_hook import (
    MockKeyboardHook,
    create_keyboard_hook,
)


class TestHotkeyState:
    """Tests for HotkeyState dataclass."""

    def test_default_state(self):
        state = HotkeyState()
        assert not state.ctrl_down
        assert not state.alt_down
        assert not state.is_active()

    def test_ctrl_only(self):
        state = HotkeyState(ctrl_down=True, alt_down=False)
        assert state.ctrl_down
        assert not state.alt_down
        assert not state.is_active()

    def test_alt_only(self):
        state = HotkeyState(ctrl_down=False, alt_down=True)
        assert not state.ctrl_down
        assert state.alt_down
        assert not state.is_active()

    def test_both_pressed(self):
        state = HotkeyState(ctrl_down=True, alt_down=True)
        assert state.ctrl_down
        assert state.alt_down
        assert state.is_active()

    def test_immutable(self):
        state = HotkeyState()
        with pytest.raises(Exception):  # FrozenInstanceError
            state.ctrl_down = True


class TestUpdateState:
    """Tests for the update_state function."""

    def test_update_ctrl(self):
        state = HotkeyState()
        new_state = update_state(state, ctrl_down=True, alt_down=False)
        assert new_state.ctrl_down
        assert not new_state.alt_down

    def test_update_both(self):
        state = HotkeyState()
        new_state = update_state(state, ctrl_down=True, alt_down=True)
        assert new_state.is_active()

    def test_original_unchanged(self):
        state = HotkeyState()
        update_state(state, ctrl_down=True, alt_down=True)
        assert not state.ctrl_down
        assert not state.alt_down


class TestMockKeyboardHook:
    """Tests for MockKeyboardHook."""

    def test_initial_state(self):
        hook = MockKeyboardHook()
        assert not hook.ctrl_down
        assert not hook.alt_down
        assert not hook.chord_active
        assert not hook.is_running

    def test_start_stop(self):
        hook = MockKeyboardHook()
        hook.start()
        assert hook.is_running
        hook.stop()
        assert not hook.is_running

    def test_simulate_lctrl(self):
        hook = MockKeyboardHook()
        hook.start()
        hook.simulate_key("lctrl", True)
        assert hook.ctrl_down
        assert not hook.chord_active

    def test_simulate_chord(self):
        events = []
        hook = MockKeyboardHook(on_chord_change=lambda active: events.append(active))
        hook.start()

        hook.simulate_key("lctrl", True)
        assert len(events) == 0

        hook.simulate_key("lalt", True)
        assert len(events) == 1
        assert events[-1] is True
        assert hook.chord_active

        hook.simulate_key("lctrl", False)
        assert len(events) == 2
        assert events[-1] is False
        assert not hook.chord_active

    def test_left_right_modifiers(self):
        hook = MockKeyboardHook()
        hook.start()

        # Right ctrl + left alt should work
        hook.simulate_key("rctrl", True)
        hook.simulate_key("lalt", True)
        assert hook.chord_active

        # Release right ctrl, press left ctrl - still active
        hook.simulate_key("rctrl", False)
        hook.simulate_key("lctrl", True)
        assert hook.chord_active


class TestCreateKeyboardHook:
    """Tests for create_keyboard_hook factory."""

    def test_create_mock(self):
        hook = create_keyboard_hook(use_mock=True)
        assert isinstance(hook, MockKeyboardHook)

    @pytest.mark.skipif(
        sys.platform != "win32",
        reason="Win32 hook only available on Windows",
    )
    def test_create_real_on_windows(self):
        from keymuse_client.hotkeys.win32_hook import Win32KeyboardHook

        hook = create_keyboard_hook(use_mock=False)
        assert isinstance(hook, Win32KeyboardHook)

    @pytest.mark.skipif(
        sys.platform == "win32",
        reason="Non-Windows platform test",
    )
    def test_create_falls_back_to_mock(self):
        # On non-Windows, should fall back to mock
        hook = create_keyboard_hook(use_mock=False)
        assert isinstance(hook, MockKeyboardHook)


class TestHotkeyController:
    """Tests for HotkeyController."""

    def test_initial_state(self):
        controller = HotkeyController(use_mock=True)
        assert not controller.is_active
        assert not controller.is_running
        assert controller.state == HotkeyState()

    def test_start_stop(self):
        controller = HotkeyController(use_mock=True)
        controller.start()
        assert controller.is_running
        controller.stop()
        assert not controller.is_running

    def test_callbacks(self):
        activate_count = 0
        deactivate_count = 0

        def on_activate():
            nonlocal activate_count
            activate_count += 1

        def on_deactivate():
            nonlocal deactivate_count
            deactivate_count += 1

        controller = HotkeyController(
            on_activate=on_activate,
            on_deactivate=on_deactivate,
            use_mock=True,
        )
        controller.start()

        mock_hook = controller.get_mock_hook()
        assert mock_hook is not None

        # Simulate chord activation
        mock_hook.simulate_key("lctrl", True)
        mock_hook.simulate_key("lalt", True)
        assert activate_count == 1
        assert controller.is_active

        # Simulate chord deactivation
        mock_hook.simulate_key("lctrl", False)
        assert deactivate_count == 1
        assert not controller.is_active

    def test_state_tracking(self):
        controller = HotkeyController(use_mock=True)
        controller.start()

        mock_hook = controller.get_mock_hook()
        assert mock_hook is not None

        # Initial state
        assert controller.state == HotkeyState(ctrl_down=False, alt_down=False)

        # After pressing Ctrl+Alt
        mock_hook.simulate_key("lctrl", True)
        mock_hook.simulate_key("ralt", True)

        # State should reflect pressed keys
        assert controller.state.ctrl_down
        assert controller.state.alt_down
        assert controller.state.is_active()


@pytest.mark.windows_only
class TestWin32KeyboardHook:
    """Tests for Win32KeyboardHook (Windows only)."""

    @pytest.mark.skipif(
        sys.platform != "win32",
        reason="Win32 hook only available on Windows",
    )
    def test_start_stop(self):
        from keymuse_client.hotkeys.win32_hook import Win32KeyboardHook

        events = []
        hook = Win32KeyboardHook(on_chord_change=lambda active: events.append(active))

        hook.start()
        assert hook.is_running

        # Give the hook thread time to start
        import time

        time.sleep(0.1)

        hook.stop()
        assert not hook.is_running
