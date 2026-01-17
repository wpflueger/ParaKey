from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass
from queue import Empty, Queue
from typing import Optional

import numpy as np
import sounddevice as sd

from keymuse_client.config import ClientConfig
from keymuse_proto.dictation_pb2 import AudioFrame

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AudioCaptureConfig:
    """Configuration for audio capture."""

    sample_rate_hz: int
    channels: int
    frame_ms: int
    device_index: Optional[int] = None


class AudioCaptureError(Exception):
    """Raised when audio capture encounters an error."""

    pass


class SoundDeviceCapture:
    """Real audio capture using sounddevice with InputStream callback."""

    def __init__(self, config: AudioCaptureConfig) -> None:
        self._config = config
        self._sequence = 0
        self._queue: Queue[np.ndarray] = Queue()
        self._stream: Optional[sd.InputStream] = None
        self._running = False
        self._error: Optional[Exception] = None

        # Calculate samples per frame (20ms at 16kHz = 320 samples)
        self._frame_samples = int(
            config.sample_rate_hz * (config.frame_ms / 1000)
        )

    def _audio_callback(
        self,
        indata: np.ndarray,
        frames: int,
        time_info: dict,
        status: sd.CallbackFlags,
    ) -> None:
        """Callback invoked by sounddevice for each audio block."""
        if status:
            logger.warning(f"Audio callback status: {status}")
            if status.input_overflow:
                logger.warning("Input overflow - audio may be clipped")

        # Copy the data to avoid issues with buffer reuse
        self._queue.put(indata.copy())

    def start(self) -> None:
        """Start audio capture."""
        if self._running:
            return

        try:
            self._stream = sd.InputStream(
                device=self._config.device_index,
                samplerate=self._config.sample_rate_hz,
                channels=self._config.channels,
                dtype=np.int16,
                blocksize=self._frame_samples,
                callback=self._audio_callback,
            )
            self._stream.start()
            self._running = True
            logger.info(
                f"Audio capture started: {self._config.sample_rate_hz}Hz, "
                f"{self._config.channels}ch, {self._config.frame_ms}ms frames"
            )
        except sd.PortAudioError as e:
            raise AudioCaptureError(f"Failed to start audio capture: {e}") from e

    def stop(self) -> None:
        """Stop audio capture."""
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        self._running = False
        logger.info("Audio capture stopped")

    @property
    def is_running(self) -> bool:
        """Return True if capture is currently running."""
        return self._running

    async def stream(self) -> AsyncIterator[AudioFrame]:
        """Yield audio frames as they become available.

        This is an infinite async generator that yields frames while capture
        is running. Stop capture with stop() to end the stream.
        """
        if not self._running:
            raise AudioCaptureError("Capture not started - call start() first")

        loop = asyncio.get_event_loop()
        frame_interval = self._config.frame_ms / 1000

        while self._running:
            try:
                # Non-blocking get with short timeout
                audio_data = await loop.run_in_executor(
                    None, lambda: self._queue.get(timeout=0.1)
                )

                self._sequence += 1
                yield AudioFrame(
                    audio=audio_data.tobytes(),
                    sample_rate_hz=self._config.sample_rate_hz,
                    channels=self._config.channels,
                    sequence=self._sequence,
                    end_of_stream=False,
                )
            except Empty:
                # No data available, continue waiting
                continue

        # Send end-of-stream marker
        self._sequence += 1
        yield AudioFrame(
            audio=b"",
            sample_rate_hz=self._config.sample_rate_hz,
            channels=self._config.channels,
            sequence=self._sequence,
            end_of_stream=True,
        )

    async def stream_duration(
        self, duration_seconds: float
    ) -> AsyncIterator[AudioFrame]:
        """Stream audio for a fixed duration.

        Args:
            duration_seconds: How long to capture audio.

        Yields:
            AudioFrame messages, followed by an end-of-stream frame.
        """
        if not self._running:
            self.start()
            started_here = True
        else:
            started_here = False

        try:
            end_time = asyncio.get_event_loop().time() + duration_seconds
            async for frame in self.stream():
                if frame.end_of_stream:
                    yield frame
                    break
                yield frame
                if asyncio.get_event_loop().time() >= end_time:
                    break

            # Send end-of-stream if we exited due to duration
            self._sequence += 1
            yield AudioFrame(
                audio=b"",
                sample_rate_hz=self._config.sample_rate_hz,
                channels=self._config.channels,
                sequence=self._sequence,
                end_of_stream=True,
            )
        finally:
            if started_here:
                self.stop()


class MockAudioCapture:
    """Mock audio capture for testing (generates silence)."""

    def __init__(self, config: AudioCaptureConfig) -> None:
        self._config = config
        self._sequence = 0
        self._running = False

    def start(self) -> None:
        self._running = True

    def stop(self) -> None:
        self._running = False

    @property
    def is_running(self) -> bool:
        return self._running

    async def stream(self) -> AsyncIterator[AudioFrame]:
        """Generate silent frames indefinitely until stopped."""
        frame_samples = int(
            self._config.sample_rate_hz * (self._config.frame_ms / 1000)
        )
        silence = b"\x00" * (frame_samples * 2)  # 16-bit = 2 bytes per sample

        while self._running:
            await asyncio.sleep(self._config.frame_ms / 1000)
            self._sequence += 1
            yield AudioFrame(
                audio=silence,
                sample_rate_hz=self._config.sample_rate_hz,
                channels=self._config.channels,
                sequence=self._sequence,
                end_of_stream=False,
            )

        self._sequence += 1
        yield AudioFrame(
            audio=b"",
            sample_rate_hz=self._config.sample_rate_hz,
            channels=self._config.channels,
            sequence=self._sequence,
            end_of_stream=True,
        )

    async def stream_duration(
        self, duration_seconds: float
    ) -> AsyncIterator[AudioFrame]:
        """Generate silent frames for a fixed duration."""
        total_frames = max(
            1, int(duration_seconds * 1000 / self._config.frame_ms)
        )
        frame_samples = int(
            self._config.sample_rate_hz * (self._config.frame_ms / 1000)
        )
        silence = b"\x00" * (frame_samples * 2)

        for _ in range(total_frames):
            await asyncio.sleep(self._config.frame_ms / 1000)
            self._sequence += 1
            yield AudioFrame(
                audio=silence,
                sample_rate_hz=self._config.sample_rate_hz,
                channels=self._config.channels,
                sequence=self._sequence,
                end_of_stream=False,
            )

        self._sequence += 1
        yield AudioFrame(
            audio=b"",
            sample_rate_hz=self._config.sample_rate_hz,
            channels=self._config.channels,
            sequence=self._sequence,
            end_of_stream=True,
        )


# Type alias for either capture implementation
AudioCapture = SoundDeviceCapture | MockAudioCapture


def create_capture(
    config: ClientConfig, use_mock: bool = False
) -> AudioCapture:
    """Create an audio capture instance.

    Args:
        config: Client configuration.
        use_mock: If True, use mock capture (for testing).

    Returns:
        An AudioCapture instance.
    """
    capture_config = AudioCaptureConfig(
        sample_rate_hz=config.sample_rate_hz,
        channels=config.channels,
        frame_ms=config.frame_ms,
    )

    if use_mock:
        return MockAudioCapture(capture_config)
    return SoundDeviceCapture(capture_config)


# Backwards compatibility alias
def default_capture(config: ClientConfig) -> MockAudioCapture:
    """Create a mock audio capture (backwards compatibility)."""
    return create_capture(config, use_mock=True)


__all__ = [
    "AudioCaptureConfig",
    "AudioCaptureError",
    "SoundDeviceCapture",
    "MockAudioCapture",
    "AudioCapture",
    "create_capture",
    "default_capture",
]
