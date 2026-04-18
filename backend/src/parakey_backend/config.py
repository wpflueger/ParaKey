"""Backend configuration for ParaKey ASR service."""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class BackendConfig:
    """Configuration for the backend service."""

    # Server settings
    host: str = "127.0.0.1"
    port: int = 50051

    # Engine mode: 'nemo' for CUDA/NeMo, 'mlx' for Apple Silicon, 'mock' for testing
    mode: str = "nemo"

    # Model settings
    model_name: str = "nvidia/parakeet-tdt-0.6b-v3"
    device: Optional[str] = None  # None = auto-detect

    # Audio settings
    sample_rate_hz: int = 16000

    # Mock mode settings (only used when mode='mock')
    final_text: str = ""
    partial_every_n_frames: int = 5


def load_config_from_env() -> "BackendConfig":
    """Load configuration from environment variables."""
    import os

    mode = os.getenv("PARAKEY_MODE", "nemo")

    default_model = (
        "mlx-community/whisper-large-v3-turbo"
        if mode == "mlx"
        else "nvidia/parakeet-tdt-0.6b-v3"
    )

    return BackendConfig(
        host=os.getenv("PARAKEY_HOST", "127.0.0.1"),
        port=int(os.getenv("PARAKEY_PORT", "50051")),
        mode=mode,
        model_name=os.getenv("PARAKEY_MODEL", default_model),
        device=os.getenv("PARAKEY_DEVICE"),
        sample_rate_hz=int(os.getenv("PARAKEY_SAMPLE_RATE", "16000")),
    )


__all__ = [
    "BackendConfig",
    "load_config_from_env",
]
