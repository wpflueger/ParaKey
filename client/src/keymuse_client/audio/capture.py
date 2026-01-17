from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass

from keymuse_client.config import ClientConfig
from keymuse_proto.dictation_pb2 import AudioFrame


@dataclass(frozen=True)
class AudioCaptureConfig:
    sample_rate_hz: int
    channels: int
    frame_ms: int


class AudioCapture:
    def __init__(self, config: AudioCaptureConfig) -> None:
        self._config = config
        self._sequence = 0

    async def stream(self, duration_seconds: float = 1.0) -> AsyncIterator[AudioFrame]:
        total_frames = max(1, int(duration_seconds * 1000 / self._config.frame_ms))
        frame_samples = int(self._config.sample_rate_hz * (self._config.frame_ms / 1000))
        for _ in range(total_frames):
            await asyncio.sleep(self._config.frame_ms / 1000)
            self._sequence += 1
            yield AudioFrame(
                audio=b"\x00" * frame_samples,
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


def default_capture(config: ClientConfig) -> AudioCapture:
    return AudioCapture(
        AudioCaptureConfig(
            sample_rate_hz=config.sample_rate_hz,
            channels=config.channels,
            frame_ms=config.frame_ms,
        )
    )
