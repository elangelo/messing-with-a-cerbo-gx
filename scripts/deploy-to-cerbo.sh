#!/usr/bin/env bash
set -euo pipefail

# Deploy cerbo-p1-bridge to a Cerbo GX / Venus OS device.
#
# Usage:
#   ./scripts/deploy-to-cerbo.sh
#   CERBO_HOST=root@192.168.0.120 ./scripts/deploy-to-cerbo.sh
#
# Optional env vars:
#   CERBO_HOST      SSH target (default: root@cerbo)
#   REMOTE_DIR      Remote install directory (default: /data/cerbo-p1-bridge)
#   SKIP_RESTART    Set to 1 to skip service (re)install after sync (default: 0)

CERBO_HOST="${CERBO_HOST:-root@cerbo}"
REMOTE_DIR="${REMOTE_DIR:-/data/cerbo-p1-bridge}"
SKIP_RESTART="${SKIP_RESTART:-0}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

log() {
  printf '[deploy] %s\n' "$*"
}

run_remote() {
  ssh -o BatchMode=yes "${CERBO_HOST}" "$@"
}

log "Deploy target: ${CERBO_HOST}"
log "Remote dir: ${REMOTE_DIR}"

log "Checking SSH connectivity"
run_remote "echo connected"

log "Creating remote directory"
run_remote "mkdir -p '${REMOTE_DIR}'"

log "Syncing cerbo/ to ${REMOTE_DIR}"
(
  cd "${PROJECT_ROOT}/cerbo"
  tar \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.pytest_cache' \
    --exclude='.mypy_cache' \
    -czf - .
) | run_remote "tar -xzf - -C '${REMOTE_DIR}'"

log "Making manage.sh executable"
run_remote "chmod a+x '${REMOTE_DIR}/manage.sh'"

if [[ "${SKIP_RESTART}" != "1" ]]; then
  log "Running manage.sh install on remote"
  run_remote "'${REMOTE_DIR}/manage.sh' install"
else
  log "Skipping manage.sh install (SKIP_RESTART=1)"
fi

log "Deployment completed successfully"
log "Check status with: ssh ${CERBO_HOST} '${REMOTE_DIR}/manage.sh status'"

