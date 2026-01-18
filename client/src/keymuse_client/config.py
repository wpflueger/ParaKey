from dataclasses import dataclass


@dataclass(frozen=True)
class ClientConfig:
    backend_host: str = "127.0.0.1"
    backend_port: int = 50051
    sample_rate_hz: int = 16000
    channels: int = 1
    frame_ms: int = 20
    backend_ready_timeout_s: float = 30.0
    backend_ready_poll_s: float = 0.5
