"""Main application window for KeyMuse.

This module provides the primary window showing status and history.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional

from keymuse_client.ui.history_panel import HistoryPanel
from keymuse_client.ui.status_panel import StatusPanel
from keymuse_client.ui.theme import Theme, configure_ttk_style, get_theme


class MainWindow(tk.Toplevel):
    """Main KeyMuse application window."""

    def __init__(
        self,
        parent: Optional[tk.Tk] = None,
        theme: Optional[Theme] = None,
        on_settings: Optional[Callable[[], None]] = None,
        on_minimize_to_tray: Optional[Callable[[], None]] = None,
        on_quit: Optional[Callable[[], None]] = None,
    ) -> None:
        """Initialize the main window.

        Args:
            parent: Parent tkinter root window.
            theme: Optional theme (defaults to global theme).
            on_settings: Callback when Settings button is clicked.
            on_minimize_to_tray: Callback when minimizing to tray.
            on_quit: Callback when quitting the application.
        """
        super().__init__(parent)
        self._theme = theme or get_theme()
        self._on_settings = on_settings
        self._on_minimize_to_tray = on_minimize_to_tray
        self._on_quit = on_quit
        self._on_copy: Optional[Callable[[str], None]] = None

        self._status_panel: Optional[StatusPanel] = None
        self._history_panel: Optional[HistoryPanel] = None

        self._setup_window()
        self._create_widgets()

    def _setup_window(self) -> None:
        """Configure window properties."""
        self.title("KeyMuse")

        # Window size and position
        width = self._theme.window_width
        height = self._theme.window_height

        # Position near bottom-right of screen
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = screen_width - width - 50
        y = screen_height - height - 100

        self.geometry(f"{width}x{height}+{x}+{y}")
        self.minsize(350, 400)

        # Configure appearance
        self.configure(bg=self._theme.bg_primary)

        # Configure styles
        configure_ttk_style(self, self._theme)

        # Handle window close - minimize to tray instead of quitting
        self.protocol("WM_DELETE_WINDOW", self._handle_close)

    def _create_widgets(self) -> None:
        """Create the window widgets."""
        padding = self._theme.padding_normal

        # Main container
        main_frame = ttk.Frame(self, style="TFrame")
        main_frame.pack(fill="both", expand=True, padx=padding, pady=padding)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=1)  # History panel expands

        # Header with title and hotkey hint
        header_frame = ttk.Frame(main_frame, style="TFrame")
        header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 15))

        title_label = ttk.Label(
            header_frame,
            text="KeyMuse",
            style="Title.TLabel",
        )
        title_label.pack(side="left")

        hotkey_label = ttk.Label(
            header_frame,
            text="Press Ctrl+Alt to dictate",
            style="Muted.TLabel",
        )
        hotkey_label.pack(side="right")

        # Status section
        status_frame = ttk.LabelFrame(
            main_frame,
            text="Status",
            style="TLabelframe",
        )
        status_frame.grid(row=1, column=0, sticky="ew", pady=(0, 15))

        self._status_panel = StatusPanel(status_frame, theme=self._theme)
        self._status_panel.pack(fill="x")

        # History section
        history_frame = ttk.LabelFrame(
            main_frame,
            text="Recent Transcripts",
            style="TLabelframe",
        )
        history_frame.grid(row=2, column=0, sticky="nsew", pady=(0, 15))
        history_frame.rowconfigure(0, weight=1)
        history_frame.columnconfigure(0, weight=1)

        self._history_panel = HistoryPanel(history_frame, theme=self._theme)
        self._history_panel.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        # Button bar
        button_frame = ttk.Frame(main_frame, style="TFrame")
        button_frame.grid(row=3, column=0, sticky="ew")

        # Settings button
        settings_btn = ttk.Button(
            button_frame,
            text="Settings",
            command=self._handle_settings,
        )
        settings_btn.pack(side="left")

        # Minimize to tray button
        minimize_btn = ttk.Button(
            button_frame,
            text="Minimize to Tray",
            command=self._handle_minimize,
        )
        minimize_btn.pack(side="right")

    def _handle_close(self) -> None:
        """Handle window close - minimize to tray."""
        self._handle_minimize()

    def _handle_settings(self) -> None:
        """Handle settings button click."""
        if self._on_settings:
            self._on_settings()

    def _handle_minimize(self) -> None:
        """Handle minimize to tray."""
        self.withdraw()  # Hide window
        if self._on_minimize_to_tray:
            self._on_minimize_to_tray()

    def set_on_copy(self, callback: Callable[[str], None]) -> None:
        """Set the copy callback for history items.

        Args:
            callback: Function to call with text when copy is clicked.
        """
        self._on_copy = callback
        if self._history_panel:
            self._history_panel.set_on_copy(callback)

    def show(self) -> None:
        """Show and raise the window."""
        self.deiconify()  # Show if hidden
        self.lift()  # Raise to top
        self.focus_force()  # Give focus

    def hide(self) -> None:
        """Hide the window."""
        self.withdraw()

    def update_dictation_state(self, state: str) -> None:
        """Update dictation state display.

        Args:
            state: State name (IDLE, RECORDING, PROCESSING, INSERTING, ERROR).
        """
        if self._status_panel:
            self._status_panel.set_dictation_state(state)

    def update_model_status(self, ready: bool, detail: str = "") -> None:
        """Update model status display.

        Args:
            ready: Whether model is loaded.
            detail: Status detail text.
        """
        if self._status_panel:
            self._status_panel.set_model_status(ready, detail)

    def update_backend_status(self, connected: bool, detail: str = "") -> None:
        """Update backend connection status.

        Args:
            connected: Whether connected to backend.
            detail: Status detail text.
        """
        if self._status_panel:
            self._status_panel.set_backend_status(connected, detail)

    def set_all_ready(self) -> None:
        """Set all status indicators to ready."""
        if self._status_panel:
            self._status_panel.set_all_ready()

    def add_transcript(self, text: str) -> None:
        """Add a new transcript to history.

        Args:
            text: The transcript text.
        """
        if self._history_panel:
            self._history_panel.add_transcript(text)

    def refresh_history(self) -> None:
        """Refresh the history panel."""
        if self._history_panel:
            self._history_panel.refresh()


__all__ = [
    "MainWindow",
]
