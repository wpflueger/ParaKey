"""Tests for CUDA warmup inference in ModelLoader."""

from __future__ import annotations

import logging
import sys
from unittest.mock import MagicMock, patch

import pytest

from parakey_backend.model import ModelLoader


class TestWarmup:
    """Tests for the _warmup method."""

    def test_warmup_called_during_load(self) -> None:
        """_warmup should be called as part of model loading."""
        mock_nemo_asr = MagicMock()
        mock_model = MagicMock()
        mock_model.cfg.sample_rate = 16000
        mock_nemo_asr.models.ASRModel.from_pretrained.return_value = mock_model

        # Inject the mock nemo module before load() tries to import it
        sys.modules["nemo"] = MagicMock()
        sys.modules["nemo.collections"] = MagicMock()
        sys.modules["nemo.collections.asr"] = mock_nemo_asr
        try:
            loader = ModelLoader.__new__(ModelLoader)
            loader._model_name = "test-model"
            loader._device = "cpu"
            loader._cache_dir = MagicMock()
            loader._cache_dir.exists = MagicMock(return_value=False)
            loader._model = None
            loader._loaded = False

            with patch.object(loader, "_warmup") as mock_warmup:
                loader.load()
                mock_warmup.assert_called_once()
        finally:
            del sys.modules["nemo.collections.asr"]
            del sys.modules["nemo.collections"]
            del sys.modules["nemo"]

    def test_warmup_skips_when_model_is_none(self) -> None:
        """_warmup should do nothing if model is None."""
        loader = ModelLoader.__new__(ModelLoader)
        loader._model = None
        # Should not raise
        loader._warmup()

    def test_warmup_logs_failure_as_warning(self, caplog) -> None:
        """_warmup failure should be logged as warning, not raise."""
        loader = ModelLoader.__new__(ModelLoader)
        mock_model = MagicMock()
        mock_model.cfg.sample_rate = 16000
        mock_model.transcribe.side_effect = RuntimeError("CUDA error")
        loader._model = mock_model

        with caplog.at_level(logging.WARNING, logger="parakey_backend.model"):
            loader._warmup()

        assert any("warmup failed" in r.message.lower() for r in caplog.records)

    def test_warmup_succeeds_with_mock_model(self) -> None:
        """_warmup should complete successfully with a cooperative mock model."""
        loader = ModelLoader.__new__(ModelLoader)
        mock_model = MagicMock()
        mock_model.cfg.sample_rate = 16000
        mock_model.transcribe.return_value = [""]
        loader._model = mock_model

        # Should not raise
        loader._warmup()
        mock_model.transcribe.assert_called_once()
