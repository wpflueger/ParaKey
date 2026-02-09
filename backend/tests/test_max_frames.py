"""Tests for max audio frames limit in service and config."""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest

from parakey_backend.config import BackendConfig
from parakey_backend.engine import MockInferenceEngine
from parakey_backend.service import DictationService
from parakey_proto import dictation_pb2


async def _audio_stream_no_eos(
    *,
    frame_count: int,
    sample_rate_hz: int = 16000,
) -> AsyncIterator[dictation_pb2.AudioFrame]:
    """Generate audio frames without end_of_stream flag."""
    for _ in range(frame_count):
        yield dictation_pb2.AudioFrame(
            audio=b"\x00" * 320,
            sample_rate_hz=sample_rate_hz,
            end_of_stream=False,
        )


class TestMaxAudioFramesConfig:
    """Tests for max_audio_frames in BackendConfig."""

    def test_default_value(self):
        config = BackendConfig()
        assert config.max_audio_frames == 5000

    def test_custom_value(self):
        config = BackendConfig(max_audio_frames=100)
        assert config.max_audio_frames == 100


class TestMaxFramesInService:
    """Tests for max frame limit enforcement in StreamAudio."""

    @pytest.mark.asyncio
    async def test_stops_at_max_frames(self) -> None:
        """Service should stop collecting after max_audio_frames."""
        config = BackendConfig(
            mode="mock",
            max_audio_frames=10,
            final_text="Truncated result",
        )
        engine = MockInferenceEngine(config)
        service = DictationService(config, engine=engine)
        service.load_model()

        # Send 20 frames with no end_of_stream — should stop at 10
        events = [
            event
            async for event in service.StreamAudio(
                _audio_stream_no_eos(frame_count=20),
                None,
            )
        ]

        finals = [e for e in events if e.final is not None]
        assert len(finals) == 1
        assert finals[0].final.text == "Truncated result"

    @pytest.mark.asyncio
    async def test_end_of_stream_before_max(self) -> None:
        """end_of_stream should still stop collection before max limit."""
        config = BackendConfig(
            mode="mock",
            max_audio_frames=100,
            final_text="Normal result",
        )
        engine = MockInferenceEngine(config)
        service = DictationService(config, engine=engine)
        service.load_model()

        async def _stream() -> AsyncIterator[dictation_pb2.AudioFrame]:
            for i in range(5):
                yield dictation_pb2.AudioFrame(
                    audio=b"\x00" * 320,
                    sample_rate_hz=16000,
                    end_of_stream=i == 4,
                )

        events = [
            event
            async for event in service.StreamAudio(_stream(), None)
        ]

        finals = [e for e in events if e.final is not None]
        assert len(finals) == 1
        assert finals[0].final.text == "Normal result"

    @pytest.mark.asyncio
    async def test_max_frames_still_transcribes(self) -> None:
        """Audio collected up to the limit should still be transcribed."""
        config = BackendConfig(
            mode="mock",
            max_audio_frames=5,
            final_text="Partial audio transcribed",
        )
        engine = MockInferenceEngine(config)
        service = DictationService(config, engine=engine)
        service.load_model()

        events = [
            event
            async for event in service.StreamAudio(
                _audio_stream_no_eos(frame_count=50),
                None,
            )
        ]

        # Should have a final transcript even though we hit the limit
        finals = [e for e in events if e.final is not None]
        assert len(finals) == 1
