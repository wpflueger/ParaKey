"""DictationOrchestrator - coordinates all KeyMuse client components.

This module provides the main orchestration logic that connects:
- Hotkey detection (start/stop recording)
- Audio capture (microphone input)
- Backend communication (gRPC streaming)
- Text insertion (clipboard + paste)
"""

from __future__ import annotations

import asyncio
import logging
import sys
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass
from enum import Enum, auto
from typing import Callable, Optional

from keymuse_client.audio.capture import (
    AudioCapture,
    SoundDeviceCapture,
    create_capture,
)
from keymuse_client.config import ClientConfig
from keymuse_client.grpc_client import DictationClient
from keymuse_client.hotkeys.state_machine import HotkeyController
from keymuse_client.insertion.clipboard import (
    ClipboardManager,
    add_to_history,
    sanitize_text,
)
from keymuse_client.insertion.keyboard import send_ctrl_v, send_unicode_string
from keymuse_client.insertion.window import (
    ForegroundWindowGuard,
    get_foreground_window,
    set_foreground_window,
)
from keymuse_proto import dictation_pb2

logger = logging.getLogger(__name__)


class DictationState(Enum):
    """Current state of the dictation system."""

    IDLE = auto()
    RECORDING = auto()
    PROCESSING = auto()
    INSERTING = auto()
    ERROR = auto()


@dataclass
class DictationResult:
    """Result of a dictation session."""

    text: str
    duration_seconds: float
    was_inserted: bool
    error: Optional[str] = None


class DictationOrchestrator:
    """Orchestrates the full dictation pipeline.

    This class coordinates:
    1. Hotkey detection to start/stop recording
    2. Audio capture while recording
    3. Streaming audio to backend for transcription
    4. Inserting final transcript into the active application

    Usage:
        orchestrator = DictationOrchestrator(config)
        await orchestrator.start()
        # ... runs until stopped ...
        await orchestrator.stop()
    """

    def __init__(
        self,
        config: ClientConfig,
        use_mock_audio: bool = False,
        use_mock_hotkey: bool = False,
    ) -> None:
        """Initialize the orchestrator.

        Args:
            config: Client configuration.
            use_mock_audio: Use mock audio capture (for testing).
            use_mock_hotkey: Use mock hotkey detection (for testing).
        """
        self._config = config
        self._state = DictationState.IDLE
        self._running = False

        # Components
        self._audio_capture: Optional[AudioCapture] = None
        self._hotkey_controller: Optional[HotkeyController] = None
        self._grpc_client: Optional[DictationClient] = None
        self._clipboard_manager = ClipboardManager()

        # Configuration flags
        self._use_mock_audio = use_mock_audio
        self._use_mock_hotkey = use_mock_hotkey or sys.platform != "win32"

        # Callbacks
        self._on_state_change: Optional[Callable[[DictationState], None]] = None
        self._on_partial: Optional[Callable[[str], None]] = None
        self._on_final: Optional[Callable[[str], None]] = None
        self._on_error: Optional[Callable[[str], None]] = None

        # Recording state
        self._recording_start_time: float = 0
        self._current_transcript: str = ""
        self._recording_task: Optional[asyncio.Task] = None

    @property
    def state(self) -> DictationState:
        """Get the current dictation state."""
        return self._state

    @property
    def is_running(self) -> bool:
        """Return True if the orchestrator is running."""
        return self._running

    @property
    def is_recording(self) -> bool:
        """Return True if currently recording."""
        return self._state == DictationState.RECORDING

    def set_callbacks(
        self,
        on_state_change: Optional[Callable[[DictationState], None]] = None,
        on_partial: Optional[Callable[[str], None]] = None,
        on_final: Optional[Callable[[str], None]] = None,
        on_error: Optional[Callable[[str], None]] = None,
    ) -> None:
        """Set event callbacks.

        Args:
            on_state_change: Called when dictation state changes.
            on_partial: Called when a partial transcript is received.
            on_final: Called when final transcript is received.
            on_error: Called when an error occurs.
        """
        self._on_state_change = on_state_change
        self._on_partial = on_partial
        self._on_final = on_final
        self._on_error = on_error

    def _set_state(self, state: DictationState) -> None:
        """Update state and notify callback."""
        if self._state != state:
            logger.debug(f"State change: {self._state.name} -> {state.name}")
            self._state = state
            if self._on_state_change:
                try:
                    self._on_state_change(state)
                except Exception as e:
                    logger.error(f"Error in state change callback: {e}")

    async def start(self) -> None:
        """Start the orchestrator.

        This initializes all components and begins listening for hotkeys.
        """
        if self._running:
            logger.warning("Orchestrator already running")
            return

        logger.info("Starting dictation orchestrator")

        # Initialize gRPC client
        self._grpc_client = DictationClient(
            self._config.backend_host,
            self._config.backend_port,
        )

        # Check backend health
        try:
            health = await self._grpc_client.health()
            logger.info(
                f"Backend connected: mode={health.mode}, ready={health.ready}"
            )
        except Exception as e:
            logger.warning(f"Backend health check failed: {e}")

        # Initialize audio capture
        self._audio_capture = create_capture(
            self._config, use_mock=self._use_mock_audio
        )

        # Initialize hotkey controller
        self._hotkey_controller = HotkeyController(
            on_activate=self._on_hotkey_activate,
            on_deactivate=self._on_hotkey_deactivate,
            use_mock=self._use_mock_hotkey,
        )

        # Start the hotkey listener
        loop = asyncio.get_event_loop()
        self._hotkey_controller.start(loop)

        self._running = True
        self._set_state(DictationState.IDLE)
        logger.info("Dictation orchestrator started")

    async def stop(self) -> None:
        """Stop the orchestrator and clean up resources."""
        if not self._running:
            return

        logger.info("Stopping dictation orchestrator")
        self._running = False

        # Cancel any active recording
        if self._recording_task and not self._recording_task.done():
            self._recording_task.cancel()
            try:
                await self._recording_task
            except asyncio.CancelledError:
                pass

        # Stop components
        if self._hotkey_controller:
            self._hotkey_controller.stop()

        if self._audio_capture and hasattr(self._audio_capture, "stop"):
            self._audio_capture.stop()

        if self._grpc_client:
            await self._grpc_client.close()

        self._set_state(DictationState.IDLE)
        logger.info("Dictation orchestrator stopped")

    def _on_hotkey_activate(self) -> None:
        """Called when hotkey chord is pressed (start recording)."""
        if self._state != DictationState.IDLE:
            logger.debug(f"Ignoring hotkey activate in state {self._state.name}")
            return

        logger.info("Hotkey activated - starting recording")
        self._recording_task = asyncio.create_task(self._run_recording())

    def _on_hotkey_deactivate(self) -> None:
        """Called when hotkey chord is released (stop recording)."""
        if self._state == DictationState.RECORDING:
            logger.info("Hotkey released - stopping recording")
            # Stop audio capture to end the stream
            if self._audio_capture and hasattr(self._audio_capture, "stop"):
                self._audio_capture.stop()

    async def _run_recording(self) -> None:
        """Execute a complete recording session."""
        self._set_state(DictationState.RECORDING)
        self._recording_start_time = time.time()
        self._current_transcript = ""

        try:
            # Start audio capture
            if isinstance(self._audio_capture, SoundDeviceCapture):
                self._audio_capture.start()

            # Stream audio to backend
            async for event in self._stream_to_backend():
                if event.partial is not None:
                    self._current_transcript = event.partial.text
                    logger.debug(f"Partial: {event.partial.text}")
                    if self._on_partial:
                        self._on_partial(event.partial.text)

                if event.final is not None:
                    self._current_transcript = event.final.text
                    logger.info(f"Final transcript: {event.final.text}")
                    if self._on_final:
                        self._on_final(event.final.text)

                if event.error is not None:
                    logger.error(f"Backend error: {event.error.message}")
                    if self._on_error:
                        self._on_error(event.error.message)

            # Insert the transcript
            if self._current_transcript:
                await self._insert_transcript(self._current_transcript)

        except asyncio.CancelledError:
            logger.info("Recording cancelled")
            raise
        except Exception as e:
            logger.error(f"Recording error: {e}")
            self._set_state(DictationState.ERROR)
            if self._on_error:
                self._on_error(str(e))
        finally:
            self._set_state(DictationState.IDLE)

    async def _stream_to_backend(
        self,
    ) -> AsyncIterator[dictation_pb2.DictationEvent]:
        """Stream audio frames to backend and yield events."""
        if self._grpc_client is None or self._audio_capture is None:
            return

        async def audio_generator() -> AsyncIterator[dictation_pb2.AudioFrame]:
            async for frame in self._audio_capture.stream():
                yield frame

        async for event in self._grpc_client.stream_audio(audio_generator()):
            yield event

    async def _insert_transcript(self, text: str) -> bool:
        """Insert transcript into the active application.

        Args:
            text: The transcript text to insert.

        Returns:
            True if insertion was successful.
        """
        if not text.strip():
            logger.debug("Empty transcript, skipping insertion")
            return False

        self._set_state(DictationState.INSERTING)

        # Sanitize the text
        sanitized = sanitize_text(text)

        # Save to history
        add_to_history(sanitized)

        # Get current foreground window for verification
        target_window = get_foreground_window()

        try:
            # Use clipboard for insertion
            with self._clipboard_manager:
                # Set clipboard content
                if not self._clipboard_manager.set_text(sanitized, sanitize=False):
                    logger.error("Failed to set clipboard text")
                    return False

                # Try to focus the target window before paste
                if sys.platform == "win32" and target_window is not None:
                    if not set_foreground_window(target_window.hwnd):
                        logger.warning("Failed to focus target window")

                # Small delay before paste
                await asyncio.sleep(0.05)

                # Verify window hasn't changed
                current_window = get_foreground_window()
                if target_window and current_window:
                    if target_window.hwnd != current_window.hwnd:
                        logger.warning("Foreground window changed, aborting paste")
                        return False

                # Send Ctrl+V
                if sys.platform == "win32":
                    if not send_ctrl_v():
                        logger.warning("Ctrl+V failed, falling back to Unicode input")
                        if not send_unicode_string(sanitized):
                            logger.error("Failed to send Unicode input")
                            return False
                else:
                    logger.info(f"Would insert (non-Windows): {sanitized}")

                # Small delay for paste to complete
                await asyncio.sleep(0.1)

            logger.info("Text inserted successfully")
            return True

        except Exception as e:
            logger.error(f"Error inserting text: {e}")
            if self._on_error:
                self._on_error(f"Insertion failed: {e}")
            return False

    async def run_forever(self) -> None:
        """Run the orchestrator until interrupted."""
        await self.start()

        try:
            # Keep running until stopped
            while self._running:
                await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            pass
        finally:
            await self.stop()


async def run_dictation(config: Optional[ClientConfig] = None) -> None:
    """Run the dictation client.

    Args:
        config: Optional client configuration.
    """
    config = config or ClientConfig()
    orchestrator = DictationOrchestrator(config)

    def on_state(state: DictationState) -> None:
        logger.info(f"State: {state.name}")

    def on_partial(text: str) -> None:
        print(f"\rPartial: {text}", end="", flush=True)

    def on_final(text: str) -> None:
        print(f"\nFinal: {text}")

    def on_error(error: str) -> None:
        print(f"\nError: {error}")

    orchestrator.set_callbacks(
        on_state_change=on_state,
        on_partial=on_partial,
        on_final=on_final,
        on_error=on_error,
    )

    await orchestrator.run_forever()


__all__ = [
    "DictationOrchestrator",
    "DictationState",
    "DictationResult",
    "run_dictation",
]
