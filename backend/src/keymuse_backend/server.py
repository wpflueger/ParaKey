import asyncio
import logging

import grpc

from keymuse_backend.config import BackendConfig
from keymuse_proto import dictation_pb2_grpc
from keymuse_backend.service import DictationService


LOGGER = logging.getLogger("keymuse.backend")


def create_server(config: BackendConfig) -> grpc.aio.Server:
    server = grpc.aio.server()
    dictation_pb2_grpc.add_DictationServiceServicer_to_server(
        DictationService(config), server
    )
    server.add_insecure_port(f"{config.host}:{config.port}")
    return server


async def serve_forever() -> None:
    config = BackendConfig()
    server = create_server(config)
    LOGGER.info("Starting backend on %s:%s", config.host, config.port)
    await server.start()
    await server.wait_for_termination()


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    asyncio.run(serve_forever())


if __name__ == "__main__":
    main()
