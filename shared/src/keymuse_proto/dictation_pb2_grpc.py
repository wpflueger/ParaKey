from __future__ import annotations

from typing import AsyncIterable, AsyncIterator, cast

import grpc

from keymuse_proto import dictation_pb2


class DictationServiceServicer:
    async def StreamAudio(
        self,
        request_iterator: AsyncIterable[dictation_pb2.AudioFrame],
        context: grpc.aio.ServicerContext,
    ) -> AsyncIterator[dictation_pb2.DictationEvent]:
        raise NotImplementedError

    async def GetHealth(
        self,
        request: dictation_pb2.HealthRequest,
        context: grpc.aio.ServicerContext,
    ) -> dictation_pb2.HealthStatus:
        raise NotImplementedError


class DictationServiceStub:
    def __init__(self, channel: grpc.aio.Channel) -> None:
        self._stream_audio = channel.stream_stream(
            "/keymuse.dictation.v1.DictationService/StreamAudio",
            request_serializer=dictation_pb2.serialize_audio_frame,
            response_deserializer=dictation_pb2.deserialize_dictation_event,
        )
        self._get_health = channel.unary_unary(
            "/keymuse.dictation.v1.DictationService/GetHealth",
            request_serializer=dictation_pb2.serialize_health_request,
            response_deserializer=dictation_pb2.deserialize_health_status,
        )

    async def StreamAudio(
        self, request_iterator: AsyncIterable[dictation_pb2.AudioFrame]
    ) -> AsyncIterator[dictation_pb2.DictationEvent]:
        typed_iterator = cast(AsyncIterator[dictation_pb2.AudioFrame], request_iterator)
        call = self._stream_audio(typed_iterator)
        async for response in call:
            yield response

    async def GetHealth(
        self, request: dictation_pb2.HealthRequest
    ) -> dictation_pb2.HealthStatus:
        return await self._get_health(request)


def add_DictationServiceServicer_to_server(
    servicer: DictationServiceServicer, server: grpc.aio.Server
) -> None:
    rpc_method_handlers = {
        "StreamAudio": grpc.stream_stream_rpc_method_handler(
            servicer.StreamAudio,
            request_deserializer=dictation_pb2.deserialize_audio_frame,
            response_serializer=dictation_pb2.serialize_dictation_event,
        ),
        "GetHealth": grpc.unary_unary_rpc_method_handler(
            servicer.GetHealth,
            request_deserializer=dictation_pb2.deserialize_health_request,
            response_serializer=dictation_pb2.serialize_health_status,
        ),
    }
    generic_handler = grpc.method_handlers_generic_handler(
        "keymuse.dictation.v1.DictationService", rpc_method_handlers
    )
    server.add_generic_rpc_handlers((generic_handler,))


__all__ = [
    "DictationServiceServicer",
    "DictationServiceStub",
    "add_DictationServiceServicer_to_server",
]
