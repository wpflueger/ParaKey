"""Settings management for KeyMuse client.

This module provides:
- JSON-based settings persistence
- Default values and validation
- Settings UI (simple tkinter-based)
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


def get_settings_dir() -> Path:
    """Get the settings directory path.

    Returns:
        Path to settings directory (~/.keymuse on Unix, %APPDATA%/KeyMuse on Windows).
    """
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home()))
    else:
        base = Path.home() / ".config"

    settings_dir = base / "keymuse"
    settings_dir.mkdir(parents=True, exist_ok=True)
    return settings_dir


def get_settings_file() -> Path:
    """Get the settings file path."""
    return get_settings_dir() / "settings.json"


@dataclass
class HotkeySettings:
    """Settings for hotkey configuration."""

    # Modifier keys (virtual key codes)
    modifiers: list[int] = field(default_factory=lambda: [0xA2, 0xA4])  # Ctrl, Alt
    debounce_ms: float = 40.0


@dataclass
class AudioSettings:
    """Settings for audio capture."""

    device_index: Optional[int] = None  # None = default device
    device_name: Optional[str] = None  # For display purposes
    sample_rate_hz: int = 16000
    channels: int = 1
    frame_ms: int = 20


@dataclass
class BackendSettings:
    """Settings for backend connection."""

    host: str = "127.0.0.1"
    port: int = 50051
    timeout_seconds: float = 30.0
    auto_reconnect: bool = True


@dataclass
class OverlaySettings:
    """Settings for overlay display."""

    enabled: bool = True
    position: str = "top-right"  # top-left, top-right, bottom-left, bottom-right
    x_offset: int = 20
    y_offset: int = 20
    auto_hide_ms: int = 2000


@dataclass
class AppSettings:
    """All application settings."""

    hotkey: HotkeySettings = field(default_factory=HotkeySettings)
    audio: AudioSettings = field(default_factory=AudioSettings)
    backend: BackendSettings = field(default_factory=BackendSettings)
    overlay: OverlaySettings = field(default_factory=OverlaySettings)

    # General settings
    start_minimized: bool = True
    show_notifications: bool = True


def _dict_to_settings(data: dict[str, Any]) -> AppSettings:
    """Convert a dictionary to AppSettings.

    Args:
        data: Dictionary from JSON.

    Returns:
        AppSettings instance.
    """
    return AppSettings(
        hotkey=HotkeySettings(**data.get("hotkey", {})),
        audio=AudioSettings(**data.get("audio", {})),
        backend=BackendSettings(**data.get("backend", {})),
        overlay=OverlaySettings(**data.get("overlay", {})),
        start_minimized=data.get("start_minimized", True),
        show_notifications=data.get("show_notifications", True),
    )


def load_settings() -> AppSettings:
    """Load settings from file.

    Returns:
        AppSettings, either from file or defaults.
    """
    settings_file = get_settings_file()

    if settings_file.exists():
        try:
            with open(settings_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            logger.info(f"Loaded settings from {settings_file}")
            return _dict_to_settings(data)
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.warning(f"Failed to load settings: {e}, using defaults")

    return AppSettings()


def save_settings(settings: AppSettings) -> bool:
    """Save settings to file.

    Args:
        settings: Settings to save.

    Returns:
        True if successful.
    """
    settings_file = get_settings_file()

    try:
        data = asdict(settings)
        with open(settings_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        logger.info(f"Saved settings to {settings_file}")
        return True
    except (OSError, TypeError) as e:
        logger.error(f"Failed to save settings: {e}")
        return False


class SettingsManager:
    """Manages settings with caching and auto-save."""

    def __init__(self) -> None:
        self._settings: Optional[AppSettings] = None
        self._on_change: list[callable] = []

    @property
    def settings(self) -> AppSettings:
        """Get current settings, loading if needed."""
        if self._settings is None:
            self._settings = load_settings()
        return self._settings

    def reload(self) -> None:
        """Reload settings from file."""
        self._settings = load_settings()
        self._notify_change()

    def save(self) -> bool:
        """Save current settings to file."""
        if self._settings is None:
            return True
        return save_settings(self._settings)

    def update(self, **kwargs) -> None:
        """Update settings and save.

        Args:
            **kwargs: Setting values to update.
        """
        settings = self.settings

        for key, value in kwargs.items():
            if hasattr(settings, key):
                setattr(settings, key, value)

        self.save()
        self._notify_change()

    def on_change(self, callback: callable) -> None:
        """Register a callback for settings changes.

        Args:
            callback: Function to call when settings change.
        """
        self._on_change.append(callback)

    def _notify_change(self) -> None:
        """Notify all registered callbacks."""
        for callback in self._on_change:
            try:
                callback(self.settings)
            except Exception as e:
                logger.error(f"Error in settings change callback: {e}")


# Global settings manager instance
_settings_manager: Optional[SettingsManager] = None


def get_settings_manager() -> SettingsManager:
    """Get the global settings manager instance."""
    global _settings_manager
    if _settings_manager is None:
        _settings_manager = SettingsManager()
    return _settings_manager


def show_settings_dialog(parent=None) -> bool:
    """Show the settings dialog.

    Args:
        parent: Optional parent window. If provided, dialog will be modal.

    Returns:
        True if settings were changed.
    """
    try:
        import tkinter as tk
        from tkinter import ttk

        manager = get_settings_manager()
        settings = manager.settings
        changed = [False]

        # Create dialog as Toplevel if parent provided, otherwise standalone
        if parent is not None:
            dialog = tk.Toplevel(parent)
            dialog.transient(parent)  # Stay on top of parent
            dialog.grab_set()  # Make modal
        else:
            dialog = tk.Tk()

        dialog.title("KeyMuse Settings")
        dialog.geometry("400x350")
        dialog.resizable(False, False)

        # Center on parent or screen
        dialog.update_idletasks()
        if parent is not None:
            x = parent.winfo_x() + (parent.winfo_width() - 400) // 2
            y = parent.winfo_y() + (parent.winfo_height() - 350) // 2
            dialog.geometry(f"+{x}+{y}")

        # Configure background
        dialog.configure(bg="#1E1E1E")

        # Try to configure ttk styles
        try:
            from keymuse_client.ui.theme import configure_ttk_style
            configure_ttk_style(dialog)
        except ImportError:
            pass

        # Create notebook for tabs
        notebook = ttk.Notebook(dialog)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        # Audio tab
        audio_frame = ttk.Frame(notebook, padding=10)
        notebook.add(audio_frame, text="Audio")

        ttk.Label(audio_frame, text="Microphone:").grid(row=0, column=0, sticky="w", pady=5)
        device_var = tk.StringVar(value=settings.audio.device_name or "Default")
        device_combo = ttk.Combobox(audio_frame, textvariable=device_var, width=30)

        # Try to populate device list
        try:
            from keymuse_client.audio.devices import list_input_devices
            devices = ["Default"] + [d.name for d in list_input_devices()]
            device_combo["values"] = devices
        except Exception:
            device_combo["values"] = ["Default"]

        device_combo.grid(row=0, column=1, pady=5)

        # Backend tab
        backend_frame = ttk.Frame(notebook, padding=10)
        notebook.add(backend_frame, text="Backend")

        ttk.Label(backend_frame, text="Host:").grid(row=0, column=0, sticky="w", pady=5)
        host_var = tk.StringVar(value=settings.backend.host)
        ttk.Entry(backend_frame, textvariable=host_var, width=20).grid(row=0, column=1, pady=5)

        ttk.Label(backend_frame, text="Port:").grid(row=1, column=0, sticky="w", pady=5)
        port_var = tk.StringVar(value=str(settings.backend.port))
        ttk.Entry(backend_frame, textvariable=port_var, width=10).grid(row=1, column=1, sticky="w", pady=5)

        auto_reconnect_var = tk.BooleanVar(value=settings.backend.auto_reconnect)
        ttk.Checkbutton(
            backend_frame,
            text="Auto-reconnect",
            variable=auto_reconnect_var,
        ).grid(row=2, column=0, columnspan=2, sticky="w", pady=5)

        # Overlay tab
        overlay_frame = ttk.Frame(notebook, padding=10)
        notebook.add(overlay_frame, text="Overlay")

        overlay_enabled_var = tk.BooleanVar(value=settings.overlay.enabled)
        ttk.Checkbutton(
            overlay_frame,
            text="Show overlay",
            variable=overlay_enabled_var,
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=5)

        ttk.Label(overlay_frame, text="Position:").grid(row=1, column=0, sticky="w", pady=5)
        position_var = tk.StringVar(value=settings.overlay.position)
        position_combo = ttk.Combobox(
            overlay_frame,
            textvariable=position_var,
            values=["top-left", "top-right", "bottom-left", "bottom-right"],
            width=15,
        )
        position_combo.grid(row=1, column=1, sticky="w", pady=5)

        # General tab
        general_frame = ttk.Frame(notebook, padding=10)
        notebook.add(general_frame, text="General")

        start_minimized_var = tk.BooleanVar(value=settings.start_minimized)
        ttk.Checkbutton(
            general_frame,
            text="Start minimized",
            variable=start_minimized_var,
        ).grid(row=0, column=0, sticky="w", pady=5)

        notifications_var = tk.BooleanVar(value=settings.show_notifications)
        ttk.Checkbutton(
            general_frame,
            text="Show notifications",
            variable=notifications_var,
        ).grid(row=1, column=0, sticky="w", pady=5)

        # Buttons
        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill="x", padx=10, pady=10)

        def save_and_close():
            # Update settings
            settings.audio.device_name = device_var.get() if device_var.get() != "Default" else None
            settings.backend.host = host_var.get()
            try:
                settings.backend.port = int(port_var.get())
            except ValueError:
                pass
            settings.backend.auto_reconnect = auto_reconnect_var.get()
            settings.overlay.enabled = overlay_enabled_var.get()
            settings.overlay.position = position_var.get()
            settings.start_minimized = start_minimized_var.get()
            settings.show_notifications = notifications_var.get()

            manager.save()
            changed[0] = True
            dialog.destroy()

        def cancel():
            dialog.destroy()

        ttk.Button(button_frame, text="Save", command=save_and_close).pack(side="right", padx=5)
        ttk.Button(button_frame, text="Cancel", command=cancel).pack(side="right")

        # Handle window close button
        dialog.protocol("WM_DELETE_WINDOW", cancel)

        # Run dialog
        if parent is not None:
            # Wait for dialog to close before returning
            parent.wait_window(dialog)
        else:
            dialog.mainloop()

        return changed[0]

    except ImportError:
        logger.warning("tkinter not available for settings dialog")
        return False
    except Exception as e:
        logger.error(f"Error showing settings dialog: {e}")
        return False


__all__ = [
    "AppSettings",
    "HotkeySettings",
    "AudioSettings",
    "BackendSettings",
    "OverlaySettings",
    "SettingsManager",
    "load_settings",
    "save_settings",
    "get_settings_dir",
    "get_settings_file",
    "get_settings_manager",
    "show_settings_dialog",
]
