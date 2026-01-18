"""Windows-first launcher that runs backend and client as a single app.

This module starts the backend gRPC server in a managed subprocess and then
runs the client UI/orchestrator in the current process. It is intended to be
used on Windows to provide a single entrypoint while keeping two managed
processes for performance.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Deque, Optional

from collections import deque
import threading

from keymuse_client.app import check_health, run_interactive, run_once
from keymuse_client.config import ClientConfig
from keymuse_client.grpc_client import DictationClient

logger = logging.getLogger("keymuse.launcher")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _build_pythonpath() -> str:
    root = _repo_root()
    paths = [
        root / "shared" / "src",
        root / "backend" / "src",
        root / "client" / "src",
    ]
    existing = os.environ.get("PYTHONPATH", "")
    merged = os.pathsep.join(str(p) for p in paths if p.exists())
    if existing:
        merged = f"{merged}{os.pathsep}{existing}"
    return merged


def _start_backend(
    *,
    host: str,
    port: int,
    mode: Optional[str],
    device: Optional[str],
    model: Optional[str],
) -> tuple[subprocess.Popen, Deque[str]]:
    env = os.environ.copy()
    if not env.get("HF_HOME"):
        env["HF_HOME"] = str(_repo_root() / ".hf_cache")
    env["PYTHONPATH"] = _build_pythonpath()
    env["PYTHONUNBUFFERED"] = "1"
    env["KEYMUSE_HOST"] = host
    env["KEYMUSE_PORT"] = str(port)
    if mode:
        env["KEYMUSE_MODE"] = mode
    if device:
        env["KEYMUSE_DEVICE"] = device
    if model:
        env["KEYMUSE_MODEL"] = model

    logger.info("Starting backend process")
    process = subprocess.Popen(
        [sys.executable, "-m", "keymuse_backend.server"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    output_buffer: Deque[str] = deque(maxlen=200)

    def _reader() -> None:
        if process.stdout is None:
            return
        for line in process.stdout:
            output_buffer.append(line.rstrip())
            logger.info("[backend] %s", line.rstrip())

    thread = threading.Thread(target=_reader, daemon=True)
    thread.start()

    return process, output_buffer


async def _wait_for_backend_ready(
    *,
    host: str,
    port: int,
    timeout_s: float,
    poll_s: float,
    backend_process: subprocess.Popen,
    backend_output: Deque[str],
) -> None:
    deadline = time.monotonic() + timeout_s
    last_error: Optional[str] = None

    while time.monotonic() < deadline:
        if backend_process.poll() is not None:
            tail = "\n".join(backend_output)
            raise RuntimeError(
                "Backend process exited early. Recent output:\n" + tail
            )

        client = DictationClient(host, port)
        try:
            health = await client.health()
            if health.ready:
                logger.info(
                    "Backend ready: mode=%s detail=%s",
                    health.mode,
                    health.detail,
                )
                return
            last_error = health.detail
        except Exception as exc:
            last_error = str(exc)
        finally:
            await client.close()

        await asyncio.sleep(poll_s)

    raise RuntimeError(
        f"Backend not ready after {timeout_s:.1f}s: {last_error or 'timeout'}"
    )


def _stop_backend(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    logger.info("Stopping backend process")
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="KeyMuse Windows launcher (backend + client)",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=50051)
    parser.add_argument(
        "--backend-mode",
        choices=["mock", "nemo"],
        help="Backend engine mode (default: env or backend default)",
    )
    parser.add_argument("--backend-device", help="Backend device override")
    parser.add_argument("--backend-model", help="Backend model override")
    parser.add_argument(
        "--client-mode",
        choices=["interactive", "once", "health"],
        default="interactive",
    )
    parser.add_argument(
        "--backend-ready-timeout",
        type=float,
        default=180.0,
        help="Seconds to wait for backend readiness",
    )
    parser.add_argument(
        "--backend-ready-poll",
        type=float,
        default=0.5,
        help="Seconds between backend readiness checks",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    return parser.parse_args()


async def run_supervised() -> None:
    args = parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    backend_process, backend_output = _start_backend(
        host=args.host,
        port=args.port,
        mode=args.backend_mode,
        device=args.backend_device,
        model=args.backend_model,
    )

    try:
        await _wait_for_backend_ready(
            host=args.host,
            port=args.port,
            timeout_s=args.backend_ready_timeout,
            poll_s=args.backend_ready_poll,
            backend_process=backend_process,
            backend_output=backend_output,
        )

        config = ClientConfig(
            backend_host=args.host,
            backend_port=args.port,
            backend_ready_timeout_s=args.backend_ready_timeout,
            backend_ready_poll_s=args.backend_ready_poll,
        )

        if args.client_mode == "health":
            await check_health(config)
        elif args.client_mode == "once":
            await run_once(config)
        else:
            await run_interactive(config)

    finally:
        _stop_backend(backend_process)


def main() -> None:
    asyncio.run(run_supervised())


if __name__ == "__main__":
    main()
