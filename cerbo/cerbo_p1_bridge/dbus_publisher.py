import logging
import os
from typing import Optional

try:
    from .config import AppConfig
except ImportError:
    # Support direct execution paths where files are run as scripts.
    from config import AppConfig  # type: ignore


def _import_vedbus():
    # Venus OS ships velib_python in the dbus-systemcalc-py tree.
    candidate_paths = [
        "/opt/victronenergy/dbus-systemcalc-py/ext/velib_python",
        "/data/dbus-systemcalc-py/ext/velib_python",
    ]

    for path in candidate_paths:
        if path not in os.sys.path and os.path.isdir(path):
            os.sys.path.append(path)

    try:
        from vedbus import VeDbusService  # type: ignore

        return VeDbusService
    except Exception:
        return None


class VictronDBusPublisher:
    PRODUCT_ID_GRID = 45069
    PRODUCT_ID_PVINVERTER = 0xA144
    DEVICE_TYPE = 345

    def __init__(self, cfg: AppConfig, logger: logging.Logger):
        self.cfg = cfg
        self.logger = logger
        self._service = None
        self._enabled = False
        self._service_name = self._build_service_name(cfg)

    @staticmethod
    def _build_service_name(cfg: AppConfig) -> str:
        base = "com.victronenergy.grid" if cfg.role == "grid" else "com.victronenergy.pvinverter"
        return "%s.http_%d" % (base, cfg.device_instance)

    def initialize(self) -> None:
        VeDbusService = _import_vedbus()
        if VeDbusService is None:
            self.logger.warning("Victron DBus library not available; running in log-only mode")
            return

        try:
            self._service = VeDbusService(self._service_name)
            self._add_common_paths()
            self._add_role_paths()
            self._service["/Connected"] = 1
            self._enabled = True
            self.logger.info("Registered DBus service: %s", self._service_name)
        except Exception as exc:
            self._enabled = False
            self._service = None
            self.logger.error("Failed to initialize DBus service: %s", exc)

    def _add_common_paths(self) -> None:
        assert self._service is not None
        self._service.add_path("/Mgmt/ProcessName", __file__)
        self._service.add_path("/Mgmt/ProcessVersion", "1.0")
        self._service.add_path("/Mgmt/Connection", "P1 via Raspberry Pi HTTP")

        if self.cfg.role == "grid":
            product_id = self.PRODUCT_ID_GRID
        else:
            product_id = self.PRODUCT_ID_PVINVERTER

        self._service.add_path("/DeviceInstance", self.cfg.device_instance)
        self._service.add_path("/ProductId", product_id)
        self._service.add_path("/DeviceType", self.DEVICE_TYPE)
        self._service.add_path("/ProductName", "Raspberry Pi P1 Bridge")
        self._service.add_path("/FirmwareVersion", "1.0")
        self._service.add_path("/HardwareVersion", "N/A")
        self._service.add_path("/Latency", None)
        self._service.add_path("/Serial", "cerbo-p1-%d" % self.cfg.device_instance)
        self._service.add_path("/Connected", 0)
        self._service.add_path("/CustomName", self.cfg.custom_name)
        self._service.add_path("/Role", self.cfg.role)
        self._service.add_path("/Position", self.cfg.position)
        self._service.add_path("/ErrorCode", 0)
        self._service.add_path("/UpdateIndex", 0)

    def _add_role_paths(self) -> None:
        assert self._service is not None

        self._service.add_path("/Ac/Power", 0)
        self._service.add_path("/Ac/Current", 0.0)
        self._service.add_path("/Ac/Voltage", 0.0)
        self._service.add_path("/Ac/L1/Power", 0)
        self._service.add_path("/Ac/L2/Power", 0)
        self._service.add_path("/Ac/L3/Power", 0)
        self._service.add_path("/Ac/L1/Voltage", 0.0)
        self._service.add_path("/Ac/L2/Voltage", 0.0)
        self._service.add_path("/Ac/L3/Voltage", 0.0)
        self._service.add_path("/Ac/L1/Current", 0.0)
        self._service.add_path("/Ac/L2/Current", 0.0)
        self._service.add_path("/Ac/L3/Current", 0.0)
        self._service.add_path("/Ac/Energy/Forward", 0.0)
        self._service.add_path("/Ac/Energy/Reverse", 0.0)

    def update_from_payload(self, payload: dict, stale: bool) -> None:
        usage_w = int(payload.get("current_power_usage_w", 0) or 0)
        production_w = int(payload.get("current_power_production_w", 0) or 0)

        usage_l1 = int(payload.get("current_power_usage_l1_w", 0) or 0)
        usage_l2 = int(payload.get("current_power_usage_l2_w", 0) or 0)
        usage_l3 = int(payload.get("current_power_usage_l3_w", 0) or 0)
        production_l1 = int(payload.get("current_power_production_l1_w", 0) or 0)
        production_l2 = int(payload.get("current_power_production_l2_w", 0) or 0)
        production_l3 = int(payload.get("current_power_production_l3_w", 0) or 0)

        voltage_l1 = float(payload.get("voltage_l1_v", 0.0) or 0.0)
        voltage_l2 = float(payload.get("voltage_l2_v", 0.0) or 0.0)
        voltage_l3 = float(payload.get("voltage_l3_v", 0.0) or 0.0)
        current_l1 = float(payload.get("current_l1_a", 0.0) or 0.0)
        current_l2 = float(payload.get("current_l2_a", 0.0) or 0.0)
        current_l3 = float(payload.get("current_l3_a", 0.0) or 0.0)

        total_consumed = float(payload.get("total_consumed_kwh", 0.0) or 0.0)
        total_produced = float(payload.get("total_produced_kwh", 0.0) or 0.0)

        if self.cfg.role == "grid":
            # Grid sign convention: import positive, export negative.
            l1_power = usage_l1 - production_l1
            l2_power = usage_l2 - production_l2
            l3_power = usage_l3 - production_l3

            if l1_power == 0 and l2_power == 0 and l3_power == 0:
                l1_power = usage_w - production_w

            ac_power = l1_power + l2_power + l3_power
        else:
            # PV inverter convention: production positive.
            l1_power = production_l1
            l2_power = production_l2
            l3_power = production_l3

            if l1_power == 0 and l2_power == 0 and l3_power == 0:
                l1_power = production_w

            ac_power = l1_power + l2_power + l3_power

        if stale:
            connected = 0
            ac_power = 0
            l1_power = 0
            l2_power = 0
            l3_power = 0
            voltage_l1 = 0.0
            voltage_l2 = 0.0
            voltage_l3 = 0.0
            current_l1 = 0.0
            current_l2 = 0.0
            current_l3 = 0.0
        else:
            connected = 1

        if self._enabled and self._service is not None:
            self._service["/Connected"] = connected
            self._service["/Ac/Power"] = ac_power
            self._service["/Ac/Current"] = current_l1 + current_l2 + current_l3

            non_zero_voltages = [v for v in (voltage_l1, voltage_l2, voltage_l3) if v > 0]
            if non_zero_voltages:
                self._service["/Ac/Voltage"] = sum(non_zero_voltages) / float(len(non_zero_voltages))
            else:
                self._service["/Ac/Voltage"] = 0.0

            self._service["/Ac/L1/Power"] = l1_power
            self._service["/Ac/L2/Power"] = l2_power
            self._service["/Ac/L3/Power"] = l3_power
            self._service["/Ac/L1/Voltage"] = voltage_l1
            self._service["/Ac/L2/Voltage"] = voltage_l2
            self._service["/Ac/L3/Voltage"] = voltage_l3
            self._service["/Ac/L1/Current"] = current_l1
            self._service["/Ac/L2/Current"] = current_l2
            self._service["/Ac/L3/Current"] = current_l3
            self._service["/Ac/Energy/Forward"] = total_consumed
            self._service["/Ac/Energy/Reverse"] = total_produced
            self._service["/ErrorCode"] = 0 if connected else 1
            self._service["/UpdateIndex"] = (int(self._service["/UpdateIndex"]) + 1) % 256

        self.logger.debug(
            "Publish role=%s connected=%d ac_power=%dW usage=%dW production=%dW",
            self.cfg.role,
            connected,
            ac_power,
            usage_w,
            production_w,
        )

    def set_error(self, message: str) -> None:
        if self._enabled and self._service is not None:
            self._service["/Connected"] = 0
            self._service["/ErrorCode"] = 2
            self._service["/UpdateIndex"] = (int(self._service["/UpdateIndex"]) + 1) % 256
        self.logger.error("DBus publisher error: %s", message)

    def get_service_name(self) -> str:
        return self._service_name

    def is_enabled(self) -> bool:
        return self._enabled
