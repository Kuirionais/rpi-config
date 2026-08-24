#!/bin/bash

set -u

DOCKER_DIR="/srv/docker"

DOWNLOAD_PROJECT="docker"
DOWNLOAD_COMPOSE="$DOCKER_DIR/compose.yaml"

ARR_PROJECT="arrstack"
ARR_COMPOSE="$DOCKER_DIR/Stack.yaml"

usage() {
    cat <<EOF
Usage: $0 <command> [stack]

Commands:
  start [stack]      Start a stack
  stop [stack]       Stop a stack
  restart [stack]    Restart a stack
  status [stack]     Show stack/container status

Stacks:
  download           VPN/download stack
  arr                Sonarr/Radarr stack
  all                All active stacks

Examples:
  $0 start
  $0 start download
  $0 stop arr
  $0 restart all
  $0 status
EOF
}

compose_cmd() {
    local project="$1"
    local compose_file="$2"
    shift 2

    docker compose \
        -p "$project" \
        -f "$compose_file" \
        "$@"
}

start_stack() {
    case "$1" in
        download)
            echo "==> Starting download stack..."
            compose_cmd "$DOWNLOAD_PROJECT" "$DOWNLOAD_COMPOSE" up -d
            ;;
        arr)
            echo "==> Starting ARR stack..."
            compose_cmd "$ARR_PROJECT" "$ARR_COMPOSE" up -d
            ;;
        *)
            echo "Unknown stack: $1"
            return 1
            ;;
    esac
}

stop_stack() {
    case "$1" in
        download)
            echo "==> Stopping download stack..."
            compose_cmd "$DOWNLOAD_PROJECT" "$DOWNLOAD_COMPOSE" down
            ;;
        arr)
            echo "==> Stopping ARR stack..."
            compose_cmd "$ARR_PROJECT" "$ARR_COMPOSE" down
            ;;
        *)
            echo "Unknown stack: $1"
            return 1
            ;;
    esac
}

status_stack() {
    case "$1" in
        download)
            echo "===== DOWNLOAD STACK ====="
            compose_cmd "$DOWNLOAD_PROJECT" "$DOWNLOAD_COMPOSE" ps
            ;;
        arr)
            echo "===== ARR STACK ====="
            compose_cmd "$ARR_PROJECT" "$ARR_COMPOSE" ps
            ;;
        *)
            echo "Unknown stack: $1"
            return 1
            ;;
    esac
}

case "${1:-}" in
    start|stop|restart|status)
        COMMAND="$1"
        STACK="${2:-all}"
        ;;
    *)
        usage
        exit 1
        ;;
esac

case "$STACK" in
    download|arr)
        case "$COMMAND" in
            start)
                start_stack "$STACK"
                ;;
            stop)
                stop_stack "$STACK"
                ;;
            restart)
                stop_stack "$STACK" && start_stack "$STACK"
                ;;
            status)
                status_stack "$STACK"
                ;;
        esac
        ;;

    all)
        case "$COMMAND" in
            start)
                start_stack download && start_stack arr
                ;;
            stop)
                # Stop ARR first, then download services.
                stop_stack arr && stop_stack download
                ;;
            restart)
                stop_stack arr &&
                stop_stack download &&
                start_stack download &&
                start_stack arr
                ;;
            status)
                status_stack download
                echo
                status_stack arr
                ;;
        esac
        ;;

    *)
        echo "Unknown stack: $STACK"
        usage
        exit 1
        ;;
esac