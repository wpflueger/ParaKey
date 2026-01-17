"""KeyMuse client application entry point.

This module provides the main entry point for the KeyMuse dictation client.
It supports both the new orchestrator-based mode and a legacy single-shot mode.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import signal
import sys
from collections.abc import AsyncIterator

from keymuse_client.audio.capture import default_capture
from keymuse_client.config import ClientConfig
from keymuse_client.grpc_client import DictationClient
from keymuse_client.insertion.clipboard import sanitize_text
from keymuse_client.orchestrator import (
    DictationOrchestrator,
    DictationState,
    run_dictation,
)
from keymuse_proto import dictation_pb2

logger = logging.getLogger("keymuse.client")


async def run_once() -> None:
    """Run a single dictation session (legacy mode).

    This is the original behavior that streams mock audio to the backend
    and logs the results. Used for testing the gRPC connection.
    """
    config = ClientConfig()
    client = DictationClient(config.backend_host, config.backend_port)
    capture = default_capture(config)

    async def audio_stream() -> AsyncIterator[dictation_pb2.AudioFrame]:
        async for frame in capture.stream_duration(1.0):
            yield frame

    audio_frames = audio_stream()
    async for event in client.stream_audio(audio_frames):
        if event.partial is not None:
            logger.info("Partial: %s", event.partial.text)
        if event.final is not None:
            sanitized = sanitize_text(event.final.text)
            logger.info("Final: %s", sanitized)

    await client.close()


async def run_interactive() -> None:
    """Run in interactive mode with hotkey detection.

    This is the main operation mode that:
    - Listens for Ctrl+Alt hotkey to start recording
    - Captures audio while hotkey is held
    - Streams to backend for transcription
    - Pastes result into active application
    """
    config = ClientConfig()

    # Determine if we should use mocks based on platform
    use_mock_audio = sys.platform != "win32"
    use_mock_hotkey = sys.platform != "win32"

    orchestrator = DictationOrchestrator(
        config,
        use_mock_audio=use_mock_audio,
        use_mock_hotkey=use_mock_hotkey,
    )

    # Setup callbacks for console output
    def on_state(state: DictationState) -> None:
        status_icons = {
            DictationState.IDLE: "⏸",
            DictationState.RECORDING: "🔴",
            DictationState.PROCESSING: "⏳",
            DictationState.INSERTING: "📋",
            DictationState.ERROR: "❌",
        }
        icon = status_icons.get(state, "?")
        logger.info(f"{icon} State: {state.name}")

    def on_partial(text: str) -> None:
        # Clear line and print partial
        print(f"\r\033[K  Partial: {text}", end="", flush=True)

    def on_final(text: str) -> None:
        print(f"\n  Final: {text}")

    def on_error(error: str) -> None:
        logger.error(f"Error: {error}")

    orchestrator.set_callbacks(
        on_state_change=on_state,
        on_partial=on_partial,
        on_final=on_final,
        on_error=on_error,
    )

    # Setup signal handlers
    shutdown_event = asyncio.Event()

    def signal_handler():
        logger.info("Received shutdown signal")
        shutdown_event.set()

    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, signal_handler)
        except NotImplementedError:
            # Windows doesn't support add_signal_handler
            pass

    # Start the orchestrator
    await orchestrator.start()

    print("\n" + "=" * 50)
    print("KeyMuse Dictation Client")
    print("=" * 50)
    if sys.platform == "win32":
        print("Press Ctrl+Alt to start recording")
        print("Release to stop and insert text")
    else:
        print("Running in mock mode (non-Windows)")
        print("Real hotkey detection requires Windows")
    print("Press Ctrl+C to exit")
    print("=" * 50 + "\n")

    try:
        # Wait for shutdown signal
        await shutdown_event.wait()
    except asyncio.CancelledError:
        pass
    finally:
        await orchestrator.stop()


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="KeyMuse dictation client",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--mode",
        choices=["interactive", "once", "health"],
        default="interactive",
        help="Run mode: interactive (default), once (single test), health (check backend)",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Backend host (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=50051,
        help="Backend port (default: 50051)",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    return parser.parse_args()


async def check_health(config: ClientConfig) -> None:
    """Check backend health status."""
    client = DictationClient(config.backend_host, config.backend_port)
    try:
        health = await client.health()
        print(f"Backend Status:")
        print(f"  Ready: {health.ready}")
        print(f"  Mode: {health.mode}")
        print(f"  Detail: {health.detail}")
    except Exception as e:
        print(f"Failed to connect to backend: {e}")
        sys.exit(1)
    finally:
        await client.close()


def main() -> None:
    """Main entry point."""
    args = parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Create config from args
    config = ClientConfig(
        backend_host=args.host,
        backend_port=args.port,
    )

    # Run appropriate mode
    if args.mode == "health":
        asyncio.run(check_health(config))
    elif args.mode == "once":
        asyncio.run(run_once())
    else:
        try:
            asyncio.run(run_interactive())
        except KeyboardInterrupt:
            print("\nShutdown complete")


if __name__ == "__main__":
    main()
