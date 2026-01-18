"""Model loading and caching for NVIDIA Parakeet TDT ASR model.

This module handles downloading, caching, and loading the Parakeet TDT model
from NVIDIA NeMo, with GPU detection and CPU fallback.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

import torch

logger = logging.getLogger(__name__)

# Default model name
DEFAULT_MODEL = "nvidia/parakeet-tdt-0.6b-v3"

# Cache directory for models
CACHE_DIR = Path.home() / ".cache" / "keymuse" / "models"


class ModelLoadError(Exception):
    """Raised when model loading fails."""

    pass


def get_device() -> str:
    """Detect the best available device for inference.

    Returns:
        'cuda' if a GPU is available.

    Raises:
        ModelLoadError: If CUDA is not available.
    """
    if torch.cuda.is_available():
        device_name = torch.cuda.get_device_name(0)
        logger.info(f"CUDA available: {device_name}")
        return "cuda"

    raise ModelLoadError(
        "CUDA is required for the Parakeet model. "
        "Ensure a compatible GPU and CUDA-enabled PyTorch are installed."
    )


def get_gpu_memory_mb() -> Optional[float]:
    """Get available GPU memory in MB.

    Returns:
        Available GPU memory in MB, or None if no GPU.
    """
    if not torch.cuda.is_available():
        return None

    props = torch.cuda.get_device_properties(0)
    total_memory = props.total_memory / (1024 * 1024)
    allocated = torch.cuda.memory_allocated(0) / (1024 * 1024)
    return total_memory - allocated


class ModelLoader:
    """Handles loading and caching of the Parakeet TDT ASR model."""

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        device: Optional[str] = None,
        cache_dir: Optional[Path] = None,
    ) -> None:
        """Initialize the model loader.

        Args:
            model_name: HuggingFace model name to load.
            device: Device to use ('cuda' or 'cpu'). If None, auto-detect.
            cache_dir: Directory to cache downloaded models.
        """
        self._model_name = model_name
        self._device = device or get_device()
        self._cache_dir = cache_dir or CACHE_DIR
        self._model = None
        self._loaded = False

        # Ensure cache directory exists
        self._cache_dir.mkdir(parents=True, exist_ok=True)

    @property
    def model_name(self) -> str:
        """Return the model name."""
        return self._model_name

    @property
    def device(self) -> str:
        """Return the device being used."""
        return self._device

    @property
    def is_loaded(self) -> bool:
        """Return True if the model is loaded."""
        return self._loaded

    def load(self, force_reload: bool = False) -> None:
        """Load the model.

        Args:
            force_reload: If True, reload even if already loaded.

        Raises:
            ModelLoadError: If model loading fails or CUDA is unavailable.
        """
        if self._loaded and not force_reload:
            logger.info("Model already loaded")
            return

        try:
            # Import NeMo here to avoid import errors if not installed
            import nemo.collections.asr as nemo_asr

            logger.info(f"Loading model: {self._model_name}")
            logger.info(f"Device: {self._device}")

            # Load the model from HuggingFace
            self._model = nemo_asr.models.ASRModel.from_pretrained(
                self._model_name,
                map_location=self._device,
            )

            # Move to device and set to eval mode
            self._model = self._model.to(self._device)
            self._model.eval()

            self._loaded = True
            logger.info(f"Model loaded successfully on {self._device}")

        except ImportError as e:
            raise ModelLoadError(
                f"NeMo not installed. Install with: pip install nemo-toolkit[asr]: {e}"
            ) from e
        except Exception as e:
            raise ModelLoadError(f"Failed to load model: {e}") from e

    def unload(self) -> None:
        """Unload the model and free memory."""
        if self._model is not None:
            del self._model
            self._model = None
            self._loaded = False

            # Clear CUDA cache if using GPU
            if self._device == "cuda" and torch.cuda.is_available():
                torch.cuda.empty_cache()

            logger.info("Model unloaded")

    def transcribe(
        self,
        audio_data: bytes,
        sample_rate: int = 16000,
    ) -> str:
        """Transcribe audio data.

        Args:
            audio_data: Raw PCM audio bytes (16-bit signed).
            sample_rate: Sample rate of the audio.

        Returns:
            Transcribed text.

        Raises:
            ModelLoadError: If model is not loaded.
        """
        if not self._loaded or self._model is None:
            raise ModelLoadError("Model not loaded - call load() first")

        import numpy as np

        # Convert bytes to numpy array (16-bit signed PCM)
        audio_array = np.frombuffer(audio_data, dtype=np.int16)

        # Normalize to float32 [-1, 1]
        audio_float = audio_array.astype(np.float32) / 32768.0

        # Transcribe
        with torch.no_grad():
            transcripts = self._model.transcribe([audio_float])

        if transcripts and len(transcripts) > 0:
            first = transcripts[0]
            if hasattr(first, "text"):
                return str(first.text)
            return str(first)
        return ""

    def transcribe_file(self, audio_path: str) -> str:
        """Transcribe an audio file.

        Args:
            audio_path: Path to the audio file.

        Returns:
            Transcribed text.

        Raises:
            ModelLoadError: If model is not loaded.
        """
        if not self._loaded or self._model is None:
            raise ModelLoadError("Model not loaded - call load() first")

        with torch.no_grad():
            transcripts = self._model.transcribe([audio_path])

        if transcripts and len(transcripts) > 0:
            first = transcripts[0]
            if hasattr(first, "text"):
                return str(first.text)
            return str(first)
        return ""

    def get_model(self):
        """Get the underlying NeMo model.

        Returns:
            The loaded ASR model, or None if not loaded.
        """
        return self._model


# Global model instance for singleton pattern
_global_model: Optional[ModelLoader] = None


def get_model_loader(
    model_name: str = DEFAULT_MODEL,
    device: Optional[str] = None,
) -> ModelLoader:
    """Get or create the global model loader instance.

    This provides singleton access to the model loader to avoid
    loading the model multiple times.

    Args:
        model_name: HuggingFace model name.
        device: Device to use.

    Returns:
        The global ModelLoader instance.
    """
    global _global_model

    if _global_model is None:
        _global_model = ModelLoader(model_name=model_name, device=device)

    return _global_model


def load_model(
    model_name: str = DEFAULT_MODEL,
    device: Optional[str] = None,
) -> ModelLoader:
    """Load the global model instance.

    Args:
        model_name: HuggingFace model name.
        device: Device to use.

    Returns:
        The loaded ModelLoader instance.
    """
    loader = get_model_loader(model_name, device)
    loader.load()
    return loader


__all__ = [
    "ModelLoader",
    "ModelLoadError",
    "get_device",
    "get_gpu_memory_mb",
    "get_model_loader",
    "load_model",
    "DEFAULT_MODEL",
]
