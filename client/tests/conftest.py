"""Pytest configuration and fixtures for KeyMuse client tests."""

from __future__ import annotations

import sys

import pytest


def pytest_configure(config):
    """Configure custom markers."""
    config.addinivalue_line(
        "markers", "windows_only: mark test to run only on Windows"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )


def pytest_collection_modifyitems(config, items):
    """Skip platform-specific tests when not on that platform."""
    if sys.platform != "win32":
        skip_windows = pytest.mark.skip(reason="Windows-only test")
        for item in items:
            if "windows_only" in item.keywords:
                item.add_marker(skip_windows)
