import os
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class AppConfig:
    source_url: str = "http://192.168.0.200:8090/api/v1/latest"
    poll_interval_ms: int = 500
    request_timeout_seconds: float = 2.0
    stale_after_seconds: int = 5
    role: str = "grid"
    custom_name: str = "Raspberry Pi P1"
    device_instance: int = 40
    position: int = 0
    log_level: str = "INFO"


DEFAULT_CONFIG_PATH = "/data/cerbo-p1-bridge/config.yaml"


def _parse_scalar(raw: str) -> Any:
    value = raw.strip()
    if value == "":
        return ""

    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]

    lower = value.lower()
    if lower in ("true", "false"):
        return lower == "true"

    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value


def _load_yaml_like(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        return {}

    data: Dict[str, Any] = {}
    with open(path, "r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if ":" not in line:
                continue

            key, value = line.split(":", 1)
            key = key.strip()
            if not key:
                continue

            # Strip inline comments for unquoted values.
            if "#" in value and '"' not in value and "'" not in value:
                value = value.split("#", 1)[0]

            data[key] = _parse_scalar(value)

    return data


def _int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return int(value)


def _float_env(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return float(value)


def load_config(config_path: Optional[str] = None) -> AppConfig:
    path = config_path or os.getenv("CERBO_P1_CONFIG", DEFAULT_CONFIG_PATH)
    cfg = _load_yaml_like(path)

    app = AppConfig(
        source_url=str(cfg.get("source_url", AppConfig.source_url)),
        poll_interval_ms=int(cfg.get("poll_interval_ms", AppConfig.poll_interval_ms)),
        request_timeout_seconds=float(cfg.get("request_timeout_seconds", AppConfig.request_timeout_seconds)),
        stale_after_seconds=int(cfg.get("stale_after_seconds", AppConfig.stale_after_seconds)),
        role=str(cfg.get("role", AppConfig.role)),
        custom_name=str(cfg.get("custom_name", AppConfig.custom_name)),
        device_instance=int(cfg.get("device_instance", AppConfig.device_instance)),
        position=int(cfg.get("position", AppConfig.position)),
        log_level=str(cfg.get("log_level", AppConfig.log_level)),
    )

    # Env overrides (useful for quick tweaks via systemd Environment=)
    app.source_url = os.getenv("CERBO_P1_SOURCE_URL", app.source_url)
    app.poll_interval_ms = _int_env("CERBO_P1_POLL_INTERVAL_MS", app.poll_interval_ms)
    app.request_timeout_seconds = _float_env("CERBO_P1_REQUEST_TIMEOUT_SECONDS", app.request_timeout_seconds)
    app.stale_after_seconds = _int_env("CERBO_P1_STALE_AFTER_SECONDS", app.stale_after_seconds)
    app.role = os.getenv("CERBO_P1_ROLE", app.role)
    app.custom_name = os.getenv("CERBO_P1_CUSTOM_NAME", app.custom_name)
    app.device_instance = _int_env("CERBO_P1_DEVICE_INSTANCE", app.device_instance)
    app.position = _int_env("CERBO_P1_POSITION", app.position)
    app.log_level = os.getenv("CERBO_P1_LOG_LEVEL", app.log_level)

    validate_config(app)
    return app


def validate_config(config: AppConfig) -> None:
    if config.poll_interval_ms < 100:
        raise ValueError("poll_interval_ms must be >= 100")
    if config.request_timeout_seconds <= 0:
        raise ValueError("request_timeout_seconds must be > 0")
    if config.stale_after_seconds < 1:
        raise ValueError("stale_after_seconds must be >= 1")
    if config.role not in ("grid", "pvinverter"):
        raise ValueError("role must be one of: grid, pvinverter")
    if config.device_instance < 0:
        raise ValueError("device_instance must be >= 0")
    if config.position not in (0, 1, 2):
        raise ValueError("position must be 0, 1, or 2")
