#!/usr/bin/python3 -u
import argparse
import json
import logging
from datetime import datetime, timezone
from typing import Optional
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

try:
    from gi.repository import GLib  # type: ignore
except ImportError:
    GLib = None  # type: ignore

try:
    from .config import load_config
    from .dbus_publisher import VictronDBusPublisher
except ImportError:
    # Support direct execution: python3 service.py
    from config import load_config  # type: ignore
    from dbus_publisher import VictronDBusPublisher  # type: ignore


def build_logger(level: str) -> logging.Logger:
    logger = logging.getLogger("cerbo-p1-bridge")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        logger.addHandler(handler)
    return logger


def _is_stale(received_at: Optional[str], stale_after_seconds: int) -> bool:
    if not received_at:
        return True
    try:
        dt = datetime.fromisoformat(received_at.replace("Z", "+00:00"))
    except ValueError:
        return True
    now = datetime.now(timezone.utc)
    return (now - dt).total_seconds() > stale_after_seconds


def poll_latest(source_url: str, timeout_seconds: float) -> dict:
    try:
        with urlopen(source_url, timeout=timeout_seconds) as response:
            status_code = getattr(response, "status", 200)
            if status_code >= 400:
                raise RuntimeError("HTTP error status: %s" % status_code)
            body = response.read().decode("utf-8")
    except HTTPError as exc:
        raise RuntimeError("HTTP error status: %s" % exc.code)
    except URLError as exc:
        raise RuntimeError("URL error: %s" % exc.reason)

    payload = json.loads(body)
    if not isinstance(payload, dict):
        raise ValueError("latest payload must be a JSON object")
    return payload


def run(config_path: Optional[str] = None) -> None:
    cfg = load_config(config_path)
    logger = build_logger(cfg.log_level)

    if GLib is None:
        raise RuntimeError("gi.repository.GLib not available; install python3-gi on Venus OS")

    from dbus.mainloop.glib import DBusGMainLoop  # type: ignore
    DBusGMainLoop(set_as_default=True)

    publisher = VictronDBusPublisher(cfg, logger)
    publisher.initialize()

    logger.info(
        "Starting Cerbo bridge role=%s source=%s poll_interval_ms=%d device_instance=%d dbus=%s",
        cfg.role,
        cfg.source_url,
        cfg.poll_interval_ms,
        cfg.device_instance,
        publisher.get_service_name(),
    )
    if not publisher.is_enabled():
        raise RuntimeError(
            "DBus publishing not enabled: registration failed or library missing; "
            "check vedbus availability and device_instance/service-name conflicts"
        )

    def _update():
        try:
            payload = poll_latest(cfg.source_url, cfg.request_timeout_seconds)
            stale = _is_stale(payload.get("received_at"), cfg.stale_after_seconds)
            publisher.update_from_payload(payload, stale)

            if stale:
                logger.warning("Received stale payload from source")
            else:
                logger.info(
                    "Latest usage=%sw production=%sw age=%.3fs",
                    payload.get("current_power_usage_w"),
                    payload.get("current_power_production_w"),
                    float(payload.get("age_seconds", -1.0)),
                )

            logger.debug("Payload: %s", json.dumps(payload, separators=(",", ":")))
        except Exception as exc:
            publisher.set_error(str(exc))
            logger.error("Polling error: %s", exc)

        return True  # keep GLib timer firing

    GLib.timeout_add(cfg.poll_interval_ms, _update)

    mainloop = GLib.MainLoop()
    logger.info("Entering GLib mainloop")
    mainloop.run()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Cerbo P1 bridge service")
    parser.add_argument(
        "--config",
        dest="config_path",
        default=None,
        help="Path to YAML config file",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run(args.config_path)


if __name__ == "__main__":
    main()
