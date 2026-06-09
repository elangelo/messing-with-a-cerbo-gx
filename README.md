# Cerbo P1 Bridge

This service runs on Cerbo GX (Venus OS), polls latest smart-meter values from your Raspberry Pi, and publishes them to Victron DBus.

## Is Python the only option?

No. You can use C/C++/Go/Rust too. But Python is the practical default on Cerbo because Victron examples and `velib_python` DBus helpers are Python-first and easiest to maintain.

## Repo layout

```
messing-with-cerbo/
  Makefile                    ← workstation tooling
  requirements.txt            ← dev dependencies (none required on device)
  scripts/
    deploy-to-cerbo.sh        ← deploy helper called by make deploy
  cerbo/                      ← everything deployed to the device
    manage.sh                 ← install / restart / uninstall / status
    cerbo-p1-bridge.py        ← entry point (sets up velib_python path)
    config.example.yaml       ← template; copied to config.yaml on first deploy
    service/
      run                     ← daemontools service script
      log/run                 ← svlogd logger (writes to /var/log/cerbo-p1-bridge)
    cerbo_p1_bridge/          ← Python package
      config.py
      dbus_publisher.py
      service.py
```

## Deploy

From your workstation:

```sh
make deploy                              # deploys to root@venus
CERBO_HOST=root@192.168.0.120 make deploy  # override host
REMOTE_DIR=/data/cerbo-p1-bridge make deploy  # override remote path
SKIP_RESTART=1 make deploy               # sync files only, skip manage.sh install
```

`make deploy` syncs `cerbo/` to `/data/cerbo-p1-bridge/` on the device and runs `manage.sh install`, which:
- Creates the `/service/cerbo-p1-bridge` symlink so daemontools starts the service
- Copies `config.example.yaml` to `config.yaml` if no config exists yet
- Adds itself to `/data/rc.local` so the service survives firmware updates

Other targets:

```sh
make status    # service status + svstat
make restart   # restart service
make logs      # tail /var/log/cerbo-p1-bridge/current (live)
make help      # list all targets
```

## Configuration

Edit `/data/cerbo-p1-bridge/config.yaml` on the Cerbo after first deploy.
See `cerbo/config.example.yaml` for all available options.

Environment variable overrides (prefix `CERBO_P1_`):
- `CERBO_P1_CONFIG`
- `CERBO_P1_SOURCE_URL`
- `CERBO_P1_POLL_INTERVAL_MS`
- `CERBO_P1_REQUEST_TIMEOUT_SECONDS`
- `CERBO_P1_STALE_AFTER_SECONDS`
- `CERBO_P1_ROLE`
- `CERBO_P1_CUSTOM_NAME`
- `CERBO_P1_DEVICE_INSTANCE`
- `CERBO_P1_POSITION`
- `CERBO_P1_LOG_LEVEL`

## Current status

- Config parsing and validation
- Polling loop to Raspberry Pi latest endpoint
- Victron DBus publishing for role `grid` and `pvinverter`
- Stale detection (marks service disconnected when source is stale)

Published DBus paths:
- `/Ac/Power`
- `/Ac/L1/Power`
- `/Ac/Energy/Forward`
- `/Ac/Energy/Reverse`
- `/Connected`
- `/ErrorCode`

## Verify on Cerbo

```sh
# Logs (live)
make logs
# or directly on the Cerbo:
tail -f /var/log/cerbo-p1-bridge/current

# Supervisor status
sv status /service/cerbo-p1-bridge

# DBus (example for grid instance 40)
dbus -y com.victronenergy.grid.http_40 /Ac/Power GetValue
```

