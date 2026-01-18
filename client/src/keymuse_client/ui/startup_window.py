"""Startup window for KeyMuse showing model loading progress.

This module provides a loading window displayed during backend startup
and model loading.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional

from keymuse_client.ui.theme import Theme, configure_ttk_style, get_theme


class StartupWindow(tk.Toplevel):
    """Window shown during KeyMuse startup and model loading."""

    def __init__(
        self,
        parent: Optional[tk.Tk] = None,
        theme: Optional[Theme] = None,
        on_cancel: Optional[Callable[[], None]] = None,
    ) -> None:
        """Initialize the startup window.

        Args:
            parent: Parent tkinter root window.
            theme: Optional theme (defaults to global theme).
            on_cancel: Callback when cancel button is clicked.
        """
        super().__init__(parent)
        self._theme = theme or get_theme()
        self._on_cancel = on_cancel
        self._log_lines: list[str] = []
        self._max_log_lines = 100

        self._setup_window()
        self._create_widgets()

    def _setup_window(self) -> None:
        """Configure window properties."""
        self.title("KeyMuse - Starting")

        # Window size and position
        width = self._theme.startup_width
        height = self._theme.startup_height

        # Center on screen
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2

        self.geometry(f"{width}x{height}+{x}+{y}")
        self.resizable(False, False)

        # Configure appearance
        self.configure(bg=self._theme.bg_primary)

        # Configure styles
        configure_ttk_style(self, self._theme)

        # Make it stay on top during loading
        self.attributes("-topmost", True)

        # Handle window close
        self.protocol("WM_DELETE_WINDOW", self._handle_close)

    def _create_widgets(self) -> None:
        """Create the window widgets."""
        padding = self._theme.padding_large

        # Main container
        main_frame = ttk.Frame(self, style="TFrame")
        main_frame.pack(fill="both", expand=True, padx=padding, pady=padding)

        # Title
        title_label = ttk.Label(
            main_frame,
            text="KeyMuse",
            style="Header.TLabel",
        )
        title_label.pack(pady=(0, 5))

        # Subtitle
        subtitle_label = ttk.Label(
            main_frame,
            text="Speech to Text Dictation",
            style="Muted.TLabel",
        )
        subtitle_label.pack(pady=(0, 20))

        # Status label
        self._status_label = ttk.Label(
            main_frame,
            text="Initializing...",
            style="TLabel",
        )
        self._status_label.pack(pady=(0, 10))

        # Progress bar
        self._progress = ttk.Progressbar(
            main_frame,
            mode="indeterminate",
            length=350,
        )
        self._progress.pack(pady=(0, 15))
        self._progress.start(10)  # Start animation

        # Model cache info
        self._cache_label = ttk.Label(
            main_frame,
            text="",
            style="Muted.TLabel",
        )
        self._cache_label.pack(pady=(0, 15))

        # Log frame
        log_frame = ttk.LabelFrame(
            main_frame,
            text="Backend Output",
            style="TLabelframe",
        )
        log_frame.pack(fill="both", expand=True, pady=(0, 15))

        # Log text area
        self._log_text = tk.Text(
            log_frame,
            height=8,
            bg=self._theme.bg_secondary,
            fg=self._theme.fg_secondary,
            font=(self._theme.font_family, self._theme.font_size_small),
            wrap="word",
            state="disabled",
            borderwidth=0,
            highlightthickness=0,
        )
        self._log_text.pack(fill="both", expand=True, padx=5, pady=5)

        # Log scrollbar
        log_scroll = ttk.Scrollbar(
            self._log_text,
            orient="vertical",
            command=self._log_text.yview,
        )
        log_scroll.pack(side="right", fill="y")
        self._log_text.configure(yscrollcommand=log_scroll.set)

        # Cancel button
        button_frame = ttk.Frame(main_frame, style="TFrame")
        button_frame.pack(fill="x")

        self._cancel_btn = ttk.Button(
            button_frame,
            text="Cancel",
            command=self._handle_cancel,
        )
        self._cancel_btn.pack(side="right")

    def _handle_close(self) -> None:
        """Handle window close button."""
        self._handle_cancel()

    def _handle_cancel(self) -> None:
        """Handle cancel button click."""
        if self._on_cancel:
            self._on_cancel()

    def set_status(self, status: str) -> None:
        """Update the status message.

        Args:
            status: New status text.
        """
        self._status_label.configure(text=status)

    def set_cache_location(self, path: str) -> None:
        """Display the model cache location.

        Args:
            path: Path to model cache directory.
        """
        # Truncate long paths
        display_path = path
        if len(display_path) > 50:
            display_path = "..." + display_path[-47:]

        self._cache_label.configure(text=f"Model cache: {display_path}")

    def append_log(self, text: str) -> None:
        """Append text to the log area.

        Args:
            text: Text to append.
        """
        self._log_lines.append(text)

        # Trim old lines
        while len(self._log_lines) > self._max_log_lines:
            self._log_lines.pop(0)

        # Update text widget
        self._log_text.configure(state="normal")
        self._log_text.delete("1.0", tk.END)
        self._log_text.insert(tk.END, "\n".join(self._log_lines))
        self._log_text.configure(state="disabled")

        # Scroll to bottom
        self._log_text.see(tk.END)

    def clear_log(self) -> None:
        """Clear the log area."""
        self._log_lines.clear()
        self._log_text.configure(state="normal")
        self._log_text.delete("1.0", tk.END)
        self._log_text.configure(state="disabled")

    def set_progress_determinate(self, value: int, maximum: int = 100) -> None:
        """Switch to determinate progress mode.

        Args:
            value: Current progress value.
            maximum: Maximum progress value.
        """
        self._progress.stop()
        self._progress.configure(mode="determinate", maximum=maximum, value=value)

    def set_progress_indeterminate(self) -> None:
        """Switch back to indeterminate progress mode."""
        self._progress.configure(mode="indeterminate")
        self._progress.start(10)

    def show_error(self, message: str) -> None:
        """Display an error state.

        Args:
            message: Error message to display.
        """
        self._progress.stop()
        self._status_label.configure(
            text=f"Error: {message}",
            foreground=self._theme.color_error,
        )
        self._cancel_btn.configure(text="Close")

    def show_success(self) -> None:
        """Display success state briefly before closing."""
        self._progress.stop()
        self._progress.configure(mode="determinate", value=100)
        self._status_label.configure(
            text="Ready!",
            foreground=self._theme.color_success,
        )

    def close(self) -> None:
        """Close and destroy the window."""
        self._progress.stop()
        self.destroy()


__all__ = [
    "StartupWindow",
]
