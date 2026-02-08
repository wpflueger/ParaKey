"""Backend configuration for ParaKey ASR service."""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class BackendConfig:
    """Configuration for the backend service."""

    # Server settings
    host: str = "127.0.0.1"
    port: int = 50051

    # Engine mode: 'nemo' for real inference
    mode: str = "nemo"

    # Model settings
    model_name: str = "nvidia/parakeet-tdt-0.6b-v3"
    device: Optional[str] = None  # None = auto-detect (GPU if available)

    # Audio settings
    sample_rate_hz: int = 16000


def load_config_from_env() -> BackendConfig:
    """Load configuration from environment variables.

    Returns:
        BackendConfig with values from environment or defaults.
    """
    import os

    return BackendConfig(
        host=os.getenv("PARAKEY_HOST", "127.0.0.1"),
        port=int(os.getenv("PARAKEY_PORT", "50051")),
        mode=os.getenv("PARAKEY_MODE", "nemo"),
        model_name=os.getenv(
            "PARAKEY_MODEL", "nvidia/parakeet-tdt-0.6b-v3"
        ),
        device=os.getenv("PARAKEY_DEVICE"),
        sample_rate_hz=int(os.getenv("PARAKEY_SAMPLE_RATE", "16000")),
    )


__all__ = [
    "BackendConfig",
    "load_config_from_env",
]
