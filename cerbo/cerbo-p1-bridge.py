#!/usr/bin/env python3
"""
Cerbo P1 Bridge — entry point for Venus OS / Cerbo GX.

Installs at /data/cerbo-p1-bridge/cerbo-p1-bridge.py and is managed
by the service/run script via the daemontools /service symlink.
"""

import os
import sys

script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

# Venus OS ships velib_python here; use it when available so no submodule or
# pip install is needed on the Cerbo.
velib_path = "/opt/victronenergy/dbus-systemcalc-py/ext/velib_python"
if os.path.isdir(velib_path) and velib_path not in sys.path:
    sys.path.insert(1, velib_path)

from cerbo_p1_bridge.service import main  # noqa: E402

if __name__ == "__main__":
    main()
