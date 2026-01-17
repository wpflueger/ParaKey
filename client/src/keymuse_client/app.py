from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator

from keymuse_client.audio.capture import default_capture
from keymuse_client.config import ClientConfig
from keymuse_client.grpc_client import DictationClient
from keymuse_client.insertion.clipboard import sanitize_text
from keymuse_proto import dictation_pb2


LOGGER = logging.getLogger("keymuse.client")


async def run_once() -> None:
    config = ClientConfig()
    client = DictationClient(config.backend_host, config.backend_port)
    capture = default_capture(config)

    async def audio_stream() -> AsyncIterator[dictation_pb2.AudioFrame]:
        async for frame in capture.stream():
            yield frame

    audio_frames = audio_stream()
    async for event in client.stream_audio(audio_frames):
        if event.partial is not None:
            LOGGER.info("Partial: %s", event.partial.text)
        if event.final is not None:
            sanitized = sanitize_text(event.final.text)
            LOGGER.info("Final: %s", sanitized)

    await client.close()


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_once())


if __name__ == "__main__":
    main()
