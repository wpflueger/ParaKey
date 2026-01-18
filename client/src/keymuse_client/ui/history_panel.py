"""History panel widget for KeyMuse UI.

This module provides a scrollable list widget showing recent transcripts
with copy functionality.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional

from keymuse_client.ui.theme import Theme, get_theme


class HistoryItem(ttk.Frame):
    """A single transcript item in the history list."""

    def __init__(
        self,
        parent,
        text: str,
        index: int,
        on_copy: Optional[Callable[[str], None]] = None,
        theme: Optional[Theme] = None,
        **kwargs,
    ) -> None:
        """Initialize the history item.

        Args:
            parent: Parent widget.
            text: The transcript text.
            index: Item index (for display).
            on_copy: Callback when copy button is clicked.
            theme: Optional theme (defaults to global theme).
            **kwargs: Additional frame options.
        """
        super().__init__(parent, style="Secondary.TFrame", **kwargs)
        self._theme = theme or get_theme()
        self._text = text
        self._index = index
        self._on_copy = on_copy

        self._create_widgets()

    def _create_widgets(self) -> None:
        """Create the item widgets."""
        self.columnconfigure(0, weight=1)

        # Truncate text for display
        display_text = self._text
        if len(display_text) > 100:
            display_text = display_text[:97] + "..."

        # Replace newlines with spaces for single-line display
        display_text = display_text.replace("\r\n", " ").replace("\n", " ")

        # Text label
        text_label = ttk.Label(
            self,
            text=display_text,
            style="Status.TLabel",
            wraplength=280,
        )
        text_label.grid(row=0, column=0, sticky="w", padx=8, pady=6)

        # Copy button
        copy_btn = ttk.Button(
            self,
            text="Copy",
            width=6,
            command=self._handle_copy,
        )
        copy_btn.grid(row=0, column=1, sticky="e", padx=(4, 8), pady=6)

    def _handle_copy(self) -> None:
        """Handle copy button click."""
        if self._on_copy:
            self._on_copy(self._text)


class HistoryPanel(ttk.Frame):
    """Panel showing transcription history."""

    def __init__(
        self,
        parent,
        theme: Optional[Theme] = None,
        **kwargs,
    ) -> None:
        """Initialize the history panel.

        Args:
            parent: Parent widget.
            theme: Optional theme (defaults to global theme).
            **kwargs: Additional frame options.
        """
        super().__init__(parent, **kwargs)
        self._theme = theme or get_theme()
        self._items: list[HistoryItem] = []
        self._on_copy: Optional[Callable[[str], None]] = None

        self._create_widgets()

    def _create_widgets(self) -> None:
        """Create the panel widgets."""
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        # Create canvas with scrollbar for scrolling
        self._canvas = tk.Canvas(
            self,
            bg=self._theme.bg_primary,
            highlightthickness=0,
            borderwidth=0,
        )
        self._canvas.grid(row=0, column=0, sticky="nsew")

        # Scrollbar
        scrollbar = ttk.Scrollbar(
            self,
            orient="vertical",
            command=self._canvas.yview,
        )
        scrollbar.grid(row=0, column=1, sticky="ns")

        self._canvas.configure(yscrollcommand=scrollbar.set)

        # Frame inside canvas to hold items
        self._inner_frame = ttk.Frame(self._canvas, style="TFrame")
        self._canvas_window = self._canvas.create_window(
            (0, 0),
            window=self._inner_frame,
            anchor="nw",
        )

        # Bind events for proper scrolling
        self._inner_frame.bind("<Configure>", self._on_frame_configure)
        self._canvas.bind("<Configure>", self._on_canvas_configure)

        # Enable mouse wheel scrolling
        self._canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        # Empty state label
        self._empty_label = ttk.Label(
            self._inner_frame,
            text="No transcripts yet.\nPress Ctrl+Alt and speak to dictate.",
            style="Muted.TLabel",
            justify="center",
        )

        # Refresh button frame
        button_frame = ttk.Frame(self)
        button_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8, 0))

        refresh_btn = ttk.Button(
            button_frame,
            text="Refresh",
            command=self.refresh,
        )
        refresh_btn.pack(side="right")

        # Initial display
        self._show_empty()

    def _on_frame_configure(self, event=None) -> None:
        """Update scroll region when inner frame changes."""
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    def _on_canvas_configure(self, event=None) -> None:
        """Update inner frame width when canvas resizes."""
        # Make the inner frame fill the canvas width
        self._canvas.itemconfig(self._canvas_window, width=event.width)

    def _on_mousewheel(self, event) -> None:
        """Handle mouse wheel scrolling."""
        self._canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _show_empty(self) -> None:
        """Show empty state message."""
        self._empty_label.pack(pady=40)

    def _hide_empty(self) -> None:
        """Hide empty state message."""
        self._empty_label.pack_forget()

    def set_on_copy(self, callback: Callable[[str], None]) -> None:
        """Set the copy callback.

        Args:
            callback: Function to call with text when copy is clicked.
        """
        self._on_copy = callback

    def set_history(self, transcripts: list[str]) -> None:
        """Update the history display.

        Args:
            transcripts: List of transcripts (oldest first).
        """
        # Clear existing items
        for item in self._items:
            item.destroy()
        self._items.clear()

        if not transcripts:
            self._show_empty()
            return

        self._hide_empty()

        # Add items in reverse order (newest first)
        for i, text in enumerate(reversed(transcripts)):
            item = HistoryItem(
                self._inner_frame,
                text=text,
                index=len(transcripts) - i,
                on_copy=self._on_copy,
                theme=self._theme,
            )
            item.pack(fill="x", pady=(0, 4))
            self._items.append(item)

        # Update scroll region
        self._on_frame_configure()

    def add_transcript(self, text: str) -> None:
        """Add a new transcript to the top of the list.

        Args:
            text: The transcript text.
        """
        self._hide_empty()

        # Create new item at the top
        item = HistoryItem(
            self._inner_frame,
            text=text,
            index=len(self._items) + 1,
            on_copy=self._on_copy,
            theme=self._theme,
        )

        # Insert at beginning
        if self._items:
            item.pack(before=self._items[0], fill="x", pady=(0, 4))
        else:
            item.pack(fill="x", pady=(0, 4))

        self._items.insert(0, item)

        # Remove old items if exceeding limit
        while len(self._items) > 10:
            old_item = self._items.pop()
            old_item.destroy()

        # Update scroll region
        self._on_frame_configure()

    def refresh(self) -> None:
        """Refresh the history from the clipboard module."""
        from keymuse_client.insertion.clipboard import get_transcript_history

        transcripts = get_transcript_history()
        self.set_history(transcripts)

    def clear(self) -> None:
        """Clear all history items."""
        for item in self._items:
            item.destroy()
        self._items.clear()
        self._show_empty()
        self._on_frame_configure()


__all__ = [
    "HistoryItem",
    "HistoryPanel",
]
