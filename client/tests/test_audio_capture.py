"""Tests for audio capture module."""

from __future__ import annotations

import asyncio

import pytest

from keymuse_client.audio.capture import (
    AudioCaptureConfig,
    MockAudioCapture,
    SoundDeviceCapture,
    create_capture,
)
from keymuse_client.audio.devices import (
    AudioDevice,
    get_default_input_device,
    list_input_devices,
)
from keymuse_client.config import ClientConfig


class TestAudioCaptureConfig:
    """Tests for AudioCaptureConfig."""

    def test_config_defaults(self):
        config = AudioCaptureConfig(
            sample_rate_hz=16000,
            channels=1,
            frame_ms=20,
        )
        assert config.sample_rate_hz == 16000
        assert config.channels == 1
        assert config.frame_ms == 20
        assert config.device_index is None

    def test_config_with_device(self):
        config = AudioCaptureConfig(
            sample_rate_hz=16000,
            channels=1,
            frame_ms=20,
            device_index=2,
        )
        assert config.device_index == 2


class TestMockAudioCapture:
    """Tests for MockAudioCapture (runs without audio hardware)."""

    @pytest.fixture
    def config(self):
        return AudioCaptureConfig(
            sample_rate_hz=16000,
            channels=1,
            frame_ms=20,
        )

    @pytest.fixture
    def capture(self, config):
        return MockAudioCapture(config)

    def test_initial_state(self, capture):
        assert not capture.is_running

    def test_start_stop(self, capture):
        capture.start()
        assert capture.is_running
        capture.stop()
        assert not capture.is_running

    @pytest.mark.asyncio
    async def test_stream_duration(self, capture):
        """Test capturing a fixed duration of audio."""
        frames = []
        async for frame in capture.stream_duration(0.1):
            frames.append(frame)

        # 100ms / 20ms = 5 frames + 1 end-of-stream
        assert len(frames) >= 5
        assert frames[-1].end_of_stream

    @pytest.mark.asyncio
    async def test_frame_properties(self, capture):
        """Test that frames have correct properties."""
        frames = []
        async for frame in capture.stream_duration(0.05):
            frames.append(frame)

        # Check non-eos frames
        for frame in frames[:-1]:
            assert frame.sample_rate_hz == 16000
            assert frame.channels == 1
            assert not frame.end_of_stream
            # 16kHz * 20ms = 320 samples * 2 bytes = 640 bytes
            assert len(frame.audio) == 640

    @pytest.mark.asyncio
    async def test_sequence_numbers(self, capture):
        """Test that sequence numbers increment."""
        frames = []
        async for frame in capture.stream_duration(0.1):
            frames.append(frame)

        sequences = [f.sequence for f in frames]
        for i in range(1, len(sequences)):
            assert sequences[i] > sequences[i - 1]

    @pytest.mark.asyncio
    async def test_stream_stop(self, capture):
        """Test that stream ends when stop() is called."""
        capture.start()

        frames = []

        async def collect():
            async for frame in capture.stream():
                frames.append(frame)
                if len(frames) >= 3:
                    capture.stop()

        await asyncio.wait_for(collect(), timeout=2.0)

        assert len(frames) >= 3
        assert frames[-1].end_of_stream


class TestDeviceEnumeration:
    """Tests for device enumeration (may be skipped without audio hardware)."""

    @pytest.mark.skipif(
        not list_input_devices(),
        reason="No audio input devices available",
    )
    def test_list_devices(self):
        devices = list_input_devices()
        assert len(devices) > 0
        for device in devices:
            assert isinstance(device, AudioDevice)
            assert device.max_input_channels > 0

    @pytest.mark.skipif(
        not list_input_devices(),
        reason="No audio input devices available",
    )
    def test_default_device(self):
        device = get_default_input_device()
        assert device is not None
        assert device.max_input_channels > 0


class TestSoundDeviceCapture:
    """Tests for real audio capture (requires audio hardware)."""

    @pytest.fixture
    def config(self):
        return AudioCaptureConfig(
            sample_rate_hz=16000,
            channels=1,
            frame_ms=20,
        )

    @pytest.mark.skipif(
        not list_input_devices(),
        reason="No audio input devices available",
    )
    @pytest.mark.asyncio
    async def test_capture_2_seconds(self, config):
        """Capture 2 seconds of audio and verify frame count."""
        capture = SoundDeviceCapture(config)

        frames = []
        async for frame in capture.stream_duration(2.0):
            frames.append(frame)

        # 2000ms / 20ms = 100 frames (approximately)
        # Allow some variance due to timing
        non_eos_frames = [f for f in frames if not f.end_of_stream]
        assert len(non_eos_frames) >= 90  # At least 90 frames
        assert len(non_eos_frames) <= 110  # At most 110 frames

        # Verify frame format
        for frame in non_eos_frames:
            assert frame.sample_rate_hz == 16000
            assert frame.channels == 1
            # 320 samples * 2 bytes per sample = 640 bytes
            assert len(frame.audio) == 640


class TestCreateCapture:
    """Tests for the create_capture factory function."""

    def test_create_mock(self):
        config = ClientConfig()
        capture = create_capture(config, use_mock=True)
        assert isinstance(capture, MockAudioCapture)

    def test_create_real(self):
        config = ClientConfig()
        capture = create_capture(config, use_mock=False)
        assert isinstance(capture, SoundDeviceCapture)
