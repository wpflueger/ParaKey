from __future__ import annotations

from collections.abc import AsyncIterator

import grpc

from keymuse_proto import dictation_pb2, dictation_pb2_grpc


class DictationClient:
    def __init__(self, host: str, port: int) -> None:
        self._channel = grpc.aio.insecure_channel(f"{host}:{port}")
        self._stub = dictation_pb2_grpc.DictationServiceStub(self._channel)

    async def stream_audio(
        self, audio_stream: AsyncIterator[dictation_pb2.AudioFrame]
    ) -> AsyncIterator[dictation_pb2.DictationEvent]:
        async for response in self._stub.StreamAudio(audio_stream):
            yield response

    async def health(self) -> dictation_pb2.HealthStatus:
        return await self._stub.GetHealth(dictation_pb2.HealthRequest())

    async def close(self) -> None:
        await self._channel.close()
