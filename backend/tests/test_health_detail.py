"""Tests for health status detail fields."""

from __future__ import annotations

import pytest

from parakey_backend.config import BackendConfig
from parakey_backend.engine import MockInferenceEngine
from parakey_backend.service import DictationService
from parakey_proto import dictation_pb2


@pytest.mark.asyncio
async def test_health_detail_when_not_loaded() -> None:
    """GetHealth should report 'Model not loaded' when engine is not ready."""
    config = BackendConfig(mode="mock")
    engine = MockInferenceEngine(config)
    service = DictationService(config, engine=engine)

    health = await service.GetHealth(dictation_pb2.HealthRequest(), None)
    assert not health.ready
    assert health.detail == "Model not loaded"


@pytest.mark.asyncio
async def test_health_detail_when_loaded() -> None:
    """GetHealth should report engine mode and device when loaded."""
    config = BackendConfig(mode="mock")
    engine = MockInferenceEngine(config)
    service = DictationService(config, engine=engine)
    service.load_model()

    health = await service.GetHealth(dictation_pb2.HealthRequest(), None)
    assert health.ready
    assert "mock" in health.detail
    assert health.mode == "mock"


@pytest.mark.asyncio
async def test_health_reflects_unload() -> None:
    """GetHealth should report not ready after model is unloaded."""
    config = BackendConfig(mode="mock")
    engine = MockInferenceEngine(config)
    service = DictationService(config, engine=engine)
    service.load_model()

    health = await service.GetHealth(dictation_pb2.HealthRequest(), None)
    assert health.ready

    service.unload_model()
    health = await service.GetHealth(dictation_pb2.HealthRequest(), None)
    assert not health.ready
    assert health.detail == "Model not loaded"
