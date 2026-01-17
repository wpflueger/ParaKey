import base64
import json
from dataclasses import dataclass
from typing import Iterator, Optional, Union


@dataclass(frozen=True)
class AudioFrame:
    audio: bytes = b""
    sample_rate_hz: int = 0
    channels: int = 0
    sequence: int = 0
    end_of_stream: bool = False


@dataclass(frozen=True)
class TranscriptPartial:
    text: str = ""
    stability: float = 0.0


@dataclass(frozen=True)
class TranscriptFinal:
    text: str = ""
    from_cache: bool = False


@dataclass(frozen=True)
class EngineStatus:
    mode: str = ""
    detail: str = ""


@dataclass(frozen=True)
class ErrorStatus:
    code: str = ""
    message: str = ""


@dataclass(frozen=True)
class DictationEvent:
    partial: Optional[TranscriptPartial] = None
    final: Optional[TranscriptFinal] = None
    status: Optional[EngineStatus] = None
    error: Optional[ErrorStatus] = None


@dataclass(frozen=True)
class HealthRequest:
    pass


@dataclass(frozen=True)
class HealthStatus:
    ready: bool = False
    mode: str = ""
    detail: str = ""


def _encode_json(data: dict[str, object]) -> bytes:
    return json.dumps(data, separators=(",", ":")).encode("utf-8")


def _decode_json(data: bytes) -> dict[str, object]:
    return json.loads(data.decode("utf-8"))


def serialize_audio_frame(message: AudioFrame) -> bytes:
    payload = {
        "audio": base64.b64encode(message.audio).decode("ascii"),
        "sample_rate_hz": message.sample_rate_hz,
        "channels": message.channels,
        "sequence": message.sequence,
        "end_of_stream": message.end_of_stream,
    }
    return _encode_json(payload)


def deserialize_audio_frame(data: bytes) -> AudioFrame:
    payload = _decode_json(data)
    audio_value = payload.get("audio", "")
    sample_rate_value = payload.get("sample_rate_hz", 0)
    channels_value = payload.get("channels", 0)
    sequence_value = payload.get("sequence", 0)
    end_of_stream_value = payload.get("end_of_stream", False)
    return AudioFrame(
        audio=base64.b64decode(str(audio_value)),
        sample_rate_hz=int(str(sample_rate_value)),
        channels=int(str(channels_value)),
        sequence=int(str(sequence_value)),
        end_of_stream=bool(end_of_stream_value),
    )


def serialize_dictation_event(message: DictationEvent) -> bytes:
    payload: dict[str, object] = {}
    if message.partial is not None:
        payload["partial"] = {
            "text": message.partial.text,
            "stability": message.partial.stability,
        }
    if message.final is not None:
        payload["final"] = {
            "text": message.final.text,
            "from_cache": message.final.from_cache,
        }
    if message.status is not None:
        payload["status"] = {
            "mode": message.status.mode,
            "detail": message.status.detail,
        }
    if message.error is not None:
        payload["error"] = {
            "code": message.error.code,
            "message": message.error.message,
        }
    return _encode_json(payload)


def deserialize_dictation_event(data: bytes) -> DictationEvent:
    payload = _decode_json(data)
    return DictationEvent(
        partial=_decode_partial(payload.get("partial")),
        final=_decode_final(payload.get("final")),
        status=_decode_status(payload.get("status")),
        error=_decode_error(payload.get("error")),
    )


def serialize_health_request(message: HealthRequest) -> bytes:
    return _encode_json({})


def deserialize_health_request(data: bytes) -> HealthRequest:
    _decode_json(data)
    return HealthRequest()


def serialize_health_status(message: HealthStatus) -> bytes:
    payload = {
        "ready": message.ready,
        "mode": message.mode,
        "detail": message.detail,
    }
    return _encode_json(payload)


def deserialize_health_status(data: bytes) -> HealthStatus:
    payload = _decode_json(data)
    return HealthStatus(
        ready=bool(payload.get("ready", False)),
        mode=str(payload.get("mode", "")),
        detail=str(payload.get("detail", "")),
    )


def _decode_partial(value: object) -> Optional[TranscriptPartial]:
    if not isinstance(value, dict):
        return None
    return TranscriptPartial(
        text=str(value.get("text", "")),
        stability=float(value.get("stability", 0.0)),
    )


def _decode_final(value: object) -> Optional[TranscriptFinal]:
    if not isinstance(value, dict):
        return None
    return TranscriptFinal(
        text=str(value.get("text", "")),
        from_cache=bool(value.get("from_cache", False)),
    )


def _decode_status(value: object) -> Optional[EngineStatus]:
    if not isinstance(value, dict):
        return None
    return EngineStatus(
        mode=str(value.get("mode", "")),
        detail=str(value.get("detail", "")),
    )


def _decode_error(value: object) -> Optional[ErrorStatus]:
    if not isinstance(value, dict):
        return None
    return ErrorStatus(
        code=str(value.get("code", "")),
        message=str(value.get("message", "")),
    )


DictationPayload = Union[TranscriptPartial, TranscriptFinal, EngineStatus, ErrorStatus]


def iter_dictation_payload(event: DictationEvent) -> Iterator[DictationPayload]:
    for payload in (event.partial, event.final, event.status, event.error):
        if payload is not None:
            yield payload


def first_payload(event: DictationEvent) -> Optional[DictationPayload]:
    return next(iter_dictation_payload(event), None)


def ensure_single_payload(event: DictationEvent) -> DictationEvent:
    payloads = list(iter_dictation_payload(event))
    if len(payloads) != 1:
        raise ValueError("DictationEvent must contain exactly one payload")
    return event


def payload_kind(payload: DictationPayload) -> str:
    if isinstance(payload, TranscriptPartial):
        return "partial"
    if isinstance(payload, TranscriptFinal):
        return "final"
    if isinstance(payload, EngineStatus):
        return "status"
    return "error"


__all__ = [
    "AudioFrame",
    "TranscriptPartial",
    "TranscriptFinal",
    "EngineStatus",
    "ErrorStatus",
    "DictationEvent",
    "HealthRequest",
    "HealthStatus",
    "DictationPayload",
    "ensure_single_payload",
    "payload_kind",
    "first_payload",
    "iter_dictation_payload",
]
