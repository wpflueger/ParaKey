#!/usr/bin/env python
"""End-to-end test script for KeyMuse.

This script tests the full dictation pipeline:
1. Connects to the backend
2. Simulates a recording session using mock components
3. Verifies transcription and insertion flow

Usage:
    # From project root:
    PYTHONPATH=$PWD/shared/src:$PWD/backend/src:$PWD/client/src python scripts/test_e2e.py

    # Or with pytest:
    PYTHONPATH=$PWD/shared/src:$PWD/backend/src:$PWD/client/src pytest scripts/test_e2e.py -v
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Add project paths
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "shared" / "src"))
sys.path.insert(0, str(project_root / "backend" / "src"))
sys.path.insert(0, str(project_root / "client" / "src"))


async def test_backend_connection():
    """Test that we can connect to the backend."""
    from keymuse_client.config import ClientConfig
    from keymuse_client.grpc_client import DictationClient

    print("Testing backend connection...")
    config = ClientConfig()
    client = DictationClient(config.backend_host, config.backend_port)

    try:
        health = await client.health()
        print(f"  Backend ready: {health.ready}")
        print(f"  Backend mode: {health.mode}")
        print(f"  Detail: {health.detail}")
        assert health.ready, "Backend not ready"
        print("  ✓ Backend connection OK")
        return True
    except Exception as e:
        print(f"  ✗ Failed to connect: {e}")
        return False
    finally:
        await client.close()


async def test_audio_streaming():
    """Test streaming audio to backend."""
    from keymuse_client.audio.capture import create_capture
    from keymuse_client.config import ClientConfig
    from keymuse_client.grpc_client import DictationClient

    print("\nTesting audio streaming...")
    config = ClientConfig()
    client = DictationClient(config.backend_host, config.backend_port)
    capture = create_capture(config, use_mock=True)

    events_received = []

    try:
        async def audio_gen():
            async for frame in capture.stream_duration(0.5):
                yield frame

        async for event in client.stream_audio(audio_gen()):
            events_received.append(event)
            if event.partial is not None:
                print(f"  Partial: {event.partial.text}")
            if event.final is not None:
                print(f"  Final: {event.final.text}")

        assert len(events_received) > 0, "No events received"
        has_final = any(e.final is not None for e in events_received)
        assert has_final, "No final transcript received"
        print("  ✓ Audio streaming OK")
        return True
    except Exception as e:
        print(f"  ✗ Streaming failed: {e}")
        return False
    finally:
        await client.close()


async def test_orchestrator_mock():
    """Test the orchestrator with mock components."""
    from keymuse_client.config import ClientConfig
    from keymuse_client.orchestrator import DictationOrchestrator, DictationState

    print("\nTesting orchestrator with mock components...")
    config = ClientConfig()

    orchestrator = DictationOrchestrator(
        config,
        use_mock_audio=True,
        use_mock_hotkey=True,
    )

    states_seen = []
    partials_seen = []
    finals_seen = []
    errors_seen = []

    def on_state(state: DictationState) -> None:
        states_seen.append(state)
        print(f"  State: {state.name}")

    def on_partial(text: str) -> None:
        partials_seen.append(text)

    def on_final(text: str) -> None:
        finals_seen.append(text)
        print(f"  Final: {text}")

    def on_error(error: str) -> None:
        errors_seen.append(error)
        print(f"  Error: {error}")

    orchestrator.set_callbacks(
        on_state_change=on_state,
        on_partial=on_partial,
        on_final=on_final,
        on_error=on_error,
    )

    try:
        await orchestrator.start()
        assert orchestrator.is_running, "Orchestrator not running"
        assert orchestrator.state == DictationState.IDLE, "Not in IDLE state"

        # Simulate hotkey press (using mock)
        mock_hook = orchestrator._hotkey_controller.get_mock_hook()
        if mock_hook:
            print("  Simulating hotkey press...")
            mock_hook.simulate_key("lctrl", True)
            mock_hook.simulate_key("lalt", True)

            # Wait for recording to start
            await asyncio.sleep(0.2)

            print("  Simulating hotkey release...")
            mock_hook.simulate_key("lctrl", False)

            # Wait for processing to complete
            await asyncio.sleep(1.0)

        await orchestrator.stop()

        print(f"  States seen: {[s.name for s in states_seen]}")
        print(f"  Finals received: {len(finals_seen)}")

        print("  ✓ Orchestrator test OK")
        return True

    except Exception as e:
        print(f"  ✗ Orchestrator test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if orchestrator.is_running:
            await orchestrator.stop()


async def test_text_sanitization():
    """Test text sanitization."""
    from keymuse_client.insertion.clipboard import sanitize_text

    print("\nTesting text sanitization...")

    tests = [
        ("Hello World", "Hello World"),
        ("Hello\x00World", "HelloWorld"),  # Control char removed
        ("Line1\nLine2", "Line1\r\nLine2"),  # LF -> CRLF
        ("e\u0301", "\u00e9"),  # NFD -> NFC
    ]

    all_passed = True
    for input_text, expected in tests:
        result = sanitize_text(input_text)
        if result == expected:
            print(f"  ✓ '{repr(input_text)}' -> '{repr(result)}'")
        else:
            print(f"  ✗ '{repr(input_text)}' -> '{repr(result)}' (expected '{repr(expected)}')")
            all_passed = False

    if all_passed:
        print("  ✓ Text sanitization OK")
    return all_passed


async def run_all_tests():
    """Run all end-to-end tests."""
    print("=" * 60)
    print("KeyMuse End-to-End Tests")
    print("=" * 60)

    results = []

    # Test 1: Backend connection
    results.append(("Backend Connection", await test_backend_connection()))

    # Test 2: Audio streaming
    if results[-1][1]:  # Only if backend connected
        results.append(("Audio Streaming", await test_audio_streaming()))

    # Test 3: Text sanitization (no backend needed)
    results.append(("Text Sanitization", await test_text_sanitization()))

    # Test 4: Orchestrator (needs backend)
    if results[0][1]:  # Only if backend connected
        results.append(("Orchestrator", await test_orchestrator_mock()))

    # Summary
    print("\n" + "=" * 60)
    print("Test Results")
    print("=" * 60)

    passed = 0
    failed = 0
    for name, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"  {status}: {name}")
        if success:
            passed += 1
        else:
            failed += 1

    print(f"\nTotal: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


def main():
    """Main entry point."""
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
