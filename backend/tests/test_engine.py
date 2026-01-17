"""Tests for the inference engine."""

from __future__ import annotations

import pytest

from keymuse_backend.config import BackendConfig
from keymuse_backend.engine import (
    EngineEvent,
    InferenceEngine,
    MockInferenceEngine,
    create_engine,
    generate_mock_events,
)


class TestEngineEvent:
    """Tests for EngineEvent dataclass."""

    def test_partial_event(self):
        event = EngineEvent(kind="partial", text="Testing...", stability=0.5)
        assert event.kind == "partial"
        assert event.text == "Testing..."
        assert event.stability == 0.5

    def test_final_event(self):
        event = EngineEvent(kind="final", text="Hello world")
        assert event.kind == "final"
        assert event.text == "Hello world"
        assert event.stability is None

    def test_immutable(self):
        event = EngineEvent(kind="final", text="test")
        with pytest.raises(Exception):  # FrozenInstanceError
            event.text = "modified"


class TestMockInferenceEngine:
    """Tests for MockInferenceEngine."""

    @pytest.fixture
    def config(self):
        return BackendConfig(
            mode="mock",
            final_text="Test transcript",
            partial_every_n_frames=5,
        )

    @pytest.fixture
    def engine(self, config):
        return MockInferenceEngine(config)

    def test_initial_state(self, engine):
        assert not engine.is_loaded
        assert engine.device == "mock"

    def test_load_unload(self, engine):
        engine.load_model()
        assert engine.is_loaded

        engine.unload_model()
        assert not engine.is_loaded

    @pytest.mark.asyncio
    async def test_transcribe(self, engine, config):
        engine.load_model()
        result = await engine.transcribe(b"\x00" * 1000)
        assert result == config.final_text

    @pytest.mark.asyncio
    async def test_process_audio_stream(self, engine, config):
        engine.load_model()

        # Create 15 frames to trigger 3 partial events (every 5 frames)
        frames = [b"\x00" * 320 for _ in range(15)]

        events = await engine.process_audio_stream(frames)

        # Should have 3 partials + 1 final
        partial_events = [e for e in events if e.kind == "partial"]
        final_events = [e for e in events if e.kind == "final"]

        assert len(partial_events) == 3
        assert len(final_events) == 1
        assert final_events[0].text == config.final_text


class TestCreateEngine:
    """Tests for create_engine factory."""

    def test_create_mock_engine(self):
        config = BackendConfig(mode="mock")
        engine = create_engine(config)
        assert isinstance(engine, MockInferenceEngine)

    def test_create_real_engine(self):
        config = BackendConfig(mode="nemo")
        engine = create_engine(config)
        assert isinstance(engine, InferenceEngine)


class TestGenerateMockEvents:
    """Tests for legacy generate_mock_events function."""

    def test_generates_partials(self):
        config = BackendConfig(partial_every_n_frames=3, final_text="Done")
        frames = [b"\x00" * 100 for _ in range(9)]

        events = generate_mock_events(config, frames)

        # 3 partials (at 3, 6, 9) + 1 final
        partial_events = [e for e in events if e.kind == "partial"]
        assert len(partial_events) == 3

    def test_always_ends_with_final(self):
        config = BackendConfig(final_text="The end")
        frames = [b"\x00" * 100 for _ in range(2)]

        events = generate_mock_events(config, frames)

        assert events[-1].kind == "final"
        assert events[-1].text == "The end"


class TestInferenceEngine:
    """Tests for real InferenceEngine (skipped without NeMo)."""

    @pytest.fixture
    def config(self):
        return BackendConfig(
            mode="nemo",
            model_name="nvidia/parakeet-tdt-0.6b-v3",
        )

    def test_initial_state(self, config):
        engine = InferenceEngine(config)
        assert not engine.is_loaded
        assert engine.device == "unknown"

    @pytest.mark.skip(reason="Requires NeMo and model download")
    @pytest.mark.asyncio
    async def test_transcribe_with_model(self, config):
        """Test with real model - skip unless explicitly testing inference."""
        engine = InferenceEngine(config)
        engine.load_model()

        # Create some test audio (1 second of silence)
        audio = b"\x00" * 32000  # 16kHz * 2 bytes

        result = await engine.transcribe(audio)

        # Silence should produce empty or minimal transcript
        assert isinstance(result, str)

        engine.unload_model()
