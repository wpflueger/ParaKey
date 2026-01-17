from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import sounddevice as sd


@dataclass(frozen=True)
class AudioDevice:
    """Information about an audio input device."""

    index: int
    name: str
    max_input_channels: int
    default_sample_rate: float
    is_default: bool


def list_input_devices() -> list[AudioDevice]:
    """List all available audio input devices.

    Returns:
        List of AudioDevice objects for devices with input channels.
    """
    devices: list[AudioDevice] = []
    default_input = sd.default.device[0]

    for i, dev in enumerate(sd.query_devices()):
        if dev["max_input_channels"] > 0:
            devices.append(
                AudioDevice(
                    index=i,
                    name=dev["name"],
                    max_input_channels=dev["max_input_channels"],
                    default_sample_rate=dev["default_samplerate"],
                    is_default=(i == default_input),
                )
            )

    return devices


def get_default_input_device() -> Optional[AudioDevice]:
    """Get the default audio input device.

    Returns:
        The default input device, or None if no input devices are available.
    """
    devices = list_input_devices()
    for device in devices:
        if device.is_default:
            return device
    return devices[0] if devices else None


def get_device_by_name(name: str) -> Optional[AudioDevice]:
    """Find an audio device by name (case-insensitive substring match).

    Args:
        name: Name or partial name of the device to find.

    Returns:
        The matching device, or None if not found.
    """
    name_lower = name.lower()
    for device in list_input_devices():
        if name_lower in device.name.lower():
            return device
    return None


def get_device_by_index(index: int) -> Optional[AudioDevice]:
    """Get an audio device by its index.

    Args:
        index: The device index.

    Returns:
        The device at the given index, or None if invalid.
    """
    for device in list_input_devices():
        if device.index == index:
            return device
    return None


__all__ = [
    "AudioDevice",
    "list_input_devices",
    "get_default_input_device",
    "get_device_by_name",
    "get_device_by_index",
]
