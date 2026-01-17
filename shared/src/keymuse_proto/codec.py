from __future__ import annotations

from typing import Callable, TypeVar

import grpc


T = TypeVar("T")


def identity(request: T) -> T:
    return request


def identity_bytes(message: T) -> bytes:
    raise TypeError("Serialization is handled in custom channel")


def build_channel() -> grpc.aio.Channel:
    raise NotImplementedError
