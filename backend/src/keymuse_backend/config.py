"""Backend configuration for KeyMuse ASR service."""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class BackendConfig:
    """Configuration for the backend service."""

    # Server settings
    host: str = "127.0.0.1"
    port: int = 50051

    # Engine mode: 'nemo' for real inference, 'mock' for testing
    mode: str = "nemo"

    # Model settings (used when mode != 'mock')
    model_name: str = "nvidia/parakeet-tdt-0.6b-v3"
    device: Optional[str] = None  # None = auto-detect (GPU if available)

    # Streaming settings
    partial_every_n_frames: int = 10
    sample_rate_hz: int = 16000

    # Mock settings
    final_text: str = "Mock transcript from KeyMuse"


def load_config_from_env() -> BackendConfig:
    """Load configuration from environment variables.

    Returns:
        BackendConfig with values from environment or defaults.
    """
    import os

    return BackendConfig(
        host=os.getenv("KEYMUSE_HOST", "127.0.0.1"),
        port=int(os.getenv("KEYMUSE_PORT", "50051")),
        mode=os.getenv("KEYMUSE_MODE", "mock"),
        model_name=os.getenv(
            "KEYMUSE_MODEL", "nvidia/parakeet-tdt-0.6b-v3"
        ),
        device=os.getenv("KEYMUSE_DEVICE"),
        partial_every_n_frames=int(
            os.getenv("KEYMUSE_PARTIAL_INTERVAL", "10")
        ),
        sample_rate_hz=int(os.getenv("KEYMUSE_SAMPLE_RATE", "16000")),
    )


__all__ = [
    "BackendConfig",
    "load_config_from_env",
]
