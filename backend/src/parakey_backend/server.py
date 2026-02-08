"""gRPC server entry point for ParaKey backend."""

from __future__ import annotations

import asyncio
import logging
import signal
from typing import Optional

import grpc

from parakey_backend.config import BackendConfig, load_config_from_env
from parakey_backend.service import DictationService
from parakey_proto import dictation_pb2_grpc

logger = logging.getLogger("parakey.backend")


class BackendServer:
    """ParaKey backend gRPC server."""

    def __init__(self, config: Optional[BackendConfig] = None) -> None:
        """Initialize the backend server.

        Args:
            config: Backend configuration. If None, loads from environment.
        """
        self._config = config or load_config_from_env()
        self._service = DictationService(self._config)
        self._server: Optional[grpc.aio.Server] = None
        self._shutdown_event = asyncio.Event()

    @property
    def config(self) -> BackendConfig:
        """Get the server configuration."""
        return self._config

    @property
    def service(self) -> DictationService:
        """Get the dictation service."""
        return self._service

    def _create_server(self) -> grpc.aio.Server:
        """Create and configure the gRPC server."""
        server = grpc.aio.server()
        dictation_pb2_grpc.add_DictationServiceServicer_to_server(
            self._service, server
        )
        server.add_insecure_port(f"{self._config.host}:{self._config.port}")
        return server

    async def start(self) -> None:
        """Start the backend server.

        Starts the gRPC server first so clients can connect and check health,
        then loads the model. GetHealth returns ready=false until loading completes.
        """
        logger.info(f"Starting ParaKey backend (mode: {self._config.mode})")

        # Start gRPC server first so health checks work during model loading
        self._server = self._create_server()
        await self._server.start()
        logger.info(
            f"Backend listening on {self._config.host}:{self._config.port}"
        )

        # Load the model in a thread so gRPC can serve health checks during loading
        logger.info("Loading model...")
        await asyncio.to_thread(self._service.load_model)
        logger.info(f"Model loaded on {self._service.engine.device}")

    async def stop(self) -> None:
        """Stop the backend server gracefully."""
        if self._server is not None:
            logger.info("Stopping server...")

            # Grace period for in-flight requests
            await self._server.stop(grace=5.0)
            self._server = None

        # Unload the model
        self._service.unload_model()
        logger.info("Server stopped")

    async def wait_for_termination(self) -> None:
        """Wait for the server to be terminated."""
        if self._server is not None:
            await self._server.wait_for_termination()

    async def run(self) -> None:
        """Run the server until interrupted.

        This method handles SIGINT and SIGTERM for graceful shutdown.
        """
        # Setup signal handlers
        loop = asyncio.get_event_loop()

        def signal_handler():
            logger.info("Received shutdown signal")
            self._shutdown_event.set()

        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, signal_handler)
            except NotImplementedError:
                # Windows doesn't support add_signal_handler
                pass

        try:
            await self.start()

            # Wait for shutdown signal or server termination
            shutdown_task = asyncio.create_task(self._shutdown_event.wait())
            wait_task = asyncio.create_task(self.wait_for_termination())

            done, pending = await asyncio.wait(
                [shutdown_task, wait_task],
                return_when=asyncio.FIRST_COMPLETED,
            )

            # Cancel pending tasks
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        finally:
            await self.stop()


def create_server(config: BackendConfig) -> grpc.aio.Server:
    """Create a gRPC server (legacy compatibility).

    Args:
        config: Backend configuration.

    Returns:
        Configured gRPC server.
    """
    service = DictationService(config)

    server = grpc.aio.server()
    dictation_pb2_grpc.add_DictationServiceServicer_to_server(service, server)
    server.add_insecure_port(f"{config.host}:{config.port}")

    # Note: load_model() blocks synchronously; callers must start the server
    # separately if they need health checks to be available during loading.
    service.load_model()

    return server


async def serve_forever() -> None:
    """Run the backend server indefinitely."""
    server = BackendServer()
    await server.run()


def main() -> None:
    """Main entry point for the backend server."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    asyncio.run(serve_forever())


if __name__ == "__main__":
    main()
