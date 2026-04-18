"""Model loading for ParaKey ASR — NeMo (CUDA/Windows) and MLX Whisper (Apple Silicon).

NeMo backend uses the NVIDIA Parakeet TDT model with CUDA.
MLX backend uses mlx-whisper with Apple Silicon GPU via the Metal Performance Shaders framework.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "nvidia/parakeet-tdt-0.6b-v3"
DEFAULT_MLX_MODEL = "mlx-community/whisper-large-v3-turbo"

CACHE_DIR = Path.home() / ".cache" / "huggingface" / "hub"


class ModelLoadError(Exception):
    """Raised when model loading fails."""

    pass


def get_device() -> str:
    """Detect the best available CUDA device for NeMo inference.

    Returns:
        'cuda' if a GPU is available.

    Raises:
        ModelLoadError: If CUDA is not available.
    """
    import torch

    if torch.cuda.is_available():
        device_name = torch.cuda.get_device_name(0)
        logger.info(f"CUDA available: {device_name}")
        return "cuda"

    raise ModelLoadError(
        "CUDA is required for the Parakeet model. "
        "Ensure a compatible GPU and CUDA-enabled PyTorch are installed."
    )


def get_gpu_memory_mb() -> Optional[float]:
    """Get available GPU memory in MB, or None if no CUDA GPU."""
    try:
        import torch

        if not torch.cuda.is_available():
            return None
        props = torch.cuda.get_device_properties(0)
        total_memory = props.total_memory / (1024 * 1024)
        allocated = torch.cuda.memory_allocated(0) / (1024 * 1024)
        return total_memory - allocated
    except ImportError:
        return None


def get_model_cache_info() -> dict:
    """Get information about model cache location and status."""
    cache_dir = CACHE_DIR
    hf_home = os.environ.get("HF_HOME")
    if hf_home:
        cache_dir = Path(hf_home) / "hub"

    xdg_cache = os.environ.get("XDG_CACHE_HOME")
    if xdg_cache and not hf_home:
        cache_dir = Path(xdg_cache) / "huggingface" / "hub"

    model_cached = False
    cache_size_mb = 0.0

    if cache_dir.exists():
        for item in cache_dir.iterdir():
            if "parakeet" in item.name.lower() or "whisper" in item.name.lower():
                model_cached = True
                if item.is_dir():
                    for f in item.rglob("*"):
                        if f.is_file():
                            cache_size_mb += f.stat().st_size / (1024 * 1024)

    return {
        "cache_dir": str(cache_dir),
        "model_cached": model_cached,
        "cache_size_mb": round(cache_size_mb, 1),
    }


class ModelLoader:
    """Loads and runs the NeMo Parakeet TDT model on CUDA."""

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        device: Optional[str] = None,
        cache_dir: Optional[Path] = None,
    ) -> None:
        self._model_name = model_name
        self._device = device or get_device()
        self._cache_dir = cache_dir or CACHE_DIR
        self._model = None
        self._loaded = False
        self._cache_dir.mkdir(parents=True, exist_ok=True)

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def device(self) -> str:
        return self._device

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    def load(self, force_reload: bool = False) -> None:
        """Load the NeMo Parakeet model from HuggingFace."""
        if self._loaded and not force_reload:
            logger.info("Model already loaded")
            return

        try:
            import nemo.collections.asr as nemo_asr

            cache_info = get_model_cache_info()
            logger.info(f"Model cache directory: {cache_info['cache_dir']}")
            if cache_info["model_cached"]:
                logger.info(f"Model already cached ({cache_info['cache_size_mb']:.1f} MB)")
            else:
                logger.info("Model not cached - will download (~1.2 GB)")

            logger.info(f"Loading model: {self._model_name} on {self._device}")

            self._model = nemo_asr.models.ASRModel.from_pretrained(
                self._model_name,
                map_location=self._device,
            )
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
        """Unload the model and free GPU memory."""
        if self._model is not None:
            import torch

            del self._model
            self._model = None
            self._loaded = False
            if self._device == "cuda" and torch.cuda.is_available():
                torch.cuda.empty_cache()
            logger.info("Model unloaded")

    def transcribe(self, audio_data: bytes, sample_rate: int = 16000) -> str:
        """Transcribe raw PCM audio bytes (16-bit signed)."""
        if not self._loaded or self._model is None:
            raise ModelLoadError("Model not loaded - call load() first")

        import numpy as np
        import torch

        audio_array = np.frombuffer(audio_data, dtype="int16")
        audio_float = audio_array.astype("float32") / 32768.0
        if audio_float.ndim > 1:
            audio_float = audio_float.flatten()

        audio_tensor = torch.from_numpy(audio_float).float()

        with torch.no_grad():
            try:
                transcripts = self._model.transcribe(audio=[audio_tensor])
            except (TypeError, RuntimeError):
                try:
                    transcripts = self._model.transcribe(audio=[audio_float.tolist()])
                except TypeError:
                    transcripts = self._model.transcribe([audio_float.tolist()])

        if transcripts and len(transcripts) > 0:
            first = transcripts[0]
            if hasattr(first, "text"):
                return str(first.text)
            return str(first)
        return ""

    def get_model(self):
        return self._model


class MLXModelLoader:
    """Loads and runs mlx-whisper on Apple Silicon via MLX."""

    def __init__(self, model_name: str = DEFAULT_MLX_MODEL) -> None:
        self._model_name = model_name
        self._loaded = False

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def device(self) -> str:
        return "mlx"

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    def load(self, force_reload: bool = False) -> None:
        """Verify mlx-whisper is importable; the model downloads on first transcribe."""
        if self._loaded and not force_reload:
            logger.info("MLX model already loaded")
            return

        try:
            import mlx_whisper  # noqa: F401

            self._loaded = True
            logger.info(f"MLX Whisper ready: {self._model_name}")
        except ImportError as e:
            raise ModelLoadError(
                f"mlx-whisper not installed. Install with: pip install mlx-whisper: {e}"
            ) from e

    def unload(self) -> None:
        self._loaded = False
        logger.info("MLX model unloaded")

    def transcribe(self, audio_data: bytes, sample_rate: int = 16000) -> str:
        """Transcribe raw PCM audio bytes (16-bit signed) using MLX Whisper."""
        if not self._loaded:
            raise ModelLoadError("Model not loaded - call load() first")

        import mlx_whisper
        import numpy as np

        audio_array = np.frombuffer(audio_data, dtype="int16").astype("float32") / 32768.0
        if audio_array.ndim > 1:
            audio_array = audio_array.flatten()

        result = mlx_whisper.transcribe(
            audio_array,
            path_or_hf_repo=self._model_name,
            verbose=None,
        )
        return result.get("text", "").strip()


_global_model: Optional[ModelLoader] = None


def get_model_loader(
    model_name: str = DEFAULT_MODEL,
    device: Optional[str] = None,
) -> ModelLoader:
    """Get or create the global NeMo ModelLoader singleton."""
    global _global_model

    if _global_model is None:
        _global_model = ModelLoader(model_name=model_name, device=device)

    return _global_model


def load_model(
    model_name: str = DEFAULT_MODEL,
    device: Optional[str] = None,
) -> ModelLoader:
    """Load and return the global NeMo model instance."""
    loader = get_model_loader(model_name, device)
    loader.load()
    return loader


__all__ = [
    "ModelLoader",
    "MLXModelLoader",
    "ModelLoadError",
    "get_device",
    "get_gpu_memory_mb",
    "get_model_cache_info",
    "get_model_loader",
    "load_model",
    "DEFAULT_MODEL",
    "DEFAULT_MLX_MODEL",
]
