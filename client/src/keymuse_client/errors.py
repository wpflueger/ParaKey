"""Error handling and retry logic for KeyMuse client.

This module provides:
- Custom exception types for different error categories
- Retry logic with exponential backoff
- Connection monitoring and reconnection
- Error recovery strategies
"""

from __future__ import annotations

import asyncio
import logging
import random
import time
from dataclasses import dataclass
from enum import Enum, auto
from typing import Callable, Optional, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ErrorCategory(Enum):
    """Categories of errors for handling decisions."""

    AUDIO = auto()  # Microphone/audio device errors
    NETWORK = auto()  # Backend connection errors
    BACKEND = auto()  # Backend processing errors
    CLIPBOARD = auto()  # Clipboard/insertion errors
    PERMISSION = auto()  # Permission denied errors
    TRANSIENT = auto()  # Temporary errors that may resolve
    FATAL = auto()  # Unrecoverable errors


class KeyMuseError(Exception):
    """Base exception for KeyMuse errors."""

    category: ErrorCategory = ErrorCategory.FATAL

    def __init__(self, message: str, cause: Optional[Exception] = None) -> None:
        super().__init__(message)
        self.cause = cause


class AudioError(KeyMuseError):
    """Audio capture related errors."""

    category = ErrorCategory.AUDIO


class AudioPermissionError(AudioError):
    """Microphone permission denied."""

    category = ErrorCategory.PERMISSION


class AudioDeviceError(AudioError):
    """Audio device disconnected or unavailable."""

    category = ErrorCategory.AUDIO


class NetworkError(KeyMuseError):
    """Network/connection errors."""

    category = ErrorCategory.NETWORK


class BackendUnavailableError(NetworkError):
    """Backend server not reachable."""

    pass


class BackendTimeoutError(NetworkError):
    """Backend request timed out."""

    category = ErrorCategory.TRANSIENT


class BackendError(KeyMuseError):
    """Backend processing errors."""

    category = ErrorCategory.BACKEND


class TranscriptionError(BackendError):
    """Error during transcription."""

    pass


class ModelLoadError(BackendError):
    """Error loading the ASR model."""

    pass


class ClipboardError(KeyMuseError):
    """Clipboard operation errors."""

    category = ErrorCategory.CLIPBOARD


class InsertionError(KeyMuseError):
    """Text insertion errors."""

    category = ErrorCategory.CLIPBOARD


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""

    max_attempts: int = 3
    initial_delay_ms: float = 100
    max_delay_ms: float = 5000
    exponential_base: float = 2.0
    jitter: bool = True


def calculate_backoff(
    attempt: int,
    config: RetryConfig,
) -> float:
    """Calculate backoff delay for a retry attempt.

    Args:
        attempt: Current attempt number (0-indexed).
        config: Retry configuration.

    Returns:
        Delay in seconds.
    """
    delay_ms = config.initial_delay_ms * (config.exponential_base ** attempt)
    delay_ms = min(delay_ms, config.max_delay_ms)

    if config.jitter:
        # Add random jitter up to 25%
        jitter_factor = 1.0 + random.uniform(-0.25, 0.25)
        delay_ms *= jitter_factor

    return delay_ms / 1000


async def retry_async(
    operation: Callable[[], T],
    config: Optional[RetryConfig] = None,
    on_retry: Optional[Callable[[int, Exception], None]] = None,
    retryable_exceptions: tuple = (Exception,),
) -> T:
    """Retry an async operation with exponential backoff.

    Args:
        operation: Async callable to retry.
        config: Retry configuration.
        on_retry: Callback called before each retry with (attempt, exception).
        retryable_exceptions: Tuple of exception types to retry on.

    Returns:
        Result of the operation.

    Raises:
        The last exception if all retries fail.
    """
    config = config or RetryConfig()
    last_exception: Optional[Exception] = None

    for attempt in range(config.max_attempts):
        try:
            return await operation()
        except retryable_exceptions as e:
            last_exception = e

            if attempt < config.max_attempts - 1:
                delay = calculate_backoff(attempt, config)
                logger.warning(
                    f"Attempt {attempt + 1}/{config.max_attempts} failed: {e}. "
                    f"Retrying in {delay:.2f}s..."
                )

                if on_retry:
                    on_retry(attempt, e)

                await asyncio.sleep(delay)
            else:
                logger.error(
                    f"All {config.max_attempts} attempts failed. Last error: {e}"
                )

    if last_exception:
        raise last_exception
    raise RuntimeError("Retry loop exited without result or exception")


class ConnectionMonitor:
    """Monitors backend connection and handles reconnection.

    This class periodically checks the backend health and attempts
    to reconnect if the connection is lost.
    """

    def __init__(
        self,
        health_check: Callable[[], bool],
        on_connected: Optional[Callable[[], None]] = None,
        on_disconnected: Optional[Callable[[], None]] = None,
        check_interval_ms: float = 5000,
        reconnect_config: Optional[RetryConfig] = None,
    ) -> None:
        """Initialize the connection monitor.

        Args:
            health_check: Async callable returning True if connected.
            on_connected: Callback when connection established.
            on_disconnected: Callback when connection lost.
            check_interval_ms: How often to check health.
            reconnect_config: Retry config for reconnection.
        """
        self._health_check = health_check
        self._on_connected = on_connected
        self._on_disconnected = on_disconnected
        self._check_interval = check_interval_ms / 1000
        self._reconnect_config = reconnect_config or RetryConfig(
            max_attempts=10,
            initial_delay_ms=1000,
            max_delay_ms=30000,
        )

        self._connected = False
        self._running = False
        self._task: Optional[asyncio.Task] = None

    @property
    def is_connected(self) -> bool:
        """Return True if currently connected."""
        return self._connected

    async def start(self) -> None:
        """Start the connection monitor."""
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._monitor_loop())
        logger.info("Connection monitor started")

    async def stop(self) -> None:
        """Stop the connection monitor."""
        self._running = False

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        logger.info("Connection monitor stopped")

    async def _monitor_loop(self) -> None:
        """Main monitoring loop."""
        while self._running:
            try:
                is_healthy = await asyncio.wait_for(
                    self._check_health(),
                    timeout=5.0,
                )

                if is_healthy and not self._connected:
                    self._connected = True
                    logger.info("Backend connection established")
                    if self._on_connected:
                        self._on_connected()

                elif not is_healthy and self._connected:
                    self._connected = False
                    logger.warning("Backend connection lost")
                    if self._on_disconnected:
                        self._on_disconnected()

                    # Attempt reconnection
                    await self._reconnect()

            except asyncio.TimeoutError:
                if self._connected:
                    self._connected = False
                    logger.warning("Backend health check timed out")
                    if self._on_disconnected:
                        self._on_disconnected()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Connection monitor error: {e}")

            await asyncio.sleep(self._check_interval)

    async def _check_health(self) -> bool:
        """Check backend health."""
        try:
            return await self._health_check()
        except Exception:
            return False

    async def _reconnect(self) -> None:
        """Attempt to reconnect with retries."""
        logger.info("Attempting to reconnect...")

        for attempt in range(self._reconnect_config.max_attempts):
            if not self._running:
                break

            try:
                if await self._check_health():
                    self._connected = True
                    logger.info("Reconnection successful")
                    if self._on_connected:
                        self._on_connected()
                    return
            except Exception as e:
                logger.debug(f"Reconnection attempt {attempt + 1} failed: {e}")

            delay = calculate_backoff(attempt, self._reconnect_config)
            await asyncio.sleep(delay)

        logger.error("Failed to reconnect after all attempts")


class ErrorRecovery:
    """Centralized error recovery strategies."""

    def __init__(
        self,
        on_error: Optional[Callable[[KeyMuseError], None]] = None,
    ) -> None:
        """Initialize error recovery.

        Args:
            on_error: Callback for all errors.
        """
        self._on_error = on_error
        self._error_counts: dict[ErrorCategory, int] = {}
        self._last_errors: dict[ErrorCategory, float] = {}

    def handle_error(self, error: KeyMuseError) -> bool:
        """Handle an error and determine if operation should retry.

        Args:
            error: The error to handle.

        Returns:
            True if operation should be retried.
        """
        category = error.category

        # Track error occurrence
        self._error_counts[category] = self._error_counts.get(category, 0) + 1
        self._last_errors[category] = time.time()

        # Log the error
        logger.error(f"[{category.name}] {error}")

        # Notify callback
        if self._on_error:
            self._on_error(error)

        # Determine if retryable
        if category == ErrorCategory.FATAL:
            return False
        elif category == ErrorCategory.PERMISSION:
            return False  # Need user action
        elif category == ErrorCategory.TRANSIENT:
            return True
        elif category == ErrorCategory.NETWORK:
            return True  # Will try reconnection
        elif category == ErrorCategory.AUDIO:
            # Retry a few times for audio errors
            return self._error_counts.get(category, 0) < 3
        else:
            return True

    def clear_errors(self, category: Optional[ErrorCategory] = None) -> None:
        """Clear error counts.

        Args:
            category: Specific category to clear, or all if None.
        """
        if category:
            self._error_counts.pop(category, None)
            self._last_errors.pop(category, None)
        else:
            self._error_counts.clear()
            self._last_errors.clear()

    def get_error_count(self, category: ErrorCategory) -> int:
        """Get error count for a category."""
        return self._error_counts.get(category, 0)


__all__ = [
    "ErrorCategory",
    "KeyMuseError",
    "AudioError",
    "AudioPermissionError",
    "AudioDeviceError",
    "NetworkError",
    "BackendUnavailableError",
    "BackendTimeoutError",
    "BackendError",
    "TranscriptionError",
    "ModelLoadError",
    "ClipboardError",
    "InsertionError",
    "RetryConfig",
    "calculate_backoff",
    "retry_async",
    "ConnectionMonitor",
    "ErrorRecovery",
]
