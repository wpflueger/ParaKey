"""Integration tests for gRPC pipeline (mock backend + client)."""

from __future__ import annotations

from collections.abc import AsyncIterator

import grpc
import pytest

from keymuse_backend.config import BackendConfig
from keymuse_backend.engine import MockInferenceEngine
from keymuse_backend.service import DictationService
from keymuse_client.grpc_client import DictationClient
from keymuse_proto import dictation_pb2, dictation_pb2_grpc


async def _audio_stream(frame_count: int) -> AsyncIterator[dictation_pb2.AudioFrame]:
    for index in range(frame_count):
        yield dictation_pb2.AudioFrame(
            audio=b"\x00" * 320,
            sample_rate_hz=16000,
            end_of_stream=index == frame_count - 1,
        )


@pytest.mark.asyncio
async def test_grpc_streaming_roundtrip() -> None:
    config = BackendConfig(
        mode="mock",
        partial_every_n_frames=3,
        final_text="Hello from mock",
    )
    engine = MockInferenceEngine(config)
    service = DictationService(config, engine=engine)
    service.load_model()

    server = grpc.aio.server()
    dictation_pb2_grpc.add_DictationServiceServicer_to_server(service, server)
    port = server.add_insecure_port("127.0.0.1:0")
    await server.start()

    client = DictationClient("127.0.0.1", port)
    try:
        health = await client.health()
        assert health.ready

        events = [
            event
            async for event in client.stream_audio(_audio_stream(6))
        ]

        partials = [e for e in events if e.partial is not None]
        finals = [e for e in events if e.final is not None]

        assert len(partials) == 2
        assert len(finals) == 1
        assert finals[0].final.text == config.final_text
    finally:
        await client.close()
        await server.stop(grace=0.1)
