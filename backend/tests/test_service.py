"""Tests for gRPC DictationService behavior."""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest

from keymuse_backend.config import BackendConfig
from keymuse_backend.engine import MockInferenceEngine
from keymuse_backend.service import DictationService
from keymuse_proto import dictation_pb2


async def _audio_stream(
    *,
    frame_count: int,
    sample_rate_hz: int,
) -> AsyncIterator[dictation_pb2.AudioFrame]:
    for index in range(frame_count):
        yield dictation_pb2.AudioFrame(
            audio=b"\x00" * 320,
            sample_rate_hz=sample_rate_hz,
            end_of_stream=index == frame_count - 1,
        )


@pytest.mark.asyncio
async def test_stream_audio_emits_partials_and_final() -> None:
    config = BackendConfig(
        mode="mock",
        partial_every_n_frames=2,
        final_text="Unit test transcript",
    )
    engine = MockInferenceEngine(config)
    service = DictationService(config, engine=engine)
    service.load_model()

    events = [
        event
        async for event in service.StreamAudio(
            _audio_stream(frame_count=4, sample_rate_hz=16000),
            None,
        )
    ]

    partials = [e for e in events if e.partial is not None]
    finals = [e for e in events if e.final is not None]

    assert len(partials) == 2
    assert len(finals) == 1
    assert finals[0].final.text == config.final_text


@pytest.mark.asyncio
async def test_health_ready_flag_reflects_model_state() -> None:
    config = BackendConfig(mode="mock")
    engine = MockInferenceEngine(config)
    service = DictationService(config, engine=engine)

    health = await service.GetHealth(dictation_pb2.HealthRequest(), None)
    assert not health.ready

    service.load_model()
    health = await service.GetHealth(dictation_pb2.HealthRequest(), None)
    assert health.ready
