from dataclasses import dataclass
from typing import Iterable

from keymuse_backend.config import BackendConfig


@dataclass(frozen=True)
class EngineEvent:
    kind: str
    text: str
    stability: float | None = None


def generate_mock_events(config: BackendConfig, audio_frames: Iterable[bytes]) -> list[EngineEvent]:
    events: list[EngineEvent] = []
    for index, _frame in enumerate(audio_frames, start=1):
        if index % config.partial_every_n_frames == 0:
            events.append(
                EngineEvent(kind="partial", text="Listening...", stability=0.4)
            )
    events.append(EngineEvent(kind="final", text=config.final_text))
    return events
