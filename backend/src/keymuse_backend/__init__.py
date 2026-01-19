"""KeyMuse backend package."""

from keymuse_backend.config import BackendConfig, load_config_from_env
from keymuse_backend.engine import (
    EngineEvent,
    InferenceEngine,
    create_engine,
)
from keymuse_backend.server import BackendServer
from keymuse_backend.service import DictationService

__version__ = "0.1.0"

__all__ = [
    "BackendConfig",
    "BackendServer",
    "DictationService",
    "EngineEvent",
    "InferenceEngine",
    "create_engine",
    "load_config_from_env",
    "__version__",
]
