"""Status panel widget for KeyMuse UI.

This module provides a status indicators panel showing:
- Model/backend status
- Current dictation state
- Connection status
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Optional

from keymuse_client.ui.theme import Theme, get_theme


class StatusIndicator(ttk.Frame):
    """A single status indicator with colored dot and label."""

    def __init__(
        self,
        parent,
        label: str,
        theme: Optional[Theme] = None,
        **kwargs,
    ) -> None:
        """Initialize the status indicator.

        Args:
            parent: Parent widget.
            label: Label text for the indicator.
            theme: Optional theme (defaults to global theme).
            **kwargs: Additional frame options.
        """
        super().__init__(parent, **kwargs)
        self._theme = theme or get_theme()
        self._label_text = label
        self._status_text = ""
        self._color = self._theme.color_idle

        self._create_widgets()

    def _create_widgets(self) -> None:
        """Create the indicator widgets."""
        # Indicator dot (using canvas)
        self._canvas = tk.Canvas(
            self,
            width=12,
            height=12,
            bg=self._theme.bg_secondary,
            highlightthickness=0,
        )
        self._canvas.pack(side="left", padx=(0, 8))

        # Draw the indicator dot
        self._dot = self._canvas.create_oval(
            2, 2, 10, 10,
            fill=self._color,
            outline="",
        )

        # Label
        self._label = ttk.Label(
            self,
            text=self._label_text,
            style="Status.TLabel",
        )
        self._label.pack(side="left")

        # Status value
        self._status_label = ttk.Label(
            self,
            text=self._status_text,
            style="Status.TLabel",
        )
        self._status_label.pack(side="right")

    def set_status(self, status: str, color: Optional[str] = None) -> None:
        """Update the status display.

        Args:
            status: Status text to display.
            color: Optional color for the indicator dot.
        """
        self._status_text = status
        self._status_label.configure(text=status)

        if color is not None:
            self._color = color
            self._canvas.itemconfig(self._dot, fill=color)

    def set_color(self, color: str) -> None:
        """Update just the indicator color.

        Args:
            color: New color for the dot.
        """
        self._color = color
        self._canvas.itemconfig(self._dot, fill=color)


class StatusPanel(ttk.Frame):
    """Panel showing status indicators for KeyMuse."""

    def __init__(
        self,
        parent,
        theme: Optional[Theme] = None,
        **kwargs,
    ) -> None:
        """Initialize the status panel.

        Args:
            parent: Parent widget.
            theme: Optional theme (defaults to global theme).
            **kwargs: Additional frame options.
        """
        super().__init__(parent, style="Secondary.TFrame", **kwargs)
        self._theme = theme or get_theme()

        self._model_indicator: Optional[StatusIndicator] = None
        self._backend_indicator: Optional[StatusIndicator] = None
        self._dictation_indicator: Optional[StatusIndicator] = None

        self._create_widgets()

    def _create_widgets(self) -> None:
        """Create the panel widgets."""
        # Configure grid
        self.columnconfigure(0, weight=1)

        padding = self._theme.padding_normal

        # Model status
        self._model_indicator = StatusIndicator(
            self,
            "Model:",
            theme=self._theme,
        )
        self._model_indicator.grid(
            row=0, column=0, sticky="ew", padx=padding, pady=(padding, 4)
        )
        self._model_indicator.set_status("Not loaded", self._theme.color_idle)

        # Backend status
        self._backend_indicator = StatusIndicator(
            self,
            "Backend:",
            theme=self._theme,
        )
        self._backend_indicator.grid(
            row=1, column=0, sticky="ew", padx=padding, pady=4
        )
        self._backend_indicator.set_status("Disconnected", self._theme.color_idle)

        # Dictation state
        self._dictation_indicator = StatusIndicator(
            self,
            "Dictation:",
            theme=self._theme,
        )
        self._dictation_indicator.grid(
            row=2, column=0, sticky="ew", padx=padding, pady=(4, padding)
        )
        self._dictation_indicator.set_status("Idle", self._theme.color_idle)

    def set_model_status(self, ready: bool, detail: str = "") -> None:
        """Update model status.

        Args:
            ready: Whether the model is loaded and ready.
            detail: Optional detail text.
        """
        if ready:
            text = detail if detail else "Ready"
            color = self._theme.color_ready
        else:
            text = detail if detail else "Loading..."
            color = self._theme.color_processing

        if self._model_indicator:
            self._model_indicator.set_status(text, color)

    def set_backend_status(self, connected: bool, detail: str = "") -> None:
        """Update backend connection status.

        Args:
            connected: Whether connected to backend.
            detail: Optional detail text.
        """
        if connected:
            text = detail if detail else "Connected"
            color = self._theme.color_ready
        else:
            text = detail if detail else "Disconnected"
            color = self._theme.color_error

        if self._backend_indicator:
            self._backend_indicator.set_status(text, color)

    def set_dictation_state(self, state: str) -> None:
        """Update dictation state display.

        Args:
            state: State name (IDLE, RECORDING, PROCESSING, INSERTING, ERROR).
        """
        state_config = {
            "IDLE": ("Idle", self._theme.color_idle),
            "RECORDING": ("Recording...", self._theme.color_recording),
            "PROCESSING": ("Processing...", self._theme.color_processing),
            "INSERTING": ("Inserting...", self._theme.color_processing),
            "ERROR": ("Error", self._theme.color_error),
        }

        text, color = state_config.get(state, ("Unknown", self._theme.color_idle))

        if self._dictation_indicator:
            self._dictation_indicator.set_status(text, color)

    def set_all_ready(self) -> None:
        """Set all indicators to ready state."""
        self.set_model_status(True, "Ready")
        self.set_backend_status(True, "Connected")
        self.set_dictation_state("IDLE")

    def set_loading(self, message: str = "Loading...") -> None:
        """Set indicators to loading state.

        Args:
            message: Loading message to display.
        """
        if self._model_indicator:
            self._model_indicator.set_status(message, self._theme.color_processing)
        if self._backend_indicator:
            self._backend_indicator.set_status("Connecting...", self._theme.color_processing)


__all__ = [
    "StatusIndicator",
    "StatusPanel",
]
