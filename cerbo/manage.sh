#!/bin/bash
# Cerbo P1 Bridge Management Script
# Manages install, restart, uninstall, and status of the cerbo-p1-bridge service on Venus OS.

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
DAEMON_NAME=${SCRIPT_DIR##*/}
SERVICE_SCRIPT="cerbo-p1-bridge.py"

show_usage() {
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  install    Install the service"
    echo "  restart    Restart the service"
    echo "  uninstall  Uninstall the service"
    echo "  status     Check service status"
    echo "  help       Show this help message"
    echo ""
    exit 1
}

install_service() {
    echo "Installing cerbo-p1-bridge service..."

    chmod a+x "$SCRIPT_DIR/service/run"
    chmod 755 "$SCRIPT_DIR/service/run"
    chmod a+x "$SCRIPT_DIR/service/log/run"
    chmod 755 "$SCRIPT_DIR/service/log/run"

    if [ -h "/service/$DAEMON_NAME" ]; then
        echo "Service link already exists, removing old link..."
        rm "/service/$DAEMON_NAME"
    fi

    ln -s "$SCRIPT_DIR/service" "/service/$DAEMON_NAME"
    echo "Service link created."

    # Ensure config exists
    if [ ! -f "$SCRIPT_DIR/config.yaml" ]; then
        cp "$SCRIPT_DIR/config.example.yaml" "$SCRIPT_DIR/config.yaml"
        echo "Created default config.yaml from config.example.yaml — please review it."
    fi

    # Add to rc.local so the service survives firmware updates
    filename=/data/rc.local
    if [ ! -f "$filename" ]; then
        touch "$filename"
        chmod 755 "$filename"
        echo "#!/bin/bash" >> "$filename"
        echo "" >> "$filename"
    fi

    grep -qxF "$SCRIPT_DIR/manage.sh install" "$filename" || echo "$SCRIPT_DIR/manage.sh install" >> "$filename"
    echo "Added to $filename for boot persistence."

    echo "Installation complete. Service should start automatically."
}

restart_service() {
    echo "Restarting cerbo-p1-bridge service..."

    pkill -f "python3 $SCRIPT_DIR/$SERVICE_SCRIPT" || echo "No running service found to kill."

    sleep 1

    check_status
}

uninstall_service() {
    echo "Uninstalling cerbo-p1-bridge service..."

    if [ -h "/service/$DAEMON_NAME" ]; then
        rm "/service/$DAEMON_NAME"
        echo "Service link removed."
    else
        echo "Service link not found, already uninstalled?"
    fi

    pkill -f "python3 $SCRIPT_DIR/$SERVICE_SCRIPT" || echo "No running service found."
    pkill -f "supervise $DAEMON_NAME" || echo "No supervise process found."

    chmod a-x "$SCRIPT_DIR/service/run"
    echo "Service script disabled."

    if [ -f /data/rc.local ]; then
        sed -i "\#$SCRIPT_DIR/manage.sh install#d" /data/rc.local
        echo "Removed from /data/rc.local startup script."
    fi

    echo "Uninstallation complete."
}

check_status() {
    echo "Checking cerbo-p1-bridge service status..."

    if [ -h "/service/$DAEMON_NAME" ]; then
        echo "Service is installed (link exists at /service/$DAEMON_NAME)."
    else
        echo "Service is not installed."
    fi

    if pgrep -f "python3 $SCRIPT_DIR/$SERVICE_SCRIPT" > /dev/null; then
        echo "Service is running."
        pid=$(pgrep -f "python3 $SCRIPT_DIR/$SERVICE_SCRIPT")
        echo "Process ID: $pid"
    else
        echo "Service is not running."
    fi

    if command -v svstat > /dev/null 2>&1; then
        svstat "/service/$DAEMON_NAME" 2>/dev/null || true
    fi
}

case "$1" in
    install)
        install_service
        ;;
    restart)
        restart_service
        ;;
    uninstall)
        uninstall_service
        ;;
    status)
        check_status
        ;;
    help|--help|-h)
        show_usage
        ;;
    *)
        if [ -z "$1" ]; then
            show_usage
        else
            echo "Unknown command: $1"
            show_usage
        fi
        ;;
esac

exit 0
