"""Theme constants for KeyMuse UI.

This module provides colors, fonts, and dimensions for the tkinter-based UI.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Theme:
    """Theme styling constants."""

    # Background colors
    bg_primary: str = "#1E1E1E"
    bg_secondary: str = "#2D2D2D"
    bg_tertiary: str = "#3C3C3C"
    bg_hover: str = "#4A4A4A"

    # Foreground colors
    fg_primary: str = "#FFFFFF"
    fg_secondary: str = "#CCCCCC"
    fg_muted: str = "#808080"

    # Status colors
    color_idle: str = "#808080"
    color_ready: str = "#4CAF50"
    color_recording: str = "#FF4444"
    color_processing: str = "#FFA500"
    color_error: str = "#FF4444"
    color_success: str = "#4CAF50"

    # Accent colors
    color_accent: str = "#007ACC"
    color_accent_hover: str = "#1E90FF"

    # Fonts
    font_family: str = "Segoe UI"
    font_size_small: int = 9
    font_size_normal: int = 10
    font_size_large: int = 12
    font_size_title: int = 16
    font_size_header: int = 20

    # Window dimensions
    window_width: int = 420
    window_height: int = 520
    startup_width: int = 500
    startup_height: int = 400

    # Padding and margins
    padding_small: int = 5
    padding_normal: int = 10
    padding_large: int = 15

    # Border
    border_radius: int = 4


# Default theme instance
DEFAULT_THEME = Theme()


def get_theme() -> Theme:
    """Get the current theme.

    Returns:
        The active theme instance.
    """
    return DEFAULT_THEME


def configure_ttk_style(root, theme: Theme | None = None) -> None:
    """Configure ttk styles for the theme.

    Args:
        root: The tkinter root window.
        theme: Optional theme to use (defaults to DEFAULT_THEME).
    """
    from tkinter import ttk

    theme = theme or DEFAULT_THEME
    style = ttk.Style(root)

    # Use clam as base theme (works well for custom styling)
    try:
        style.theme_use("clam")
    except Exception:
        pass  # Fall back to default

    # Configure frame style
    style.configure(
        "TFrame",
        background=theme.bg_primary,
    )

    style.configure(
        "Secondary.TFrame",
        background=theme.bg_secondary,
    )

    # Configure label style
    style.configure(
        "TLabel",
        background=theme.bg_primary,
        foreground=theme.fg_primary,
        font=(theme.font_family, theme.font_size_normal),
    )

    style.configure(
        "Title.TLabel",
        background=theme.bg_primary,
        foreground=theme.fg_primary,
        font=(theme.font_family, theme.font_size_title, "bold"),
    )

    style.configure(
        "Header.TLabel",
        background=theme.bg_primary,
        foreground=theme.fg_primary,
        font=(theme.font_family, theme.font_size_header, "bold"),
    )

    style.configure(
        "Muted.TLabel",
        background=theme.bg_primary,
        foreground=theme.fg_muted,
        font=(theme.font_family, theme.font_size_small),
    )

    style.configure(
        "Status.TLabel",
        background=theme.bg_secondary,
        foreground=theme.fg_primary,
        font=(theme.font_family, theme.font_size_normal),
    )

    # Configure button style
    style.configure(
        "TButton",
        background=theme.bg_tertiary,
        foreground=theme.fg_primary,
        font=(theme.font_family, theme.font_size_normal),
        padding=(theme.padding_normal, theme.padding_small),
    )

    style.map(
        "TButton",
        background=[("active", theme.bg_hover)],
    )

    style.configure(
        "Accent.TButton",
        background=theme.color_accent,
        foreground=theme.fg_primary,
    )

    style.map(
        "Accent.TButton",
        background=[("active", theme.color_accent_hover)],
    )

    # Configure labelframe style
    style.configure(
        "TLabelframe",
        background=theme.bg_primary,
        foreground=theme.fg_primary,
    )

    style.configure(
        "TLabelframe.Label",
        background=theme.bg_primary,
        foreground=theme.fg_secondary,
        font=(theme.font_family, theme.font_size_normal, "bold"),
    )

    # Configure progressbar style
    style.configure(
        "TProgressbar",
        background=theme.color_accent,
        troughcolor=theme.bg_tertiary,
    )

    # Configure separator
    style.configure(
        "TSeparator",
        background=theme.bg_tertiary,
    )


__all__ = [
    "Theme",
    "DEFAULT_THEME",
    "get_theme",
    "configure_ttk_style",
]
