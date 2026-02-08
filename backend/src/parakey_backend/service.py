"""gRPC service implementation for ParaKey dictation."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterable
from typing import AsyncIterator, Optional

import grpc

from parakey_backend.config import BackendConfig
from parakey_backend.engine import (
    InferenceEngine,
    create_engine,
)
from parakey_proto import dictation_pb2, dictation_pb2_grpc

logger = logging.getLogger(__name__)


class DictationService(dictation_pb2_grpc.DictationServiceServicer):
    """gRPC service for speech-to-text dictation."""

    def __init__(
        self,
        config: BackendConfig,
        engine: Optional[InferenceEngine] = None,
    ) -> None:
        """Initialize the dictation service.

        Args:
            config: Backend configuration.
            engine: Optional pre-created engine. If None, creates one.
        """
        self._config = config
        self._engine = engine or create_engine(config)

    @property
    def engine(self) -> InferenceEngine:
        """Get the inference engine."""
        return self._engine

    def load_model(self) -> None:
        """Load the ASR model.

        This should be called before serving requests.
        """
        self._engine.load_model()

    def unload_model(self) -> None:
        """Unload the ASR model."""
        self._engine.unload_model()

    async def StreamAudio(
        self,
        request_iterator: AsyncIterable[dictation_pb2.AudioFrame],
        context: grpc.aio.ServicerContext,
    ) -> AsyncIterator[dictation_pb2.DictationEvent]:
        """Stream audio frames and return transcription events.

        This is the main RPC for real-time dictation. The client streams
        audio frames, and the server responds with partial and final
        transcription events.
        """
        audio_frames: list[bytes] = []
        sample_rate: int = self._config.sample_rate_hz

        # Collect audio frames
        try:
            async for frame in request_iterator:
                audio_frames.append(frame.audio)

                # Track sample rate from first frame
                if frame.sample_rate_hz > 0:
                    sample_rate = frame.sample_rate_hz

                if frame.end_of_stream:
                    break

        except grpc.aio.AioRpcError as e:
            logger.error(f"Client stream error: {e}")
            yield dictation_pb2.DictationEvent(
                error=dictation_pb2.ErrorStatus(
                    code="STREAM_ERROR",
                    message=str(e),
                )
            )
            return

        # Process audio and generate events
        logger.debug(f"Processing {len(audio_frames)} audio frames")

        events = await self._engine.process_audio_stream(
            audio_frames, sample_rate
        )

        for event in events:
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
            elif event.kind == "status":
                yield dictation_pb2.DictationEvent(
                    status=dictation_pb2.EngineStatus(
                        mode=self._config.mode,
                        detail=event.text,
                    )
                )
            elif event.kind == "error":
                yield dictation_pb2.DictationEvent(
                    error=dictation_pb2.ErrorStatus(
                        code="TRANSCRIPTION_ERROR",
                        message=event.text,
                    )
                )

    async def GetHealth(
        self,
        request: dictation_pb2.HealthRequest,
        context: grpc.aio.ServicerContext,
    ) -> dictation_pb2.HealthStatus:
        """Return the health status of the backend."""
        is_ready = self._engine.is_loaded

        detail = (
            f"Engine: {self._config.mode}, Device: {self._engine.device}"
            if is_ready
            else "Model not loaded"
        )

        return dictation_pb2.HealthStatus(
            ready=is_ready,
            mode=self._config.mode,
            detail=detail,
        )


__all__ = [
    "DictationService",
]
