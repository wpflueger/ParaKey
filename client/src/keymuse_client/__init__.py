"""KeyMuse client package."""

from keymuse_client.config import ClientConfig
from keymuse_client.grpc_client import DictationClient
from keymuse_client.orchestrator import (
    DictationOrchestrator,
    DictationResult,
    DictationState,
)
from keymuse_client.settings import (
    AppSettings,
    SettingsManager,
    get_settings_manager,
    load_settings,
    save_settings,
)

__version__ = "0.1.0"

__all__ = [
    "ClientConfig",
    "DictationClient",
    "DictationOrchestrator",
    "DictationResult",
    "DictationState",
    "AppSettings",
    "SettingsManager",
    "get_settings_manager",
    "load_settings",
    "save_settings",
    "__version__",
]
