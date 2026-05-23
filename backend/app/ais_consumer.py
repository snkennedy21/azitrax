from __future__ import annotations

import asyncio
from dataclasses import dataclass
import logging
import os
import signal

from app.ais_source import AisSourceConfig
from app.ais_source import AisSourceError
from app.ais_source import load_ais_vessel_records


logger = logging.getLogger("app.ais_consumer")


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
    print("ais-consumer: loading configuration", flush=True)
    try:
        consumer_config = consumer_config or AisConsumerConfig.from_env()
        ais_config = ais_config or AisSourceConfig.from_env()
    except (AisSourceError, ValueError):
        print("ais-consumer: configuration failed", flush=True)
        logger.exception("AIS consumer configuration failed")
        logger.info("AIS consumer shutdown complete")
        return 1

    stop_event = stop_event or asyncio.Event()
    print(
        "ais-consumer: starting "
        f"source={ais_config.source} "
        f"mode={_source_mode(ais_config)} "
        f"poll_seconds={consumer_config.poll_seconds} "
        f"run_once={consumer_config.run_once}",
        flush=True,
    )

    logger.info(
        "Starting AIS consumer source=%s mode=%s fixture_path=%s ws_url=%s",
        ais_config.source,
        _source_mode(ais_config),
        ais_config.fixture_path,
        ais_config.aisstream_ws_url,
    )

    exit_code = 0
    try:
        while not stop_event.is_set():
            try:
                print("ais-consumer: reading vessel records", flush=True)
                records = await load_ais_vessel_records(ais_config)
            except AisSourceError:
                print("ais-consumer: read failed", flush=True)
                logger.exception("AIS consumer startup/read failed")
                exit_code = 1
                break

            print(f"ais-consumer: read {len(records)} vessel records", flush=True)
            logger.info("AIS consumer read %s vessel records", len(records))
            if consumer_config.run_once:
                print("ais-consumer: run-once complete", flush=True)
                logger.info("AIS consumer run-once mode complete")
                break

            print(f"ais-consumer: sleeping for {consumer_config.poll_seconds} seconds", flush=True)
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=consumer_config.poll_seconds)
            except TimeoutError:
                continue
    finally:
        print("ais-consumer: shutdown complete", flush=True)
        logger.info("AIS consumer shutdown complete")

    return exit_code


def main() -> int:
    print("ais-consumer: main started", flush=True)
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    async def _main() -> int:
        stop_event = asyncio.Event()
        _install_signal_handlers(stop_event)
        return await run_consumer(stop_event=stop_event)

    try:
        return asyncio.run(_main())
    except KeyboardInterrupt:
        print("ais-consumer: interrupted", flush=True)
        logger.info("AIS consumer interrupted")
        return 0


def _install_signal_handlers(stop_event: asyncio.Event) -> None:
    loop = asyncio.get_running_loop()
    for signal_name in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(signal_name, stop_event.set)
        except NotImplementedError:
            signal.signal(signal_name, lambda *_: stop_event.set())


def _source_mode(config: AisSourceConfig) -> str:
    if config.source == "fixture":
        return "fixture"
    if config.source == "aisstream":
        return "live"
    return "unsupported"


def _parse_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


if __name__ == "__main__":
    raise SystemExit(main())
