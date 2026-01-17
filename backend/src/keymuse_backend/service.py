import asyncio
from collections.abc import AsyncIterable
from typing import AsyncIterator

import grpc

from keymuse_backend.config import BackendConfig
from keymuse_backend.engine import generate_mock_events
from keymuse_proto import dictation_pb2, dictation_pb2_grpc


class DictationService(dictation_pb2_grpc.DictationServiceServicer):
    def __init__(self, config: BackendConfig) -> None:
        self._config = config

    async def StreamAudio(
        self,
        request_iterator: AsyncIterable[dictation_pb2.AudioFrame],
        context: grpc.aio.ServicerContext,
    ) -> AsyncIterator[dictation_pb2.DictationEvent]:
        audio_frames: list[bytes] = []
        async for frame in request_iterator:
            audio_frames.append(frame.audio)
            if frame.end_of_stream:
                break

        events = generate_mock_events(self._config, audio_frames)
        for event in events:
            await asyncio.sleep(0.05)
            if event.kind == "partial":
                yield dictation_pb2.DictationEvent(
                    partial=dictation_pb2.TranscriptPartial(
                        text=event.text,
                        stability=event.stability or 0.0,
                    )
                )
            elif event.kind == "final":
                yield dictation_pb2.DictationEvent(
                    final=dictation_pb2.TranscriptFinal(
                        text=event.text,
                        from_cache=False,
                    )
                )

    async def GetHealth(
        self,
        request: dictation_pb2.HealthRequest,
        context: grpc.aio.ServicerContext,
    ) -> dictation_pb2.HealthStatus:
        return dictation_pb2.HealthStatus(
            ready=True,
            mode=self._config.mode,
            detail="Mock backend ready",
        )
