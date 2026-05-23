from __future__ import annotations

import asyncio
from dataclasses import dataclass
import os
import signal

from app.ais_source import AisSourceConfig
from app.ais_source import AisSourceError
from app.ais_source import load_ais_vessel_records


@dataclass(frozen=True)
class AisConsumerConfig:
    poll_seconds: float = 60.0
    run_once: bool = False

    @classmethod
    def from_env(cls) -> AisConsumerConfig:
        return cls(
            poll_seconds=max(0.1, float(os.getenv("AIS_CONSUMER_POLL_SECONDS", "60"))),
            run_once=_parse_bool(os.getenv("AIS_CONSUMER_RUN_ONCE", "false")),
        )


async def run_consumer(
    consumer_config: AisConsumerConfig | None = None,
    ais_config: AisSourceConfig | None = None,
    stop_event: asyncio.Event | None = None,
) -> int:
    try:
        consumer_config = consumer_config or AisConsumerConfig.from_env()
        ais_config = ais_config or AisSourceConfig.from_env()
    except (AisSourceError, ValueError):
        return 1

    stop_event = stop_event or asyncio.Event()

    exit_code = 0
    while not stop_event.is_set():
        try:
            await load_ais_vessel_records(ais_config)
        except AisSourceError:
            exit_code = 1
            break

        if consumer_config.run_once:
            break

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=consumer_config.poll_seconds)
        except TimeoutError:
            continue

    return exit_code


def main() -> int:
    async def _main() -> int:

        ## Clean Shutdown writes (Ctrl+C/Docker stop signals)
        stop_event = asyncio.Event()
        _install_signal_handlers(stop_event)

        # Actual Consumer
        return await run_consumer(stop_event=stop_event)

    try:
        return asyncio.run(_main())
    except KeyboardInterrupt:
        return 0


def _install_signal_handlers(stop_event: asyncio.Event) -> None:
    loop = asyncio.get_running_loop()
    for signal_name in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(signal_name, stop_event.set)
        except NotImplementedError:
            signal.signal(signal_name, lambda *_: stop_event.set())


def _parse_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


if __name__ == "__main__":
    raise SystemExit(main())
