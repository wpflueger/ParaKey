from dataclasses import dataclass


@dataclass(frozen=True)
class BackendConfig:
    host: str = "127.0.0.1"
    port: int = 50051
    mode: str = "mock"
    partial_every_n_frames: int = 10
    final_text: str = "Mock transcript from KeyMuse"
